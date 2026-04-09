from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta, datetime, date
from django.db.models import Sum, F, DecimalField
from decimal import Decimal
import pandas as pd
from django.http import HttpResponse
from django.template.loader import render_to_string
import pdfkit
import platform
import os

# Configuración PDFKit (Búsqueda robusta en Windows)
if platform.system() == "Windows":
    rutas_probables = [
        r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
        r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
    ]
    path_wkhtmltopdf = None
    for r in rutas_probables:
        if os.path.exists(r):
            path_wkhtmltopdf = r
            break
    if path_wkhtmltopdf:
        PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    else:
        PDFKIT_CONFIG = pdfkit.configuration()
else:
    PDFKIT_CONFIG = pdfkit.configuration()

PDF_OPTIONS = {
    'page-size': 'A4',
    'encoding': "UTF-8",
    'enable-local-file-access': None,
    'quiet': '',
}

from rrhh.models import Empleado, Sector, RegistroHoraExtra, TransaccionBancoHoras, FrancoProgramado, RegistroAsistencia
from innovacion.decorators import tiene_funcion


@login_required
@tiene_funcion('rrhh_cargar_hs_extras')
def registro_horas_extras(request, sector_id):
    from rrhh.models import Sector, Empleado, TransaccionBancoHoras, Feriado, RegistroHoraExtra
    import math
    
    sector = get_object_or_404(Sector, id=sector_id)
    
    # Validamos que el usuario logueado tenga permiso sobre ese sector 
    try:
        perfil = request.user.perfil_innovacion
        sector_usuario = perfil.empleado.sector
        subsector_usuario = perfil.empleado.subsector
        
        es_admin = getattr(request, 'user_funciones', []) and 'acceso_innovacion_admin' in getattr(request, 'user_funciones', [])
        
        if not es_admin and sector.id != sector_usuario.id and (not subsector_usuario or sector.id != subsector_usuario.id):
             messages.error(request, "No tienes permisos para cargar horas extras en este sector.")
             return redirect('rrhh:dashboard_rrhh')
             
    except Exception:
        messages.error(request, "Tu usuario no posee un perfil de empleado vinculado.")
        return redirect('rrhh:dashboard_rrhh')

    personal = Empleado.objects.filter(sector=sector, activo=True)
    hoy = timezone.now().date()
    
    # Cargamos todos los feriados para la clasificación
    feriados = Feriado.objects.values_list('fecha', flat=True)
    
    for emp in personal:
        # Calcular los balances generados
        generadas = emp.transacciones_banco.filter(tipo='HORA_EXTRA', cantidad__gt=0)
        tot_lv = 0.0
        tot_sab = 0.0
        tot_dom_fer = 0.0
        
        for tx in generadas:
            cantidad = float(tx.cantidad)
            # Lunes a Viernes es 0 a 4, Sabado = 5, Domingo = 6
            if tx.fecha in feriados or tx.fecha.weekday() == 6:
                tot_dom_fer += cantidad
            elif tx.fecha.weekday() == 5:
                tot_sab += cantidad
            else:
                tot_lv += cantidad
                
        # Total consumido
        consumidas_franco = abs(float(emp.transacciones_banco.filter(tipo='FRANCO', cantidad__lt=0).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0))
        consumidas_pago = abs(float(emp.transacciones_banco.filter(tipo='PAGO', cantidad__lt=0).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0))
        consumidas_ajuste = abs(float(emp.transacciones_banco.filter(tipo='AJUSTE', cantidad__lt=0).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0))
        
        rem_lv = tot_lv
        rem_sab = tot_sab
        rem_dom = tot_dom_fer
        
        # 1. Pago consume Dom -> Sab -> L-V
        pago_rest = consumidas_pago
        d_pago = min(rem_dom, pago_rest)
        rem_dom -= d_pago
        pago_rest -= d_pago
        
        s_pago = min(rem_sab, pago_rest)
        rem_sab -= s_pago
        pago_rest -= s_pago
        
        l_pago = min(rem_lv, pago_rest)
        rem_lv -= l_pago
        pago_rest -= l_pago
        
        # 2. Franco y Ajuste consumen L-V -> Sab -> Dom
        franco_rest = consumidas_franco + consumidas_ajuste
        l_fran = min(rem_lv, franco_rest)
        rem_lv -= l_fran
        franco_rest -= l_fran
        
        s_fran = min(rem_sab, franco_rest)
        rem_sab -= s_fran
        franco_rest -= s_fran
        
        d_fran = min(rem_dom, franco_rest)
        rem_dom -= d_fran
        franco_rest -= d_fran
        
        emp.rem_lv = max(0, rem_lv)
        emp.rem_sab = max(0, rem_sab)
        emp.rem_dom = max(0, rem_dom)

        # Mes actual (simplemente lo totalizamos para mostrar)
        emp.horas_acumuladas = float(emp.transacciones_banco.filter(
            fecha__year=hoy.year, fecha__month=hoy.month
        ).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0)
        
        # Saldo histórico total
        emp.saldo_banco = float(emp.transacciones_banco.aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0)
        
        # Redondeo pro-empleado si hubiera liquidación hoy
        emp.saldo_entero = math.ceil(emp.saldo_banco) if emp.saldo_banco > 0 else 0

    if request.method == 'POST':
        # Procesar nueva hora extra manual si fuera necesario (modalHoraExtra)
        # Esto está mantenido tal cual estaba en la vista original
        empleado_id = request.POST.get('empleado_id')
        fecha_str = request.POST.get('fecha')
        hora_inicio_str = request.POST.get('hora_inicio')
        hora_fin_str = request.POST.get('hora_fin')
        detalle = request.POST.get('detalle', 'Horas Extras ingresadas')
        
        if empleado_id and fecha_str and hora_inicio_str and hora_fin_str:
            try:
                emp = Empleado.objects.get(id=empleado_id)
                
                # Parsear fechas y horas
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                h_ini = datetime.strptime(hora_inicio_str, "%H:%M").time()
                h_fin = datetime.strptime(hora_fin_str, "%H:%M").time()

                # Calcular la diferencia en horas
                dt_ini = datetime.combine(fecha, h_ini)
                dt_fin = datetime.combine(fecha, h_fin)
                
                # Si la hora fin es menor a la hora inicio, suponemos que cruzó la medianoche
                if dt_fin < dt_ini:
                    dt_fin += timedelta(days=1)
                
                diferencia = dt_fin - dt_ini
                horas_totales = diferencia.total_seconds() / 3600.0
                
                from rrhh.utils import verificar_solapamiento
                if verificar_solapamiento(emp, fecha, h_ini.strftime('%H:%M'), h_fin.strftime('%H:%M')):
                    messages.error(request, "Las horas ingresadas se solapan con un registro existente.")
                else:
                    registro_he = RegistroHoraExtra.objects.create(
                        empleado=emp,
                        fecha=fecha,
                        hora_inicio=h_ini,
                        hora_fin=h_fin,
                        horas_totales=round(horas_totales, 2),
                        motivo_actividad=detalle,
                        registrado_por=request.user
                    )
                    
                    # Alimentamos el Banco de Horas
                    TransaccionBancoHoras.objects.create(
                        empleado=emp,
                        fecha=fecha,
                        cantidad=round(horas_totales, 2),
                        tipo='HORA_EXTRA',
                        referencia_id=registro_he.id,
                        detalle=f"Carga de Horas Extras: {detalle}"
                    )
                    
                    messages.success(request, f"Se sumaron {round(horas_totales, 2)} hs al banco de {emp.get_short_name()}.")
            except Exception as e:
                messages.error(request, f"Ocurrió un error: {e}")
        return redirect(f"{request.path}")

    return render(request, 'rrhh/asistencia/registro_horas_extras.html', {
        'personal': personal,
        'sector': sector,
        'hoy': hoy,
        'mes_actual': hoy.strftime("%B").capitalize() # Para mostrar el nombre del mes
    })



