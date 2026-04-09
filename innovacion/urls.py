from django.urls import path
from . import views

app_name = 'innovacion'

urlpatterns = [
    # ===============================================================
    #   RUTA DE CAPTURA (Sustituye la de Django por la tuya)
    # ===============================================================
    path('accounts/password_change/', views.cambiar_password_primera_vez),
    
    # ===============================================================
    #   Dashboard Principal
    # ===============================================================
    path('', views.InnovacionHomeView.as_view(), name='dashboard'),
    path('home/', views.InnovacionHomeView.as_view(), name='home'),
    
    # ===============================================================
    #   Seguridad y Cambio de Clave
    # ===============================================================
    path('cambiar-password/', views.cambiar_password_primera_vez, name='cambiar_password_inicio'),
    # NUEVA RUTA PARA RESTABLECER AL DNI
    path('usuarios/restablecer/<int:user_id>/', views.restablecer_password, name='restablecer_password'),
    
    # ===============================================================
    #   Gestión de Solicitudes (Pendientes)
    # ===============================================================
    path('solicitudes/', views.ListaSolicitudesView.as_view(), name='lista_solicitudes'),
    path('solicitar-acceso/<int:empleado_id>/', views.solicitar_acceso_view, name='solicitar_acceso'),
    path('procesar-acceso/<int:solicitud_id>/', views.procesar_acceso_view, name='procesar_acceso'),
    
    # ===============================================================
    #   Gestión de Usuarios Activos
    # ===============================================================
    path('usuarios/activos/', views.lista_usuarios_activos, name='usuarios_activos'),
    path('usuarios/accesos/<int:user_id>/', views.gestionar_accesos_usuario, name='gestionar_accesos'),
    path('usuarios/toggle-estado/<int:user_id>/', views.toggle_estado_usuario, name='toggle_estado_usuario'),
    path('usuarios/toggle-permiso/<int:user_id>/', views.toggle_permiso_solicitud, name='toggle_permiso_solicitud'),


# ===============================================================
    #   Gestión de Operaciones (Asistencia)
    # ===============================================================
    path('asistencia/tomar/', views.toma_asistencia_view, name='toma_asistencia'),
]