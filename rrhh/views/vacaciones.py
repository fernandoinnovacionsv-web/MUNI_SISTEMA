import io
import csv
import pandas as pd
import pdfkit
import platform
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.template.loader import render_to_string
import os

from ..models import Vacacion, Empleado, Feriado, Movimiento, TipoMovimiento
from ..forms import VacacionForm, FeriadoForm
from ..utils import obtener_personal_permitido # <--- EL FILTRO
from innovacion.decorators import tiene_funcion  # Importamos el candado

# Configuración PDFKit
if platform.system() == "Windows":
    # Buscamos el ejecutable en rutas comunes de Windows
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
        PDFKIT_CONFIG = pdfkit.configuration() # Intentar que lo saque del PATH
else:
    PDFKIT_CONFIG = pdfkit.configuration()

PDF_OPTIONS = {
    'page-size': 'A4',
    'encoding': "UTF-8",
    'enable-local-file-access': None,
    'quiet': '',
}

@login_required
@tiene_funcion('rrhh_ver_vac_todas')
def vacaciones_list(request):
    personal_permitido = obtener_personal_permitido(request.user)
    vacaciones = Vacacion.objects.filter(empleado__in=personal_permitido).select_related("empleado").order_by("-fecha_inicio")
    return render(request, "rrhh/vacaciones/vacaciones_list.html", {"vacaciones": vacaciones})

@login_required
@tiene_funcion('rrhh_pedir_vacacion')
def vacacion_create(request):
    empleado_id = request.GET.get("empleado") or request.POST.get("empleado")
    anio = int(request.GET.get("anio") or date.today().year - 1)
    q = request.GET.get("q", "").strip()
    
    personal_permitido = obtener_personal_permitido(request.user)
    empleados = personal_permitido.filter(activo=True).order_by("apellido")
    if q:
        empleados = empleados.filter(Q(legajo__icontains=q) | Q(apellido__icontains=q))
    else:
        empleados = empleados[:20]

    empleado = get_object_or_404(Empleado, pk=empleado_id) if empleado_id else None
    saldo, corresponde, usados = 0, 0, 0
    
    if empleado:
        antig = empleado.antiguedad_anios
        corresponde = 15 if antig < 5 else 20 if antig < 10 else 25 if antig < 15 else 30
        usados = Vacacion.objects.filter(empleado=empleado, anio=anio).exclude(estado="rechazada").aggregate(total=Sum("dias_habiles"))["total"] or 0
        saldo = corresponde - usados

    if request.method == "POST":
        form = VacacionForm(request.POST, request.FILES)
        if form.is_valid():
            vac = form.save(commit=False)
            vac.dias_habiles = form.cleaned_data.get('dias_habiles', 0)
            vac.empleado = empleado
            vac.usuario = request.user
            vac.estado = "pendiente" # Siempre inicia en pendiente
            vac.save()
            messages.success(request, "Solicitud de vacaciones registrada. Pendiente de aval.")
            return redirect("rrhh:vacaciones_list")
    else:
        form = VacacionForm(initial={"empleado": empleado_id, "anio": anio})

    holidays_json = [f.strftime('%Y-%m-%d') for f in Feriado.objects.values_list('fecha', flat=True)]
    return render(request, "rrhh/vacaciones/vacacion_form.html", locals())

@login_required
def vacacion_aprobar(request, pk):
    vac = get_object_or_404(Vacacion, pk=pk)
    # Usamos las funciones cargadas por el Middleware
    funciones = getattr(request, 'user_funciones', [])
    
    # 1. Prioridad RRHH (Aprobación Final) - Puede aprobar si está pendiente o tiene visto bueno
    if 'rrhh_admin_vacacion' in funciones:
        if vac.estado in ["pendiente", "visto_bueno"]:
            vac.estado = "aprobada"
            vac.aprobado_por = request.user  # Guardamos quién aprobó
            vac.save()
            tipo_mov, _ = TipoMovimiento.objects.get_or_create(nombre="VACACIONES", defaults={"icono": "fa-plane"})
            Movimiento.objects.create(
                tipo=tipo_mov, 
                empleado=vac.empleado, 
                usuario=request.user, 
                detalle=f"Aprobación Final: {vac.fecha_inicio} al {vac.fecha_fin}"
            )
            messages.success(request, f"Vacación de {vac.empleado} aprobada definitivamente.")
        else:
            messages.warning(request, "Esta solicitud no puede ser aprobada en su estado actual.")
    
    # 2. Aval de Jefe (Solo si está pendiente)
    elif 'rrhh_aval_jefe' in funciones:
        if vac.estado == "pendiente":
            vac.estado = "visto_bueno"
            vac.save()
            tipo_mov, _ = TipoMovimiento.objects.get_or_create(nombre="VACACIONES", defaults={"icono": "fa-calendar-alt"})
            Movimiento.objects.create(
                tipo=tipo_mov, 
                empleado=vac.empleado, 
                usuario=request.user, 
                detalle=f"Aval de Jefe (Visto Bueno): {vac.fecha_inicio} al {vac.fecha_fin}"
            )
            messages.success(request, f"Visto Bueno otorgado a la solicitud de {vac.empleado}.")
        else:
            messages.warning(request, "La solicitud ya no está en estado pendiente.")
    
    else:
        messages.error(request, "No tienes permisos para realizar esta acción.")
        
    return redirect("rrhh:vacaciones_list")

