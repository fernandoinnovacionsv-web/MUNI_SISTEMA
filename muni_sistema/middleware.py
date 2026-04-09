from django.shortcuts import redirect
from django.urls import reverse

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Si el username es igual a la password (simplificado para el primer ingreso)
            # O si una bandera en su perfil dice 'debe_cambiar_clave'
            if request.user.check_password(request.user.username):
                path_cambio = reverse('password_change') # URL estándar de Django
                if request.path != path_cambio and not request.path.startswith('/static/'):
                    return redirect(path_cambio)
        
        return self.get_response(request)