@login_required
@tiene_funcion('rrhh_reporte_hs_extras')
def exportar_horas_extras_pdf(request, sector_id):
    """Genera un archivo PDF con el reporte de horas extras del mes actual o rango asignado"""
    from rrhh.models import Feriado
    sector = get_object_or_404(Sector, id=sector_id)
    hoy = timezone.now().date()
    
    fecha_desde_str = request.GET.get('fecha_desde')
    fecha_hasta_str = request.GET.get('fecha_hasta')

    # Parse parameters or default to current month
    if fecha_desde_str and fecha_hasta_str:
        fecha_desde = datetime.strptime(fecha_desde_str, "%Y-%m-%d").date()
        fecha_hasta = datetime.strptime(fecha_hasta_str, "%Y-%m-%d").date()
    else:
        fecha_desde = hoy.replace(day=1)
        proximo_mes = fecha_desde.replace(day=28) + timedelta(days=4)
        fecha_hasta = proximo_mes - timedelta(days=proximo_mes.day)

    # Listado de feriados para detección rápida
    feriados = Feriado.objects.filter(fecha__range=[fecha_desde, fecha_hasta]).values_list('fecha', flat=True)

    personal = Empleado.objects.filter(sector=sector, activo=True)
    reporte_data = []

    for emp in personal:
        registros = RegistroHoraExtra.objects.filter(
            empleado=emp, 
            fecha__range=[fecha_desde, fecha_hasta]
        ).order_by('fecha')
        
        if registros.exists():
            total_sem = 0.0
            total_sab = 0.0
            total_dom_fer = 0.0
            
            for reg in registros:
                # Determinar categoría
                es_feriado = reg.fecha in feriados
                dia_semana = reg.fecha.weekday() # 0=Mon, 5=Sat, 6=Sun
                
                if es_feriado or dia_semana == 6:
                    total_dom_fer += float(reg.horas_totales)
                    reg.categoria = 'dom_fer'
                elif dia_semana == 5:
                    total_sab += float(reg.horas_totales)
                    reg.categoria = 'sab'
                else:
                    total_sem += float(reg.horas_totales)
                    reg.categoria = 'semana'

            # Saldo anterior al periodo consultado
            saldo_anterior = TransaccionBancoHoras.objects.filter(
                empleado=emp,
                fecha__lt=fecha_desde
            ).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0
            
            # --- CALCULO BALANCES HISTÓRICOS TOTALES DISPONIBLES (Para Liquidación final) ---
            generadas = emp.transacciones_banco.filter(tipo='HORA_EXTRA', cantidad__gt=0)
            tot_lv = 0.0; tot_sab = 0.0; tot_dom_f = 0.0
            feriados_all = Feriado.objects.values_list('fecha', flat=True)
            for tx in generadas:
                cant = float(tx.cantidad)
                if tx.fecha in feriados_all or tx.fecha.weekday() == 6: tot_dom_f += cant
                elif tx.fecha.weekday() == 5: tot_sab += cant
                else: tot_lv += cant
                
            consumidas_franco = abs(float(emp.transacciones_banco.filter(tipo='FRANCO', cantidad__lt=0).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0))
            consumidas_pago = abs(float(emp.transacciones_banco.filter(tipo='PAGO', cantidad__lt=0).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0))
            consumidas_ajuste = abs(float(emp.transacciones_banco.filter(tipo='AJUSTE', cantidad__lt=0).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0))
            
            r_lv = tot_lv; r_sab = tot_sab; r_dom = tot_dom_f
            
            # 1. Pago consume Dom -> Sab -> L-V
            p_rest = consumidas_pago
            d_p = min(r_dom, p_rest); r_dom -= d_p; p_rest -= d_p
            s_p = min(r_sab, p_rest); r_sab -= s_p; p_rest -= s_p
            l_p = min(r_lv, p_rest); r_lv -= l_p; p_rest -= l_p
            
            # 2. Franco/Ajuste consumen L-V -> Sab -> Dom
            f_rest = consumidas_franco + consumidas_ajuste
            l_f = min(r_lv, f_rest); r_lv -= l_f; f_rest -= l_f
            s_f = min(r_sab, f_rest); r_sab -= s_f; f_rest -= s_f
            d_f = min(r_dom, f_rest); r_dom -= d_f; f_rest -= d_f
            
            rem_lv = max(0, r_lv); rem_sab = max(0, r_sab); rem_dom = max(0, r_dom)
            
            saldo_banco_total = float(emp.transacciones_banco.aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0)
            import math
            saldo_entero = math.ceil(saldo_banco_total) if saldo_banco_total > 0 else 0

            reporte_data.append({
                'empleado': emp,
                'registros': registros,
                'total_sem': total_sem,
                'total_sab': total_sab,
                'total_dom_fer': total_dom_fer,
                'total_periodo': total_sem + total_sab + total_dom_fer,
                'saldo_anterior': saldo_anterior,
                'rem_lv': rem_lv,
                'rem_sab': rem_sab,
                'rem_dom': rem_dom,
                'saldo_banco_total': saldo_banco_total,
                'saldo_entero': saldo_entero
            })

    context = {
        'sector': sector,
        'reporte_data': reporte_data,
        'fecha_actual': hoy,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }

    html = render_to_string("rrhh/asistencia/pdf_horas_extras.html", context)
    pdf = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG, options=PDF_OPTIONS)
    
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="Horas_Extras_{sector.nombre.replace(" ", "_")}_{fecha_desde}_al_{fecha_hasta}.pdf"'
    
    return response


