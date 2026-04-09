from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Empleado, Sector, Categoria, CondicionLaboral
from django.http import JsonResponse
from innovacion.decorators import tiene_funcion # <--- EL CANDADO

@login_required
@tiene_funcion('rrhh_config_general')
def panel_abm_configuracion(request):
    # Traemos Sectores Principales (los que no tienen padre)
    sectores_principales = Sector.objects.filter(padre__isnull=True)
    # Traemos todos los que SI tienen padre para la lista de subsectores
    subsectores = Sector.objects.filter(padre__isnull=False).select_related('padre')
    
    context = {
        'sectores': sectores_principales,
        'subsectores': subsectores,
        'categorias': Categoria.objects.all(),
        'condiciones': CondicionLaboral.objects.all(),
    }
    return render(request, 'rrhh/config/panel_abm.html', context)

@login_required
@tiene_funcion('rrhh_config_general')
def sector_create(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        if nombre:
            Sector.objects.create(nombre=nombre.upper())
            messages.success(request, f"Sector '{nombre}' creado correctamente.")
    return redirect("rrhh:panel_abm_configuracion")

@login_required
@tiene_funcion('rrhh_config_general')
def subsector_create(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        padre_id = request.POST.get("padre_id")
        if nombre and padre_id:
            padre = get_object_or_404(Sector, id=padre_id)
            Sector.objects.create(nombre=nombre.upper(), padre=padre)
            messages.success(request, f"Subsector '{nombre}' asignado a {padre.nombre}.")
    return redirect("rrhh:panel_abm_configuracion")

@login_required
@tiene_funcion('rrhh_config_general')
def condicion_create(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        if nombre:
            CondicionLaboral.objects.create(nombre=nombre.upper())
            messages.success(request, "Nueva condición laboral agregada.")
    return redirect("rrhh:panel_abm_configuracion")

@login_required
@tiene_funcion('rrhh_config_general')
def categoria_create(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        remuneracion = request.POST.get("remuneracion", 0)
        if nombre:
            Categoria.objects.create(nombre=nombre.upper(), remuneracion_base=remuneracion)
            messages.success(request, "Categoría creada correctamente.")
    return redirect("rrhh:panel_abm_configuracion")

@login_required
@tiene_funcion('rrhh_aval_jefe') # Solo quienes tengan rol de jefe según Innovación
def panel_jefe_sector(request):
    # Verificamos que el usuario tenga un perfil asociado con sector de gestión
    perfil = getattr(request.user, 'perfil', None)
    if not perfil or not perfil.sector_gestion:
        messages.error(request, "Usted no tiene asignado un sector para gestionar.")
        return redirect("rrhh:dashboard_rrhh")
    
    # El jefe ve a los empleados de su sector
    empleados = Empleado.objects.filter(sector=perfil.sector_gestion, activo=True)
    return render(request, 'rrhh/panel_jefe.html', {
        'empleados': empleados, 
        'sector': perfil.sector_gestion
    })

@login_required
def get_subsectores(request):
    # Esta función es de utilidad para formularios, no requiere permiso crítico
    sector_id = request.GET.get('sector_id')
    subsectores = Sector.objects.filter(padre_id=sector_id).order_by('nombre')
    return JsonResponse(
        [{'id': s.id, 'nombre': s.nombre} for s in subsectores], 
        safe=False
    )

@login_required
@tiene_funcion('rrhh_config_general')
def sector_edit(request, pk):
    sector = get_object_or_404(Sector, pk=pk)
    if request.method == "POST":
        nuevo_nombre = request.POST.get("nombre")
        if nuevo_nombre:
            sector.nombre = nuevo_nombre.upper()
            sector.save()
            messages.success(request, f"Actualizado: {sector.nombre}")
    return redirect("rrhh:panel_abm_configuracion")