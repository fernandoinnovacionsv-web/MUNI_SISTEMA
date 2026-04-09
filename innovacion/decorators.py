from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def tiene_funcion(codigo_funcion):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Si es SuperAdmin o Staff de Django, pasa directo (Seguridad de RRHH/Adm)
            if request.user.is_superuser or request.user.is_staff:
                return view_func(request, *args, **kwargs)

            # Buscamos el perfil del usuario creado desde Innovación
            perfil = getattr(request.user, 'perfil_innovacion', None)
            
            if perfil and perfil.esta_activo:
                # 1. Búsqueda exacta de la función
                if perfil.funciones.filter(codigo_interno=codigo_funcion).exists():
                    return view_func(request, *args, **kwargs)
                
                # 2. Jerarquía: Si tiene el permiso "Full" del sistema correspondiente
                # Ejemplo: si pide 'rrhh_entregar_ropa', chequeamos 'rrhh_admin_total'
                if '_' in codigo_funcion:
                    sistema_prefix = codigo_funcion.split('_')[0]
                    admin_total_code = f"{sistema_prefix}_admin_total"
                    if perfil.funciones.filter(codigo_interno=admin_total_code).exists():
                        return view_func(request, *args, **kwargs)

            messages.error(request, "No tienes permiso para realizar esta acción.")
            return redirect('rrhh:dashboard_rrhh')
        return _wrapped_view
    return decorator