# =====================================================
#  GESTIÓN DE BANCO DE HORAS
# =====================================================

@login_required
@tiene_funcion('rrhh_tomar_asistencia')
def programar_franco(request, empleado_id):
    """Programa uno o varios días de franco para un empleado y descuenta horas (mínimo 6hs) del banco."""
    empleado = get_object_or_404(Empleado, id=empleado_id)
    
    # Saldo histórico total
    saldo_actual = float(empleado.transacciones_banco.aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0)
    
    if request.method == 'POST':
        fecha_inicio_str = request.POST.get('fecha_inicio')
        fecha_hasta_str = request.POST.get('fecha_hasta')
        detalle = request.POST.get('detalle', 'Día de Franco acumulado')
        
        if fecha_inicio_str:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
                # Si no hay fecha_hasta, es un solo día
                if fecha_hasta_str:
                    fecha_hasta = datetime.strptime(fecha_hasta_str, "%Y-%m-%d").date()
                else:
                    fecha_hasta = fecha_inicio

                if fecha_hasta < fecha_inicio:
                    messages.error(request, "La fecha final no puede ser anterior a la inicial.")
                    return redirect(request.META.get('HTTP_REFERER', 'rrhh:dashboard_rrhh'))

                dias_procesados = 0
                delta = timedelta(days=1)
                curr_fecha = fecha_inicio
                
                while curr_fecha <= fecha_hasta:
                    # Chequear saldo
                    if saldo_actual < 6.0:
                        messages.warning(request, f"Se detuvo la programación el {curr_fecha} por falta de saldo en banco (mínimo 6hs).")
                        break
                    # 1. Crear el Franco Programado (para bloquear la asistencia)
                    # Usamos update_or_create para evitar duplicados si se carga dos veces el mismo rango
                    FrancoProgramado.objects.update_or_create(
                        empleado=empleado,
                        fecha=curr_fecha,
                        defaults={'registrado_por': request.user}
                    )
                    
                    # 2. Descontar las 6hs del Banco implicando prioridad de consumo en detalle
                    TransaccionBancoHoras.objects.create(
                        empleado=empleado,
                        fecha=curr_fecha,
                        cantidad=-6.0,
                        tipo='FRANCO',
                        detalle=f"{detalle} (Día {curr_fecha}). Descuento prioritario 100% L-V."
                    )
                    
                    saldo_actual -= 6.0
                    
                    curr_fecha += delta
                    dias_procesados += 1
                
                total_horas = dias_procesados * 6.0
                messages.success(request, f"Se programaron {dias_procesados} días de franco para {empleado.get_full_name()}. Total descontado: {total_horas} hs.")
            except Exception as e:
                messages.error(request, f"Error al programar francos: {str(e)}")
        
    return redirect(request.META.get('HTTP_REFERER', 'rrhh:dashboard_rrhh'))

