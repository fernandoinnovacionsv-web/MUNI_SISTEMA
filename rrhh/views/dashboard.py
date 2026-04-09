from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone # Importante para la fecha de hoy
from ..models import Empleado, Vacacion, Movimiento, RegistroAsistencia, SolicitudLicencia # Agregamos SolicitudLicencia
from innovacion.decorators import tiene_funcion
from ..utils import obtener_personal_permitido

@login_required
@tiene_funcion('rrhh_ver_personal') 
def dashboard_rrhh(request):
    # Fecha actual para filtrar la asistencia
    hoy = timezone.now().date()
    
    personal_permitido = obtener_personal_permitido(request.user)
    
    # Contar personal de licencia actual (excluyendo rechazadas)
    conteo_licencias = SolicitudLicencia.objects.filter(
        empleado__in=personal_permitido,
        fecha_desde__lte=hoy,
        fecha_hasta__gte=hoy
    ).exclude(estado='Rechazada').values('empleado').distinct().count()
    
    # NUEVO: Contar registros de asistencia realizados hoy
    asistencia_hoy = RegistroAsistencia.objects.filter(empleado__in=personal_permitido, fecha=hoy).count()
    
    # Contar personal sancionado hoy
    sanciones_hoy = RegistroAsistencia.objects.filter(empleado__in=personal_permitido, fecha=hoy, estado='SANCION').count()
    
    context = {
        "metrics": {
            "activos": personal_permitido.filter(activo=True).count(),
            "vacaciones": Vacacion.objects.filter(empleado__in=personal_permitido, estado="aprobada").count(),
            "licencias": conteo_licencias,
            "sanciones": sanciones_hoy,
            "asistencia_hoy": asistencia_hoy, # Enviamos el dato real al template
        },
        "movimientos": Movimiento.objects.filter(empleado__in=personal_permitido).order_by("-fecha")[:5],
    }
    return render(request, "rrhh/dashboard.html", context)