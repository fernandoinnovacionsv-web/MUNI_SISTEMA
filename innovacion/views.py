from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import TemplateView, ListView
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
import datetime

# Importaciones internas del módulo Innovación
from .models import SolicitudAcceso, SistemaMunicipal, FuncionSistema, PerfilAcceso
from innovacion.decorators import tiene_funcion

# ===============================================================
#   1. VISTAS DE DASHBOARD Y SEGURIDAD
# ===============================================================

class InnovacionHomeView(LoginRequiredMixin, TemplateView):
    """Panel principal del módulo de Innovación / Sistemas"""
    template_name = 'innovacion/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['debe_cambiar_pass'] = user.check_password(user.username)
        context['pendientes_count'] = SolicitudAcceso.objects.filter(estado='PENDIENTE').count()
        return context

@login_required
def cambiar_password_primera_vez(request):
    """Obliga al usuario a cambiar su DNI como clave por una segura"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            request.session['must_change_password'] = False
            messages.success(request, "Contraseña actualizada correctamente.")
            return redirect('central:seleccionar_modulo')
        else:
            messages.error(request, "Error en los datos. Revise los requisitos de la clave.")
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'innovacion/acceso/cambiar_password_inicio.html', {'form': form})

@login_required
def restablecer_password(request, user_id):
    """Vuelve la contraseña del usuario a su número de DNI"""
    funciones = getattr(request, 'user_funciones', [])
    if not (request.user.is_superuser or 'acceso_innovacion_admin' in funciones):
        messages.error(request, "No tienes permisos para esta acción.")
        return redirect('central:seleccionar_modulo')

    usuario_afectado = get_object_or_404(User, id=user_id)
    usuario_afectado.set_password(usuario_afectado.username)
    usuario_afectado.save()

    messages.success(request, f"Contraseña de {usuario_afectado.username} restablecida con éxito.")
    return redirect('innovacion:usuarios_activos')

# ===============================================================
#   2. GESTIÓN DE SOLICITUDES DE ACCESO
# ===============================================================

class ListaSolicitudesView(LoginRequiredMixin, ListView):
    model = SolicitudAcceso
    template_name = 'innovacion/acceso/solicitudes_list.html'
    context_object_name = 'solicitudes'
    
    def get_queryset(self):
        return SolicitudAcceso.objects.filter(estado='PENDIENTE').order_by('-id')

@login_required
def solicitar_acceso_view(request, empleado_id):
    """Crea una petición de acceso desde el listado de RRHH"""
    from rrhh.models import Empleado 
    empleado = get_object_or_404(Empleado, id=empleado_id)
    
    solicitud, created = SolicitudAcceso.objects.get_or_create(
        empleado=empleado, 
        estado='PENDIENTE',
        defaults={'solicitado_por': request.user}
    )
    
    if created: 
        messages.success(request, f"Solicitud enviada para {empleado.apellido}.")
    else: 
        messages.warning(request, "Ya existe una solicitud pendiente.")
    
    return redirect('rrhh:personal_list')

@login_required
def procesar_acceso_view(request, solicitud_id):
    """Aprueba la solicitud, crea el usuario y vincula el empleado al perfil"""
    from rrhh.models import Empleado
    solicitud = get_object_or_404(SolicitudAcceso, id=solicitud_id)
    empleado = solicitud.empleado
    dni_usuario = str(empleado.dni)

    # 1. Crear o recuperar el Usuario de Django
    user, created = User.objects.get_or_create(
        username=dni_usuario,
        defaults={
            'first_name': empleado.nombre,
            'last_name': empleado.apellido,
            'email': getattr(empleado, 'correo', '') 
        }
    )
    
    if created:
        user.set_password(dni_usuario)
        user.save()

    # 2. Manejo del Perfil de Innovación
    # Importante: Creamos el perfil inicialmente desactivado para evitar el ValidationError del modelo
    perfil, created_perfil = PerfilAcceso.objects.get_or_create(
        user=user,
        defaults={'esta_activo': False}
    )
    
    # 3. Vinculamos formalmente al empleado y activamos
    perfil.empleado = empleado
    perfil.esta_activo = True
    perfil.save() # Aquí ya pasará la validación porque tiene el objeto empleado asignado

    # 4. Actualizar estado de la solicitud
    solicitud.estado = 'PROCESADO'
    solicitud.save()

    messages.info(request, f"Acceso procesado para {dni_usuario}. Ahora asigne las funciones correspondientes.")
    return redirect('innovacion:gestionar_accesos', user_id=user.id)

# ===============================================================
#   3. CONTROL DE FUNCIONES Y ASISTENCIA
# ===============================================================

@login_required
def gestionar_accesos_usuario(request, user_id):
    """Asigna funciones de sistemas (rrhh, obras, etc) a un usuario"""
    usuario_afectado = get_object_or_404(User, id=user_id)
    perfil, _ = PerfilAcceso.objects.get_or_create(user=usuario_afectado)
    
    if request.method == "POST":
        funciones_ids = request.POST.getlist('funciones_seleccionadas')
        perfil.funciones.set(funciones_ids)
        perfil.esta_activo = 'esta_activo' in request.POST
        perfil.save()
        
        messages.success(request, f"Permisos actualizados para {usuario_afectado.get_full_name()}.")
        return redirect('innovacion:usuarios_activos')

    sistemas = SistemaMunicipal.objects.prefetch_related('funciones').all()
    funciones_usuario = perfil.funciones.values_list('id', flat=True)

    context = {
        'usuario_afectado': usuario_afectado,
        'perfil': perfil,
        'sistemas': sistemas,
        'funciones_usuario': funciones_usuario,
    }
    return render(request, 'innovacion/acceso/gestionar_accesos.html', context)

@login_required
@tiene_funcion('rrhh_tomar_asistencia')
def toma_asistencia_view(request):
    """Vista para cargar asistencia y horas extras filtrado por sector del jefe"""
    from rrhh.models import Empleado, RegistroAsistencia, FrancoProgramado
    
    # Capturar la fecha parámetro (por defecto hoy)
    fecha_param = request.GET.get('fecha') or request.POST.get('fecha_registro')
    hoy = timezone.now().date()
    if fecha_param:
        try:
            fecha_parseada = datetime.datetime.strptime(fecha_param, "%Y-%m-%d").date()
            # Validación: permitir carga solo del mes actual y mes inmediato anterior (si no está bloqueado)
            # Para simplificar, la fecha seleccionada es la que manda
            hoy = fecha_parseada
        except ValueError:
            pass
    
    try:
        # Acceso al perfil usando el related_name correcto
        perfil = request.user.perfil_innovacion 
        if not perfil.empleado or not perfil.empleado.sector:
            messages.error(request, "Error: Tu usuario no tiene un Sector asignado en RRHH.")
            return redirect('rrhh:dashboard_rrhh')
        
        sector_usuario = perfil.empleado.sector
        subsector_usuario = perfil.empleado.subsector
    except Exception:
        messages.error(request, "Tu usuario no posee un perfil de empleado vinculado.")
        return redirect('rrhh:dashboard_rrhh')

    # Filtros de personal a cargo
    filtros = {'sector': sector_usuario, 'activo': True}
    if subsector_usuario:
        filtros['subsector'] = subsector_usuario

    personal = Empleado.objects.filter(**filtros)

    # Identificar quiénes tienen Franco hoy
    francos_hoy = FrancoProgramado.objects.filter(fecha=hoy, empleado__in=personal).values_list('empleado_id', flat=True)
    
    for emp in personal:
        emp.tiene_franco_hoy = emp.id in francos_hoy

    # Verificación de bloqueo de carga diaria y detección de licencias/francos
    asistencias_existentes = RegistroAsistencia.objects.filter(
        fecha=hoy, 
        empleado__in=personal
    )
    ya_registrado = asistencias_existentes.exists()
    
    # Determinar si el día actual está bloqueado (basta que uno esté bloqueado para asumir cierre)
    mes_cerrado = asistencias_existentes.filter(bloqueado=True).exists()

    # Si se intenta cargar un registro de mes anterior, verificamos regla:
    if hoy.month != timezone.now().date().month and hoy.year == timezone.now().date().year:
        if not request.user.is_superuser and 'acceso_innovacion_admin' not in getattr(request, 'user_funciones', []):
           # messages.warning(request, "Estás visualizando/editando un mes pasado. Si está cerrado no podrás guardar.")
           pass

    # Mapeo de licencias para acceso rápido
    dict_asistencias = {a.empleado_id: a.estado for a in asistencias_existentes}

    for emp in personal:
        emp.tiene_franco_hoy = emp.id in francos_hoy
        emp.estado_hoy = dict_asistencias.get(emp.id)
        emp.tiene_licencia_hoy = (emp.estado_hoy == 'LICENCIA')

    # Determinar qué MES corresponde cerrar (el más antiguo abierto)
    primer_registro_abierto = RegistroAsistencia.objects.filter(
        empleado__in=personal,
        bloqueado=False
    ).order_by('fecha').first()
    
    mes_a_cerrar = None
    puedes_cerrar = False
    
    if primer_registro_abierto:
        mes_a_cerrar = primer_registro_abierto.fecha
        # Permitir cerrar si es un mes pasado
        if mes_a_cerrar.year < timezone.now().date().year or mes_a_cerrar.month <= timezone.now().date().month:
            puedes_cerrar = True

    meses_nombres = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    if request.method == 'POST':
        if mes_cerrado:
            messages.error(request, "Este mes se encuentra CERRADO para modificaciones de asistencia.")
            return redirect(request.META.get('HTTP_REFERER', 'rrhh:dashboard_rrhh'))

        for emp in personal:
            estado = request.POST.get(f'estado_{emp.id}')
            if estado:
                # Captura de Horas Extras
                hs_extra = request.POST.get(f'horas_{emp.id}', 0)
                try:
                    hs_extra = float(hs_extra.replace(',', '.')) if hs_extra else 0.0
                except ValueError:
                    hs_extra = 0.0

                # Protegemos el estado de LICENCIA (no se puede sobreescribir por el jefe)
                if RegistroAsistencia.objects.filter(empleado=emp, fecha=hoy, estado='LICENCIA').exists():
                    continue

                # Guardado con nombres de campos correctos del modelo RRHH
                registro, created = RegistroAsistencia.objects.update_or_create(
                    empleado=emp,
                    fecha=hoy,
                    defaults={
                        'estado': estado,
                        'horas_extras': hs_extra,
                        'motivo_ausencia': request.POST.get(f'motivo_{emp.id}', ''),
                        'registrado_por': request.user
                    }
                )
                
                if f'adjunto_{emp.id}' in request.FILES:
                    registro.adjunto_justificativo = request.FILES[f'adjunto_{emp.id}']
                    registro.save()
        
        messages.success(request, f"Asistencia del {hoy} procesada correctamente.")
        return redirect(f"{request.path}?fecha={hoy}")

    return render(request, 'rrhh/asistencia/toma_asistencia.html', {
        'personal': personal,
        'sector': sector_usuario,
        'subsector': subsector_usuario,
        'hoy': hoy,
        'ya_registrado': ya_registrado,
        'mes_cerrado': mes_cerrado,
        'mes_a_cerrar_obj': mes_a_cerrar,
        'mes_a_cerrar_nombre': meses_nombres.get(mes_a_cerrar.month) if mes_a_cerrar else None,
        'puedes_cerrar': puedes_cerrar
    })

# ===============================================================
#   4. ADMINISTRACIÓN DE USUARIOS
# ===============================================================

@login_required
def lista_usuarios_activos(request):
    """Listado de todos los usuarios que tienen un perfil creado"""
    usuarios = User.objects.filter(
        is_superuser=False, 
        perfil_innovacion__isnull=False
    ).select_related('perfil_innovacion', 'perfil_innovacion__empleado').order_by('last_name')
    
    return render(request, 'innovacion/acceso/usuarios_activos.html', {
        'usuarios': usuarios,
    })

@login_required
def toggle_estado_usuario(request, user_id):
    """Activa o desactiva el acceso de un usuario al sistema"""
    perfil = get_object_or_404(PerfilAcceso, user_id=user_id)
    perfil.esta_activo = not perfil.esta_activo
    perfil.save()
    
    estado = "activado" if perfil.esta_activo else "bloqueado"
    messages.success(request, f"El acceso ha sido {estado}.")
    return redirect('innovacion:usuarios_activos')

@login_required
def toggle_permiso_solicitud(request, user_id):
    """Permite o prohíbe que el usuario cargue sus propias vacaciones"""
    perfil = get_object_or_404(PerfilAcceso, user_id=user_id)
    perfil.puede_solicitar = not perfil.puede_solicitar
    perfil.save()
    
    accion = "habilitado" if perfil.puede_solicitar else "deshabilitado"
    messages.info(request, f"Trámites de personal {accion}.")
    return redirect('innovacion:usuarios_activos')