@login_required
@tiene_funcion('rrhh_tomar_asistencia')
def registrar_pago_horas(request, empleado_id):
    """Registra que se le pagaron X horas al personal y las descuenta del banco"""
    empleado = get_object_or_404(Empleado, id=empleado_id)
    
    if request.method == 'POST':
        cantidad = request.POST.get('cantidad_horas')
        detalle = request.POST.get('detalle', 'Pago de horas extras')
        fecha_str = request.POST.get('fecha', timezone.now().date().strftime("%Y-%m-%d"))
        
        if cantidad:
            try:
                cant = float(cantidad.replace(',', '.'))
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                
                TransaccionBancoHoras.objects.create(
                    empleado=empleado,
                    fecha=fecha,
                    cantidad=-cant, # Negativo porque se resta del "haber"
                    tipo='PAGO',
                    detalle=f"{detalle}. Descuento prioritario 200% Dom/Fer."
                )
                
                messages.success(request, f"Se registraron {cant} hs pagadas para {empleado.get_full_name()}.")
            except Exception as e:
                messages.error(request, f"Error al registrar pago: {str(e)}")
                
    return redirect(request.META.get('HTTP_REFERER', 'rrhh:dashboard_rrhh'))

@login_required
@tiene_funcion('rrhh_descargar_asistencia')
def exportar_asistencia_pdf(request, sector_id):
    """Genera un archivo PDF con el reporte de asistencias del personal de un sector"""
    sector = get_object_or_404(Sector, id=sector_id)
    hoy = timezone.now().date()
    
    fecha_desde_str = request.GET.get('fecha_desde')
    fecha_hasta_str = request.GET.get('fecha_hasta')

    if fecha_desde_str and fecha_hasta_str:
        fecha_desde = datetime.strptime(fecha_desde_str, "%Y-%m-%d").date()
        fecha_hasta = datetime.strptime(fecha_hasta_str, "%Y-%m-%d").date()
    else:
        fecha_desde = hoy.replace(day=1)
        proximo_mes = fecha_desde.replace(day=28) + timedelta(days=4)
        fecha_hasta = proximo_mes - timedelta(days=proximo_mes.day)

    # 1. Listado de días laborales (Excluyendo sábados, domingos y feriados)
    from rrhh.models import Feriado, FrancoProgramado
    feriados = set(Feriado.objects.filter(fecha__range=[fecha_desde, fecha_hasta]).values_list('fecha', flat=True))
    
    dias_laborales = []
    curr = fecha_desde
    while curr <= fecha_hasta:
        # 0=Lunes, 6=Domingo. Laboral = 0-4 (Lun a Vie)
        if curr.weekday() < 5 and curr not in feriados:
            dias_laborales.append(curr)
        curr += timedelta(days=1)
    
    total_laborales = len(dias_laborales)

    personal = Empleado.objects.filter(sector=sector, activo=True).order_by('apellido', 'nombre')
    reporte_data = []

    for emp in personal:
        # Mapa de asistencias cargadas
        asistencias_query = RegistroAsistencia.objects.filter(
            empleado=emp,
            fecha__range=[fecha_desde, fecha_hasta]
        )
        asistencias_map = { a.fecha: a.estado for a in asistencias_query }
        
        # Francos en el rango
        francos_fechas = set(FrancoProgramado.objects.filter(
            empleado=emp,
            fecha__range=[fecha_desde, fecha_hasta]
        ).values_list('fecha', flat=True))

        # Contadores de estados (Solo sobre días laborales)
        totales = {
            'PRESENTE': 0,
            'FRANCO': 0,
            'AUSENTE_CON_AVISO': 0,
            'AUSENTE_SIN_AVISO': 0,
            'TARDANZA': 0,
        }

        for dia in dias_laborales:
            if dia in francos_fechas:
                totales['FRANCO'] += 1
            elif dia in asistencias_map:
                estado = asistencias_map[dia]
                if estado in totales:
                    totales[estado] += 1
                elif estado == 'LICENCIA' or estado == 'SANCION':
                    # Podríamos sumarlos a Franco o a una nueva columna, pero 
                    # el reporte actual no tiene esas columnas. Los dejamos como "Justificado" (Presente simbólico)
                    # o simplemente no los restamos de la asistencia si el usuario no los pidió.
                    # Para no complicar, si no es ausencia ni tardanza, es "Presente"
                    totales['PRESENTE'] += 1
                else:
                    totales['PRESENTE'] += 1
            else:
                # SI NO HAY REGISTRO -> PRESENTE (Por defecto al cerrar mes)
                totales['PRESENTE'] += 1

        reporte_data.append({
            'empleado': emp,
            'totales': totales,
            'total_dias': total_laborales
        })

    context = {

        'sector': sector,
        'reporte_data': reporte_data,
        'fecha_actual': hoy,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }

    html = render_to_string("rrhh/asistencia/pdf_asistencia.html", context)
    pdf = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG, options=PDF_OPTIONS)
    
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="Asistencia_{sector.nombre.replace(" ", "_")}_{fecha_desde}_al_{fecha_hasta}.pdf"'
    
    return response

