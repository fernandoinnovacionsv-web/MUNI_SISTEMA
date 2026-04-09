import io
import pandas as pd
import csv
import platform
import pdfkit
import os
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string

from ..models import (
    Empleado, Movimiento, DocumentoEmpleado, 
    Hijo, Conyuge, Sector, Categoria, CondicionLaboral, TipoMovimiento
)
from ..forms import (
    EmpleadoForm, ConyugeForm, HijoFormSet, 
    DocumentoFormSet, IndumentariaFormSet, MovimientoForm
)

from ..utils import obtener_personal_permitido
from innovacion.decorators import tiene_funcion # <--- EL CANDADO

# --- CONFIGURACIÓN PDFKIT ---
if platform.system() == "Windows":
    rutas_probables = [
        r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
        r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
    ]
    path_wkhtmltopdf = None
    import os
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
    "page-size": "A4",
    "margin-top": "10mm",
    "margin-right": "10mm",
    "margin-bottom": "10mm",
    "margin-left": "10mm",
    "encoding": "UTF-8",
    "enable-local-file-access": None,
    "quiet": "",
}

@login_required
@tiene_funcion('rrhh_ver_personal')
def personal_list(request):
    q = request.GET.get("q", "")
    empleados = obtener_personal_permitido(request.user).order_by("-id")
    if q:
        empleados = empleados.filter(
            Q(dni__icontains=q) | Q(legajo__icontains=q) | 
            Q(apellido__icontains=q) | Q(nombre__icontains=q)
        )
    return render(request, "rrhh/personal/personal_list.html", {"empleados": empleados, "q": q})

@login_required
@tiene_funcion('rrhh_crear_personal') # También aplica para editar según tu esquema
def personal_wizard(request, pk=None):
    is_edit = pk is not None
    # Si es edición, verificamos el permiso específico de edición
    if is_edit:
        # Podrías usar un segundo permiso aquí si quisieras separar Crear de Editar
        pass

    empleado = get_object_or_404(Empleado, pk=pk) if is_edit else None
    conyuge_inicial = getattr(empleado, "conyuge", None)

    if request.method == "POST":
        empleado_form = EmpleadoForm(request.POST, request.FILES, instance=empleado, prefix='emp')
        conyuge_form = ConyugeForm(request.POST, instance=conyuge_inicial, prefix='conyuge')
        hijos_formset = HijoFormSet(request.POST, instance=empleado, prefix='hijos')
        documentos_formset = DocumentoFormSet(request.POST, request.FILES, instance=empleado, prefix='docs')
        indumentaria_formset = IndumentariaFormSet(request.POST, instance=empleado, prefix='indum')

        if all([empleado_form.is_valid(), conyuge_form.is_valid(), hijos_formset.is_valid(), 
                documentos_formset.is_valid(), indumentaria_formset.is_valid()]):
            try:
                with transaction.atomic():
                    empleado = empleado_form.save()
                    
                    cd_conyuge = conyuge_form.cleaned_data
                    if cd_conyuge.get("dni") or cd_conyuge.get("apellido") or cd_conyuge.get("nombre"):
                        conyuge_obj = conyuge_form.save(commit=False)
                        conyuge_obj.empleado = empleado
                        conyuge_obj.save()
                    elif conyuge_inicial:
                        conyuge_inicial.delete()

                    for fs in [hijos_formset, documentos_formset, indumentaria_formset]:
                        fs.instance = empleado
                        fs.save()

                    if not is_edit:
                        tipo_mov, _ = TipoMovimiento.objects.get_or_create(nombre="ALTA")
                        detalle_mov = "Alta inicial registrada mediante Formulario de Personal."
                    else:
                        tipo_mov, _ = TipoMovimiento.objects.get_or_create(nombre="MODIFICACION")
                        detalle_mov = "Actualización de datos del agente mediante Formulario de Personal."
                    
                    Movimiento.objects.create(
                        tipo=tipo_mov, 
                        empleado=empleado, 
                        usuario=request.user,
                        detalle=detalle_mov
                    )
                    
                    messages.success(request, f"Personal {'actualizado' if is_edit else 'registrado'} con éxito.")
                    return redirect("rrhh:personal_list")
            except Exception as e:
                messages.error(request, f"Error al procesar el formulario: {e}")
    else:
        empleado_form = EmpleadoForm(instance=empleado, prefix='emp')
        conyuge_form = ConyugeForm(instance=conyuge_inicial, prefix='conyuge')
        hijos_formset = HijoFormSet(instance=empleado, prefix='hijos')
        documentos_formset = DocumentoFormSet(instance=empleado, prefix='docs')
        indumentaria_formset = IndumentariaFormSet(instance=empleado, prefix='indum')

    context = {
        'empleado_form': empleado_form,
        'conyuge_form': conyuge_form,
        'hijos_formset': hijos_formset,
        'documentos_formset': documentos_formset,
        'indumentaria_formset': indumentaria_formset,
        'is_edit': is_edit,
        'empleado': empleado,
        'sectores': Sector.objects.filter(padre__isnull=True),
        'categorias': Categoria.objects.all(),
        'condiciones': CondicionLaboral.objects.all(),
    }
    return render(request, "rrhh/personal/personal_wizard.html", context)

