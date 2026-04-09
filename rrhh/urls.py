from django.urls import path
from . import views
from innovacion.views import toma_asistencia_view 
from .views.licencias import (
    LicenciasConfigView, CategoriaLicenciaCreateView, TipoLicenciaCreateView,
    LicenciaListView, LicenciaCreateView, LicenciaUpdateView, LicenciaExtensionView,
    SeguimientoMedicoDetailView, SeguimientoMedicoCreateView, SeguimientoMedicoUpdateView
)

app_name = "rrhh"

urlpatterns = [
    # DASHBOARD
    path("", views.dashboard_rrhh, name="dashboard_rrhh"),

    # GESTIÓN DE PERSONAL
    path("personal/", views.personal_list, name="personal_list"),
    path("personal/nuevo/", views.personal_create, name="personal_create"),
    path("personal/editar/<int:pk>/", views.personal_edit, name="personal_edit"),
    path("personal/detalle/<int:pk>/", views.personal_detalle, name="personal_detalle"),
    path("personal/detalle/pdf/<int:pk>/", views.personal_detalle_pdf, name="personal_detalle_pdf"),
    path("personal/baja/<int:pk>/", views.personal_baja, name="personal_baja"),
    path("personal/alta/<int:pk>/", views.personal_alta, name="personal_alta"),
    path("personal/export/", views.personal_export, name="personal_export"),

    # MOVIMIENTOS / HISTORIAL
    path("movimientos/", views.movimientos_list, name="movimientos_list"),
    path("movimientos/nuevo/", views.movimiento_create, name="movimiento_create"),

    # GESTIÓN DE VACACIONES
    path("vacaciones/", views.vacaciones_list, name="vacaciones_list"),
    path("vacaciones/nueva/", views.vacacion_create, name="vacacion_create"),
    path("vacaciones/nota/<int:pk>/", views.nota_vacaciones, name="nota_vacaciones"),
    path("vacaciones/pdf/<int:pk>/", views.pdf_vacacion, name="pdf_vacacion"),
    path("vacaciones/<int:pk>/aprobar/", views.vacacion_aprobar, name="vacacion_aprobar"),
    path("vacaciones/<int:pk>/rechazar/", views.vacacion_rechazar, name="vacacion_rechazar"),
    path("vacaciones/personal/", views.vacaciones_personal, name="vacaciones_personal"),
    
    # rrhh/urls.py
path('vacaciones/editar/<int:pk>/', views.vacacion_edit, name='vacacion_edit'),
path('vacaciones/aprobar/<int:pk>/', views.vacacion_aprobar, name='vacacion_aprobar'),
path('vacaciones/rechazar/<int:pk>/', views.vacacion_rechazar, name='vacacion_rechazar'),

    # CALENDARIO Y FERIADOS
    path("vacaciones/feriados/", views.feriados_list, name="feriados_list"),
    path("vacaciones/feriados/nuevo/", views.feriado_create, name="feriado_create"),
    path("vacaciones/feriados/editar/<int:pk>/", views.feriado_editar, name="feriado_editar"),
    path("vacaciones/feriados/<int:pk>/eliminar/", views.feriado_delete, name="feriado_delete"),
    path("vacaciones/feriados/importar/", views.feriado_import_excel, name="feriado_importar"),
    path("vacaciones/feriados/plantilla/", views.feriado_plantilla, name="feriado_plantilla"),

    # INDUMENTARIA (Entregas y Gestión)
    path("indumentaria/", views.indumentaria_list, name="indumentaria_list"),
    path("indumentaria/<int:pk>/historial/", views.indumentaria_historial, name="indumentaria_historial"),
    path("indumentaria/carrito/add/", views.indumentaria_carrito_add, name="indumentaria_carrito_add"),
    path("indumentaria/carrito/remove/<int:index>/", views.indumentaria_carrito_remove, name="indumentaria_carrito_remove"),
    path("indumentaria/<int:pk>/confirmar/", views.indumentaria_confirmar, name="indumentaria_confirmar"),
    path("indumentaria/entrega/<int:pk>/pdf/", views.entrega_pdf, name="entrega_pdf"),

    # STOCK DE INDUMENTARIA
    path("indumentaria/stock/", views.indumentaria_stock_panel, name="indumentaria_stock_panel"),
    path("indumentaria/stock/listado/", views.indumentaria_stock_list, name="indumentaria_stock_list"),
    path("indumentaria/stock/nuevo/", views.indumentaria_stock_add, name="indumentaria_stock_add"),
    path("indumentaria/stock/editar/<int:pk>/", views.indumentaria_stock_edit, name="indumentaria_stock_edit"),
    path("indumentaria/stock/eliminar/<int:pk>/", views.indumentaria_stock_delete, name="indumentaria_stock_delete"),
    path("indumentaria/stock/importar/", views.indumentaria_stock_import, name="indumentaria_stock_import"),
    path("indumentaria/stock/plantilla/", views.indumentaria_stock_plantilla, name="indumentaria_stock_plantilla"),


# =====================================================
#  Rutas de Configuración / ABM (CORREGIDO)
# =====================================================
    path('configuracion/', views.panel_abm_configuracion, name='panel_abm_configuracion'),
    
    # Ruta para Secretarías (Sectores Padre)
    path('configuracion/sector/nuevo/', views.sector_create, name='sector_create'),
    
    # RUTA FALTANTE: Ruta para Subsectores (Áreas dependientes)
    path('configuracion/subsector/nuevo/', views.subsector_create, name='subsector_create'),
    
    # RUTA FALTANTE: Ruta para Condiciones Laborales
    path('configuracion/condicion/nuevo/', views.condicion_create, name='condicion_create'),
    
    # Ruta para Categorías
    path('configuracion/categoria/nuevo/', views.categoria_create, name='categoria_create'),
    
    # API AJAX para selects dependientes
    path('ajax/get-subsectores/', views.get_subsectores, name='get_subsectores'),
    
    path('configuracion/sector/editar/<int:pk>/', views.sector_edit, name='sector_edit'),
    path('configuracion/condicion/nuevo/', views.condicion_create, name='condicion_create'),
    path('ajax/get-subsectores/', views.get_subsectores, name='get_subsectores'),
    
    
    # PARA ASISTENCIA
    path('asistencia/toma/', toma_asistencia_view, name='toma_asistencia'),
    path('asistencia/horas-extras/<int:sector_id>/', views.registro_horas_extras, name='registro_horas_extras'),
    path('asistencia/horas-extras/<int:sector_id>/pdf/', views.exportar_horas_extras_pdf, name='exportar_horas_extras_pdf'),
    path('asistencia/exportar-pdf/<int:sector_id>/', views.exportar_asistencia_pdf, name='exportar_asistencia_pdf'),
    path('asistencia/exportar-excel/<int:sector_id>/', views.exportar_asistencia_excel, name='exportar_asistencia_excel'),
    path('asistencia/cerrar-mes/<int:sector_id>/', views.cerrar_mes_asistencia, name='cerrar_mes_asistencia'),
    path('asistencia/liquidar/<int:sector_id>/', views.liquidar_horas, name='liquidar_horas'),
    path('asistencia/exportar-liquidaciones-pdf/<int:sector_id>/', views.exportar_liquidaciones_pdf, name='exportar_liquidaciones_pdf'),
    path('asistencia/historial-empleado/<int:empleado_id>/', views.historial_asistencia_empleado, name='historial_asistencia_empleado'),

    # BANCO DE HORAS
    path('asistencia/banco/franco/<int:empleado_id>/', views.programar_franco, name='programar_franco'),

    path('asistencia/banco/pago/<int:empleado_id>/', views.registrar_pago_horas, name='registrar_pago_horas'),

    # =====================================================
    #  LICENCIAS (DECRETO 683/89)
    # =====================================================
    path('licencias/', LicenciaListView.as_view(), name='licencias_list'),
    path('licencias/config/', LicenciasConfigView.as_view(), name='licencias_config'),
    path('licencias/config/categoria/nueva/', CategoriaLicenciaCreateView.as_view(), name='categoria_create'),
    path('licencias/config/tipo/nuevo/', TipoLicenciaCreateView.as_view(), name='tipo_create'),
    path('licencias/nueva/', LicenciaCreateView.as_view(), name='licencias_create'),
    path('licencias/editar/<int:pk>/', LicenciaUpdateView.as_view(), name='licencias_edit'),
    path('licencias/extender/<int:pk>/', LicenciaExtensionView.as_view(), name='licencias_extension'),
    path('licencias/<int:pk>/detalle/', SeguimientoMedicoDetailView.as_view(), name='seguimiento_detalle'),
    path('licencias/<int:solicitud_id>/seguimiento/nuevo/', SeguimientoMedicoCreateView.as_view(), name='seguimiento_create'),
    path('licencias/seguimiento/editar/<int:pk>/', SeguimientoMedicoUpdateView.as_view(), name='seguimiento_edit'),
]