@login_required
@tiene_funcion('rrhh_descargar_asistencia')
def exportar_asistencia_excel(request, sector_id):
    """Genera un archivo Excel con el resumen de asistencias (similar al PDF)"""
    from rrhh.models import Feriado, FrancoProgramado
    sector = get_object_or_404(Sector, id=sector_id)
    hoy = timezone.now().date()
    
    fecha_desde_str = request.GET.get('fecha_desde')
    fecha_hasta_str = request.GET.get('fecha_hasta')

    if fecha_desde_str and fecha_hasta_str:
        fecha_desde = datetime.strptime(fecha_desde_str, "%Y-%m-%d").date()
        fecha_hasta = datetime.strptime(fecha_hasta_str, "%Y-%m-%d").date()
    else:
        fecha_desde = hoy.replace(day=1)
        proximo_mes = fecha_desde.replace(day=28) + timedelta(days=4)
        fecha_hasta = proximo_mes - timedelta(days=proximo_mes.day)

    feriados = set(Feriado.objects.filter(fecha__range=[fecha_desde, fecha_hasta]).values_list('fecha', flat=True))
    dias_laborales = []
    curr = fecha_desde
    while curr <= fecha_hasta:
        if curr.weekday() < 5 and curr not in feriados:
            dias_laborales.append(curr)
        curr += timedelta(days=1)
    
    total_laborales = len(dias_laborales)
    personal = Empleado.objects.filter(sector=sector, activo=True).order_by('apellido', 'nombre')
    
    data = []
    for emp in personal:
        asistencias_map = { a.fecha: a.estado for a in RegistroAsistencia.objects.filter(empleado=emp, fecha__range=[fecha_desde, fecha_hasta]) }
        francos_fechas = set(FrancoProgramado.objects.filter(empleado=emp, fecha__range=[fecha_desde, fecha_hasta]).values_list('fecha', flat=True))

        totales = {'PRESENTE': 0, 'FRANCO': 0, 'AUSENTE_CON_AVISO': 0, 'AUSENTE_SIN_AVISO': 0, 'TARDANZA': 0}

        for dia in dias_laborales:
            if dia in francos_fechas: totales['FRANCO'] += 1
            elif dia in asistencias_map:
                estado = asistencias_map[dia]
                if estado in totales: totales[estado] += 1
                else: totales['PRESENTE'] += 1
            else: totales['PRESENTE'] += 1

        data.append({
            'Legajo': emp.legajo,
            'Apellido': emp.apellido,
            'Nombre': emp.nombre,
            'Presente': totales['PRESENTE'],
            'Franco': totales['FRANCO'],
            'Ausente C/A': totales['AUSENTE_CON_AVISO'],
            'Ausente S/A': totales['AUSENTE_SIN_AVISO'],
            'Tardanza': totales['TARDANZA'],
            'Total Dias Hábiles': total_laborales
        })
        
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Resumen_Asistencia_{sector.nombre.replace(" ", "_")}.xlsx"'
    df.to_excel(response, index=False)
    return response

