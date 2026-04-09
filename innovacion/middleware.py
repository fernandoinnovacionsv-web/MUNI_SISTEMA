from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.contrib import messages

class InnovacionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user_funciones = []

        if request.user.is_authenticated:
            # 1. Intentar cargar perfil y funciones
            perfil = getattr(request.user, 'perfil_innovacion', None)
            if perfil and perfil.esta_activo:
                request.user_funciones = list(
                    perfil.funciones.values_list('codigo_interno', flat=True)
                )

            path = request.path

            # 2. FILTRO DE ACCESO AL MÓDULO (SEGURIDAD POR CARPETA)
            if path.startswith('/innovacion/'):
                # Excepción: La página de cambio de clave debe ser accesible para todos
                if "cambiar-password" not in path:
                    es_admin_innovacion = 'acceso_innovacion_admin' in request.user_funciones
                    # Si no es SuperUser y no tiene el permiso, fuera.
                    if not (request.user.is_superuser or es_admin_innovacion):
                        messages.error(request, "No tienes permisos para entrar al módulo de Innovación.")
                        
                        # CORRECCIÓN: Usamos seleccionar_modulo en lugar de home
                        try:
                            return redirect('central:seleccionar_modulo')
                        except NoReverseMatch:
                            return redirect('/')

            # 3. EXCLUSIONES DE RENDIMIENTO
            if any(x in path for x in ["/static/", "/media/", "/admin/logout", "password_change"]):
                return self.get_response(request)

            # 4. LÓGICA DE CAMBIO DE CLAVE (OPTIMIZADA CON SESIÓN)
            if "cambiar-password" not in path:
                must_change = request.session.get('must_change_password')

                if must_change is None:
                    # Si el password es igual al DNI, debe cambiarlo
                    must_change = request.user.check_password(request.user.username)
                    request.session['must_change_password'] = must_change

                if must_change:
                    try:
                        return redirect('innovacion:cambiar_password_inicio')
                    except NoReverseMatch:
                        pass # Si no existe la URL, dejamos pasar para no romper el sitio

        return self.get_response(request)