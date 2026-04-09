from .dashboard import dashboard_rrhh
from .personal import (
    personal_list, personal_wizard, personal_create, 
    personal_edit, personal_detalle, personal_detalle_pdf,
    personal_export, personal_alta, personal_baja, 
    movimientos_list, movimiento_create
)
from .vacaciones import (
    vacaciones_list, vacacion_create, vacacion_edit, 
    vacacion_aprobar, vacacion_rechazar, pdf_vacacion, 
    nota_vacaciones, feriados_list, feriado_create, 
    feriado_editar, feriado_delete, feriado_import_excel, 
    feriado_plantilla, vacaciones_personal
)
from .indumentaria import (
    indumentaria_list, indumentaria_historial, indumentaria_carrito_add,
    indumentaria_carrito_remove, indumentaria_confirmar, entrega_pdf,
    indumentaria_stock_list, indumentaria_stock_add, indumentaria_stock_edit,
    indumentaria_stock_delete, indumentaria_stock_import, 
    indumentaria_stock_plantilla, indumentaria_stock_panel
)

from .config import (
    panel_abm_configuracion, 
    panel_jefe_sector, 
    sector_create,
    subsector_create,
    categoria_create,
    condicion_create,
    get_subsectores,       # <--- Asegúrate de que esté exactamente así
    sector_edit,
    
)

from .asistencia import (
    registro_horas_extras, exportar_horas_extras_pdf,
    exportar_asistencia_pdf,
    programar_franco, registrar_pago_horas,
    exportar_asistencia_excel,
    cerrar_mes_asistencia,
    historial_asistencia_empleado,
    liquidar_horas,
    exportar_liquidaciones_pdf
)