@login_required
@tiene_funcion('rrhh_cierre_mes')
def cerrar_mes_asistencia(request, sector_id):
    if request.method == 'POST':
        # Capturamos el mes y año que se desea cerrar (enviados desde el modal)
        anio = int(request.POST.get('anio', 0))
        mes = int(request.POST.get('mes', 0))
        hoy = timezone.now().date()
        
        if not anio or not mes:
            messages.error(request, "Mes o año no especificado.")
            return redirect('rrhh:toma_asistencia')

        # 1. Validación: No cerrar meses futuros
        if anio >= hoy.year and mes > hoy.month:
            messages.error(request, "No puedes cerrar un mes futuro.")
            return redirect('rrhh:toma_asistencia')

        # 2. Validación: No permitir saltarse meses (deben estar cerrados todos los anteriores)
        # Buscamos si hay registros previos al mes solicitado que no estén bloqueados
        from django.db.models import Min
        fecha_objetivo = date(anio, mes, 1)
        
        existen_previos_abiertos = RegistroAsistencia.objects.filter(
            empleado__sector_id=sector_id,
            fecha__lt=fecha_objetivo,
            bloqueado=False
        ).exists()
        
        if existen_previos_abiertos:
            messages.error(request, f"No puedes cerrar {mes}/{anio} porque aún existen registros abiertos en meses anteriores.")
            return redirect('rrhh:toma_asistencia')

        # 3. Proceder al cierre
        registros = RegistroAsistencia.objects.filter(
            empleado__sector_id=sector_id,
            fecha__year=anio,
            fecha__month=mes,
            bloqueado=False
        )
        
        if not registros.exists():
            messages.info(request, f"No se encontraron registros abiertos para {mes}/{anio}.")
            return redirect('rrhh:toma_asistencia')
            
        actualizados = registros.update(bloqueado=True)
        messages.success(request, f"Se han cerrado y bloqueado {actualizados} registros del mes {mes}/{anio}.")
    return redirect('rrhh:toma_asistencia')