@login_required
@tiene_funcion('rrhh_admin_vacacion')
def pdf_vacacion(request, pk):
    vac = get_object_or_404(Vacacion, pk=pk)
    if vac.estado != "aprobada":
        messages.error(request, "Solo se pueden generar comprobantes de vacaciones aprobadas.")
        return redirect("rrhh:vacaciones_list")
        
    empleado = vac.empleado
    antig = empleado.antiguedad_anios
    dias_correspondientes = 15 if antig < 5 else 20 if antig < 10 else 25 if antig < 15 else 30
    usados = Vacacion.objects.filter(empleado=empleado, anio=vac.anio).exclude(estado="rechazada").aggregate(total=Sum("dias_habiles"))["total"] or 0
    
    fecha_reintegro = vac.fecha_reintegro
    if not fecha_reintegro:
        dia_siguiente = vac.fecha_fin + timedelta(days=1)
        while dia_siguiente.weekday() in [5, 6]:
            dia_siguiente += timedelta(days=1)
        fecha_reintegro = dia_siguiente

    context = {
        "vacacion": vac,
        "empleado": empleado,
        "usuario": vac.aprobado_por or vac.usuario or request.user, # Prioridad al aprobador
        "fecha_actual": date.today(),
        "dias_correspondientes": dias_correspondientes,
        "dias_tomados": vac.dias_habiles,
        "saldo_restante": dias_correspondientes - usados,
        "fecha_reintegro": fecha_reintegro
    }
    
    html = render_to_string("rrhh/vacaciones/nota_vacaciones.html", context)
    pdf = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG, options=PDF_OPTIONS)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Vacaciones_{vac.empleado.apellido}.pdf"'
    return response

# --- GESTIÓN DE FERIADOS ---
@login_required
@tiene_funcion('rrhh_admin_feriados')
def feriados_list(request):
    feriados = Feriado.objects.all().order_by("fecha")
    form = FeriadoForm()
    return render(request, "rrhh/vacaciones/feriados_list.html", {"feriados": feriados, "form": form})

@login_required
@tiene_funcion('rrhh_admin_feriados')
def feriado_create(request):
    if request.method == "POST":
        form = FeriadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Feriado agregado.")
            return redirect("rrhh:feriados_list")
    else:
        form = FeriadoForm()
    return render(request, "rrhh/vacaciones/feriado_form.html", {"form": form})

@login_required
@tiene_funcion('rrhh_admin_feriados')
def feriado_delete(request, pk):
    get_object_or_404(Feriado, pk=pk).delete()
    messages.success(request, "Feriado eliminado.")
    return redirect("rrhh:feriados_list")

@login_required
@tiene_funcion('rrhh_pedir_vacacion')
def vacaciones_personal(request): 
    return vacacion_create(request)

@login_required
@tiene_funcion('rrhh_admin_vacacion')
def vacacion_edit(request, pk):
    vac = get_object_or_404(Vacacion, pk=pk)
    if request.method == "POST":
        form = VacacionForm(request.POST, request.FILES, instance=vac)
        if form.is_valid():
            form.save()
            messages.success(request, "Vacación actualizada.")
            return redirect("rrhh:vacaciones_list")
    else:
        form = VacacionForm(instance=vac)
    
    return render(request, "rrhh/vacaciones/vacacion_form.html", {"form": form, "edit": True})

@login_required
def vacacion_rechazar(request, pk):
    # El rechazo lo puede hacer tanto el Jefe como RRHH
    vac = get_object_or_404(Vacacion, pk=pk)
    vac.estado = "rechazada"
    vac.save()
    messages.warning(request, f"Vacación de {vac.empleado} rechazada.")
    return redirect("rrhh:vacaciones_list")

@login_required
@tiene_funcion('rrhh_admin_vacacion')
def nota_vacaciones(request, pk):
    return pdf_vacacion(request, pk)

@login_required
@tiene_funcion('rrhh_admin_feriados')
def feriado_editar(request, pk):
    feriado = get_object_or_404(Feriado, pk=pk)
    if request.method == "POST":
        form = FeriadoForm(request.POST, instance=feriado)
        if form.is_valid():
            form.save()
            messages.success(request, "Feriado actualizado.")
            return redirect("rrhh:feriados_list")
    else:
        form = FeriadoForm(instance=feriado)
    return render(request, "rrhh/vacaciones/feriado_form.html", {"form": form, "is_edit": True})

@login_required
@tiene_funcion('rrhh_import_feriados')
def feriado_import_excel(request):
    if request.method == "POST" and request.FILES.get("excel_file"):
        file = request.FILES["excel_file"]
        try:
            df = pd.read_excel(file)
            for _, row in df.iterrows():
                Feriado.objects.get_or_create(
                    fecha=row['fecha'], 
                    defaults={'nombre': row.get('nombre', row.get('descripcion', 'Feriado Importado'))}
                )
            messages.success(request, "Feriados importados con éxito.")
        except Exception as e:
            messages.error(request, f"Error al importar: {e}")
    return redirect("rrhh:feriados_list")

@login_required
@tiene_funcion('rrhh_import_feriados')
def feriado_plantilla(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="plantilla_feriados.csv"'
    writer = csv.writer(response)
    writer.writerow(['fecha', 'nombre'])
    writer.writerow(['2024-12-25', 'Navidad'])
    return response