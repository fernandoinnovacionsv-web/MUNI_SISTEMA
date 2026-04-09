import csv
import io
import pandas as pd
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Q
import pdfkit
import platform
import os
from django.template.loader import render_to_string

from rrhh.models import (
    Empleado, IndumentariaStock, EntregaIndumentaria,
    EmpleadoTalle, Movimiento, TipoMovimiento
)
from ..forms import IndumentariaStockForm
from ..utils import obtener_personal_permitido
from innovacion.decorators import tiene_funcion # <--- EL CANDADO

# Configuración PDFKit
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
    'margin-top': '0mm',
    'margin-right': '0mm',
    'margin-bottom': '0mm',
    'margin-left': '0mm',
    'encoding': "UTF-8",
    'enable-local-file-access': None,
    'no-outline': None
}

@login_required
@tiene_funcion('rrhh_ver_indumentaria')
def indumentaria_list(request):
    q = request.GET.get("q", "").strip()
    empleados = obtener_personal_permitido(request.user).filter(activo=True).order_by("apellido")
    if q:
        empleados = empleados.filter(Q(apellido__icontains=q) | Q(dni__icontains=q))
    return render(request, "rrhh/indumentaria/indumentaria_list.html", {"empleados": empleados, "q": q})

@login_required
@tiene_funcion('rrhh_ver_indumentaria')
def indumentaria_historial(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    entregas = EntregaIndumentaria.objects.filter(empleado=empleado).order_by("-fecha")
    stock = IndumentariaStock.objects.all().order_by("prenda")
    carrito = request.session.get("carrito_indumentaria", [])
    return render(request, "rrhh/indumentaria/indumentaria_historial.html", locals())

@login_required
@tiene_funcion('rrhh_entregar_ropa')
def indumentaria_carrito_add(request):
    if request.method == "POST":
        item = {
            "prenda": request.POST.get("prenda"),
            "talle": request.POST.get("talle"),
            "cantidad": int(request.POST.get("cantidad", 1))
        }
        carrito = list(request.session.get("carrito_indumentaria", [])) # Clonar para evitar problemas de referencia
        carrito.append(item)
        request.session["carrito_indumentaria"] = carrito
        request.session.modified = True
        
        # Redirección explícita si tenemos el ID del empleado
        emp_id = request.POST.get("empleado_id")
        if emp_id:
            return redirect("rrhh:indumentaria_historial", pk=emp_id)

    return redirect(request.META.get('HTTP_REFERER', 'rrhh:indumentaria_list'))

@login_required
@tiene_funcion('rrhh_entregar_ropa')
def indumentaria_confirmar(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    carrito = request.session.get("carrito_indumentaria", [])
    
    processed = 0
    for item in carrito:
        stock_item = IndumentariaStock.objects.filter(prenda__iexact=item['prenda'], talle__iexact=item['talle']).first()
        if stock_item and stock_item.cantidad >= item['cantidad']:
            stock_item.cantidad -= item['cantidad']
            stock_item.save()
            EntregaIndumentaria.objects.create(
                empleado=empleado, prenda=item['prenda'], talle=item['talle'], 
                cantidad=item['cantidad'], usuario=request.user
            )
            processed += 1
        else:
            messages.warning(request, f"No se pudo entregar {item['prenda']} (Talle {item['talle']}) por falta de stock.")
    
    if processed > 0:
        messages.success(request, f"Entrega de {processed} ítem(s) procesada correctamente.")
        # REGISTRO EN EL HISTORIAL DE MOVIMIENTOS
        tipo_indum = TipoMovimiento.objects.filter(nombre='INDUMENTARIA').first()
        if tipo_indum:
            Movimiento.objects.create(
                tipo=tipo_indum,
                empleado=empleado,
                usuario=request.user,
                detalle=f"Entrega de indumentaria: {processed} artículos."
            )
    
    request.session["carrito_indumentaria"] = []
    return redirect("rrhh:indumentaria_historial", pk=pk)

@login_required
@tiene_funcion('rrhh_admin_stock')
def indumentaria_stock_list(request):
    if request.method == "POST":
        form = IndumentariaStockForm(request.POST)
        if form.is_valid():
            prenda = form.cleaned_data['prenda']
            talle = form.cleaned_data['talle']
            cant = form.cleaned_data['cantidad']
            
            obj, created = IndumentariaStock.objects.get_or_create(
                prenda__iexact=prenda, talle__iexact=talle,
                defaults={'prenda': prenda, 'talle': talle, 'cantidad': cant}
            )
            if not created:
                obj.cantidad += cant
                obj.save()
            messages.success(request, "Stock actualizado exitosamente.")
            return redirect("rrhh:indumentaria_stock_list")
        else:
            messages.error(request, "Error al guardar el nuevo ítem. Revise los datos ingresados.")
            
    stock = IndumentariaStock.objects.all().order_by("prenda")
    form = IndumentariaStockForm()
    return render(request, "rrhh/indumentaria/stock_list.html", {"stock": stock, "form": form})

@login_required
@tiene_funcion('rrhh_admin_stock')
def indumentaria_stock_add(request):
    if request.method == "POST":
        form = IndumentariaStockForm(request.POST)
        if form.is_valid():
            prenda = form.cleaned_data['prenda']
            talle = form.cleaned_data['talle']
            cant = form.cleaned_data['cantidad']
            
            obj, created = IndumentariaStock.objects.get_or_create(
                prenda__iexact=prenda, talle__iexact=talle,
                defaults={'prenda': prenda, 'talle': talle, 'cantidad': cant}
            )
            if not created:
                obj.cantidad += cant
                obj.save()
            messages.success(request, "Stock actualizado exitosamente.")
            return redirect("rrhh:indumentaria_stock_list")
    return render(request, "rrhh/indumentaria/stock_form.html", {"form": IndumentariaStockForm()})

@login_required
@tiene_funcion('rrhh_entregar_ropa')
def indumentaria_carrito_remove(request, index):
    carrito = request.session.get("carrito_indumentaria", [])
    try:
        carrito.pop(index)
        request.session["carrito_indumentaria"] = carrito
        request.session.modified = True
    except IndexError:
        pass
    return redirect(request.META.get('HTTP_REFERER', 'rrhh:indumentaria_list'))

@login_required
@tiene_funcion('rrhh_ver_indumentaria')
def entrega_pdf(request, pk):
    # El pk viene del historial, es el ID de una EntregaIndumentaria particular
    entrega_obj = get_object_or_404(EntregaIndumentaria, pk=pk)
    empleado = entrega_obj.empleado
    
    # Agrupamos todas las prendas entregadas el mismo día para este agente
    # Ya que el modelo es por ítem y no por lote de entrega.
    prendas = EntregaIndumentaria.objects.filter(
        empleado=empleado, 
        fecha=entrega_obj.fecha
    ).order_by("prenda")

    context = {
        "empleado": empleado, 
        "prendas": prendas,
        "fecha": entrega_obj.fecha,
        "usuario": entrega_obj.usuario or request.user
    }
    html = render_to_string("rrhh/indumentaria/entrega_pdf.html", context)
    pdf = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG, options=PDF_OPTIONS)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="entrega_{empleado.dni}.pdf"'
    return response

@login_required
@tiene_funcion('rrhh_admin_stock')
def indumentaria_stock_edit(request, pk):
    item = get_object_or_404(IndumentariaStock, pk=pk)
    if request.method == "POST":
        form = IndumentariaStockForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Stock modificado.")
            return redirect("rrhh:indumentaria_stock_list")
    else:
        form = IndumentariaStockForm(instance=item)
    return render(request, "rrhh/indumentaria/stock_form.html", {"form": form, "edit": True})

@login_required
@tiene_funcion('rrhh_admin_stock')
def indumentaria_stock_delete(request, pk):
    # Nota: Aquí puedes decidir si borrar físicamente o solo poner en 0 
    # según tu política de "nada se borra".
    item = get_object_or_404(IndumentariaStock, pk=pk)
    item.delete()
    messages.warning(request, "Ítem eliminado del inventario.")
    return redirect("rrhh:indumentaria_stock_list")

@login_required
@tiene_funcion('rrhh_admin_stock')
def indumentaria_stock_import(request):
    if request.method == "POST" and request.FILES.get("archivo"):
        file = request.FILES["archivo"]
        try:
            df = pd.read_excel(file)
            summary = {"inserted": 0, "updated": 0, "invalid": 0}
            errors = []
            
            for index, row in df.iterrows():
                try:
                    obj, created = IndumentariaStock.objects.get_or_create(
                        prenda=row['prenda'], talle=str(row['talle']),
                        defaults={'cantidad': row['cantidad']}
                    )
                    if not created:
                        obj.cantidad += row['cantidad']
                        obj.save()
                        summary["updated"] += 1
                    else:
                        summary["inserted"] += 1
                except Exception as e:
                    summary["invalid"] += 1
                    errors.append({"row": index + 2, "reason": str(e), "value": row.to_dict()})
                    
            messages.success(request, "Stock importado correctamente.")
            return render(request, "rrhh/indumentaria/indumentaria_stock_import.html", {"summary": summary, "errors": errors})
        except Exception as e:
            messages.error(request, f"Error en la importación: {e}")
            return redirect("rrhh:indumentaria_stock_list")
            
    return render(request, "rrhh/indumentaria/indumentaria_stock_import.html")

@login_required
@tiene_funcion('rrhh_admin_stock')
def indumentaria_stock_plantilla(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="plantilla_stock.csv"'
    writer = csv.writer(response)
    writer.writerow(['prenda', 'talle', 'cantidad'])
    writer.writerow(['Pantalón Grafa', '42', '10'])
    return response

@login_required
@tiene_funcion('rrhh_admin_stock')
def indumentaria_stock_panel(request):
    stock_bajo = IndumentariaStock.objects.filter(cantidad__lt=5)
    return render(request, "rrhh/indumentaria/stock_panel.html", {"stock_bajo": stock_bajo})