@login_required
@tiene_funcion('rrhh_liquidacion_hs_extras')
def liquidar_horas(request, sector_id):
    from rrhh.models import Sector, Empleado, TransaccionBancoHoras, Feriado
    import math

    sector = get_object_or_404(Sector, id=sector_id)
    personal = Empleado.objects.filter(sector=sector, activo=True)
    hoy = timezone.now().date()
    feriados_all = Feriado.objects.values_list('fecha', flat=True)

    for emp in personal:
        # --- Cálculo de Balances (Copia de lógica existente) ---
        generadas = emp.transacciones_banco.filter(tipo='HORA_EXTRA', cantidad__gt=0)
        tot_lv = 0.0; tot_sab = 0.0; tot_dom_f = 0.0
        for tx in generadas:
            cant = float(tx.cantidad)
            if tx.fecha in feriados_all or tx.fecha.weekday() == 6: tot_dom_f += cant
            elif tx.fecha.weekday() == 5: tot_sab += cant
            else: tot_lv += cant
            
        consumidas_franco = abs(float(emp.transacciones_banco.filter(tipo='FRANCO', cantidad__lt=0).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0))
        consumidas_pago = abs(float(emp.transacciones_banco.filter(tipo='PAGO', cantidad__lt=0).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0))
        consumidas_ajuste = abs(float(emp.transacciones_banco.filter(tipo='AJUSTE', cantidad__lt=0).aggregate(Sum('cantidad'))['cantidad__sum'] or 0.0))
        
        r_lv = tot_lv; r_sab = tot_sab; r_dom = tot_dom_f
        
        # 1. Pago consume Dom -> Sab -> L-V
        p_rest = consumidas_pago
        d_p = min(r_dom, p_rest); r_dom -= d_p; p_rest -= d_p
        s_p = min(r_sab, p_rest); r_sab -= s_p; p_rest -= s_p
        l_p = min(r_lv, p_rest); r_lv -= l_p; p_rest -= l_p
        
        # 2. Franco/Ajuste consumen L-V -> Sab -> Dom
        f_rest = consumidas_franco + consumidas_ajuste
        l_f = min(r_lv, f_rest); r_lv -= l_f; f_rest -= l_f
        s_f = min(r_sab, f_rest); r_sab -= s_f; f_rest -= s_f
        d_f = min(r_dom, f_rest); r_dom -= d_f; f_rest -= d_f
        
        emp.rem_lv = max(0, r_lv)
        emp.rem_sab = max(0, r_sab)
        emp.rem_dom = max(0, r_dom)
        emp.total_balance = emp.rem_lv + emp.rem_sab + emp.rem_dom

    if request.method == 'POST':
        periodo = request.POST.get('periodo', hoy.strftime("%m/%Y"))
        modificados = 0
        
        for emp in personal:
            # Capturamos cuánto queda para Franco
            franco_str = request.POST.get(f'franco_{emp.id}', '0').replace(',', '.')
            try:
                horas_franco = float(franco_str)
                total_disp = emp.total_balance
                
                if total_disp <= 0:
                    continue

                # Lo que se liquida (paga) es Total - Franco
                # El resto (Franco) queda en el banco para uso futuro, NO se descuenta ahora.
                horas_pagar = max(0, total_disp - horas_franco)
                
                if horas_pagar > 0:
                    # Desglose para el reporte (Dom -> Sab -> LV)
                    p_rest = horas_pagar
                    p_dom = min(emp.rem_dom, p_rest); p_rest -= p_dom
                    p_sab = min(emp.rem_sab, p_rest); p_rest -= p_sab
                    p_lv = min(emp.rem_lv, p_rest); p_rest -= p_lv
                    
                    detalle_pago = f"Liquidación Mes {periodo}. [LV:{p_lv:.1f}|S:{p_sab:.1f}|DF:{p_dom:.1f}]"

                    # Generar transacción de PAGO
                    TransaccionBancoHoras.objects.create(
                        empleado=emp,
                        fecha=hoy,
                        cantidad=-horas_pagar,
                        tipo='PAGO',
                        detalle=detalle_pago
                    )
                    modificados += 1
            except ValueError:
                continue
        
        if modificados > 0:
            messages.success(request, f"Se procesó la liquidación de {modificados} empleados con éxito.")
        return redirect('rrhh:registro_horas_extras', sector_id=sector.id)

    return render(request, 'rrhh/asistencia/liquidar_horas.html', {
        'sector': sector,
        'personal': personal,
        'hoy': hoy
    })

