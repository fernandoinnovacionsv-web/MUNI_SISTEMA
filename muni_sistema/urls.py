from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

# Importamos la vista profesional desde tu app de innovación
from innovacion.views import cambiar_password_primera_vez 

urlpatterns = [
    path('admin/', admin.site.urls),

    # ===============================================================
    #   PRIORIDAD DE SEGURIDAD
    # ===============================================================
    # Esta línea captura la URL de Django y le obliga a usar TU template.
    # Debe ir OBLIGATORIAMENTE antes de 'accounts/' include.
    path('accounts/password_change/', cambiar_password_primera_vez, name='password_change'),

    # Resto de funcionalidades de autenticación (Login, Logout, etc.)
    path('accounts/', include('django.contrib.auth.urls')),

    # ===============================================================
    #   MÓDULOS DEL SISTEMA
    # ===============================================================
    
    # Módulo central: selector
    path('modulos/', include('central.urls')),

    # Recursos Humanos
    path('rrhh/', include('rrhh.urls')),
    
    # Innovación
    path('innovacion/', include('innovacion.urls')),

    # Redirigir raíz al selector principal
    path('', RedirectView.as_view(url='/modulos/', permanent=False)),
]

# Configuración para archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)