@login_required
@tiene_funcion('rrhh_crear_personal')
def personal_create(request): 
    return personal_wizard(request)

@login_required
@tiene_funcion('rrhh_editar_personal')
def personal_edit(request, pk): 
    return personal_wizard(request, pk=pk)

@login_required
@tiene_funcion('rrhh_detalle_personal')
def personal_detalle(request, pk):
    emp = get_object_or_404(Empleado, pk=pk)
    movimientos = Movimiento.objects.filter(empleado=emp).order_by("-fecha")
    documentos = DocumentoEmpleado.objects.filter(empleado=emp)
    hijos = Hijo.objects.filter(empleado=emp)
    conyuge = getattr(emp, "conyuge", None)
    return render(request, "rrhh/personal/personal_detalle.html", locals())

@login_required
@tiene_funcion('rrhh_detalle_personal')
def personal_detalle_pdf(request, pk):
    emp = get_object_or_404(Empleado, pk=pk)
    context = {
        "emp": emp,
        "movimientos": Movimiento.objects.filter(empleado=emp).order_by("-fecha"),
        "documentos": DocumentoEmpleado.objects.filter(empleado=emp),
        "hijos": Hijo.objects.filter(empleado=emp),
        "conyuge": getattr(emp, "conyuge", None),
    }
    html = render_to_string("rrhh/PDF/personal_detalle_pdf.html", context)
    pdf = pdfkit.from_string(html, False, options=PDF_OPTIONS, configuration=PDFKIT_CONFIG)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="ficha_{emp.dni}.pdf"'
    return response

@login_required
@tiene_funcion('rrhh_baja_personal')
def personal_alta(request, pk):
    emp = get_object_or_404(Empleado, pk=pk)
    emp.activo = True
    emp.save()
    tipo_alta, _ = TipoMovimiento.objects.get_or_create(nombre="ALTA")
    Movimiento.objects.create(tipo=tipo_alta, empleado=emp, usuario=request.user, detalle="Re-activación de personal")
    messages.success(request, f"Empleado {emp} dado de alta.")
    return redirect("rrhh:personal_list")

@login_required
@tiene_funcion('rrhh_baja_personal')
def personal_baja(request, pk):
    emp = get_object_or_404(Empleado, pk=pk)
    emp.activo = False
    emp.save()
    tipo_baja, _ = TipoMovimiento.objects.get_or_create(nombre="BAJA")
    Movimiento.objects.create(tipo=tipo_baja, empleado=emp, usuario=request.user, detalle="Baja de personal")
    messages.warning(request, f"Empleado {emp} dado de baja.")
    return redirect("rrhh:personal_list")

@login_required
@tiene_funcion('rrhh_ver_movimientos')
def movimientos_list(request):
    personal_permitido = obtener_personal_permitido(request.user)
    movs = Movimiento.objects.filter(empleado__in=personal_permitido).select_related("empleado", "tipo", "usuario").order_by("-fecha")
    return render(request, "rrhh/personal/movimientos_list.html", {"movimientos": movs})

@login_required
@tiene_funcion('rrhh_crear_movimiento')
def movimiento_create(request):
    if request.method == "POST":
        form = MovimientoForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.usuario = request.user
            mov.save()
            return redirect("rrhh:movimientos_list")
    else:
        form = MovimientoForm()
    return render(request, "rrhh/personal/movimiento_form.html", {"form": form})

@login_required
@tiene_funcion('rrhh_exportar_excel')
def personal_export(request):
    empleados = obtener_personal_permitido(request.user).order_by("apellido")
    
    data = []
    for e in empleados:
        data.append({
            "Legajo": e.legajo,
            "DNI": e.dni,
            "Apellido": e.apellido,
            "Nombre": e.nombre,
            "Sector": e.sector.nombre if e.sector else "-",
            "Área": e.subsector.nombre if e.subsector else "-",
            "Activo": "SÍ" if e.activo else "NO"
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Personal')
    
    output.seek(0)
    
    response = HttpResponse(
        output.read(), 
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="personal_municipal.xlsx"'
    return response