@login_required
@tiene_funcion('rrhh_ver_personal')
def historial_asistencia_empleado(request, empleado_id):
    import calendar
    empleado = get_object_or_404(Empleado, id=empleado_id)
    
    # Manejo de mes y año
    hoy = timezone.now().date()
    mes = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))
    
    # Obtener el calendario del mes
    cal = calendar.Calendar(firstweekday=6) # Empieza en Domingo
    month_days = cal.monthdatescalendar(anio, mes)
    
    registros = RegistroAsistencia.objects.filter(
        empleado=empleado,
        fecha__year=anio,
        fecha__month=mes
    )
    asistencias_map = {r.fecha: r for r in registros}
    
    francos = set(FrancoProgramado.objects.filter(
        empleado=empleado,
        fecha__year=anio,
        fecha__month=mes
    ).values_list('fecha', flat=True))
    
    from rrhh.models import Feriado
    feriados = set(Feriado.objects.filter(
        fecha__year=anio,
        fecha__month=mes
    ).values_list('fecha', flat=True))

    # Cierre de mes: verificamos si hay algún registro bloqueado en el mes
    mes_cerrado = registros.filter(bloqueado=True).exists()
    
    # Estructura para el template y cálculo de días laborales
    calendar_data = []
    total_laborales = 0
    primer_dia_mes_actual = hoy.replace(day=1)
    
    for week in month_days:
        week_data = []
        for day in week:
            is_laboral = day.month == mes and day.weekday() < 5 and day not in feriados
            if is_laboral:
                total_laborales += 1
                
            day_info = {
                'date': day,
                'is_current_month': day.month == mes,
                'is_today': day == hoy,
                'asistencia': asistencias_map.get(day),
                'is_franco': day in francos,
                'is_feriado': day in feriados,
                'is_weekend': day.weekday() >= 5,
                'is_laboral': is_laboral,
            }
            week_data.append(day_info)
        calendar_data.append(week_data)

    months_list = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]

    return render(request, 'rrhh/asistencia/historial_empleado.html', {
        'empleado': empleado,
        'calendar_data': calendar_data,
        'mes_nombre': next(m[1] for m in months_list if m[0] == mes),
        'mes': mes,
        'anio': anio,
        'mes_cerrado': mes_cerrado,
        'total_laborales': total_laborales,
        'primer_dia_mes_actual': primer_dia_mes_actual,
        'months_list': months_list,
        'years_list': range(hoy.year - 5, hoy.year + 1), # Más rango hacia atrás
        'registros': registros.order_by('-fecha') # Para el detalle lateral
    })

@login_required
@tiene_funcion('rrhh_descargar_liquidaciones')
def exportar_liquidaciones_pdf(request, sector_id):
    from rrhh.models import Sector, Empleado, TransaccionBancoHoras
    from django.template.loader import render_to_string
    import pdfkit

    sector = get_object_or_404(Sector, id=sector_id)
    fecha_desde_str = request.GET.get('fecha_desde')
    fecha_hasta_str = request.GET.get('fecha_hasta')

    if not fecha_desde_str or not fecha_hasta_str:
        return HttpResponse("Faltan fechas de rango.", status=400)

    from datetime import datetime
    fecha_desde = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
    fecha_hasta = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()

    personal = Empleado.objects.filter(sector=sector, activo=True).distinct().order_by('apellido')
    data_reporte = []

    for emp in personal:
        pagos = TransaccionBancoHoras.objects.filter(
            empleado=emp,
            tipo='PAGO',
            fecha__range=[fecha_desde, fecha_hasta]
        )
        if pagos.exists():
            total_pagado = abs(sum(tx.cantidad for tx in pagos))
            
            total_lv = 0
            total_s = 0
            total_df = 0
            
            # Intentamos extraer el desglose de cada pago para el reporte
            for p in pagos:
                p.desglose = None
                if "[" in p.detalle and "]" in p.detalle:
                    try:
                        inner = p.detalle.split("[")[1].split("]")[0]
                        parts = inner.split("|")
                        desglose = {
                            'LV': float(parts[0].split(":")[1]),
                            'S': float(parts[1].split(":")[1]),
                            'DF': float(parts[2].split(":")[1])
                        }
                        p.desglose = desglose
                        total_lv += desglose['LV']
                        total_s += desglose['S']
                        total_df += desglose['DF']
                    except: pass

            data_reporte.append({
                'agente': emp,
                'pagos': pagos,
                'total_pagado': total_pagado,
                'total_lv': total_lv,
                'total_s': total_s,
                'total_df': total_df
            })

    html_string = render_to_string('rrhh/asistencia/pdf_liquidaciones.html', {
        'sector': sector,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'data_reporte': data_reporte,
        'hoy': timezone.now(),
    })

    # Configuración de pdfkit (Márgenes profesionales de 15mm)
    options = {
        'page-size': 'A4',
        'margin-top': '15mm',
        'margin-right': '15mm',
        'margin-bottom': '15mm',
        'margin-left': '15mm',
        'encoding': "UTF-8",
        'no-outline': None,
        'quiet': '',
        'enable-local-file-access': None,
    }
    
    try:
        # Usamos la configuración global definida al inicio del archivo
        pdf = pdfkit.from_string(html_string, False, options=options, configuration=PDFKIT_CONFIG)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Liquidacion_{sector.nombre.replace(" ", "_")}.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error al generar PDF: {str(e)}", status=500)
