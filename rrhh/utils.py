from rrhh.models import Empleado

def obtener_personal_permitido(user):
    """
    Retorna un queryset de Empleado filtrado según los permisos del usuario.
    - Si es superuser o de RRHH, ve a todos.
    - Si es un jefe con perfil vinculado, ve solo a los de su sector/subsector.
    - En otro caso, no ve a nadie.
    """
    if user.is_superuser:
        return Empleado.objects.all()

    # Buscamos el perfil del usuario de innovación
    perfil = getattr(user, 'perfil_innovacion', None)
    
    # Si tiene funciones totales de rrhh o licencias, ve a todos
    if perfil and perfil.esta_activo:
        if perfil.funciones.filter(codigo_interno__in=[
            'rrhh_admin_total', 
            'rrhh_carga_inicial_licencias', 
            'rrhh_control_total_licencias',
            'rrhh_aprobar_licencia'
        ]).exists():
            return Empleado.objects.all()

    # Si no es admin total, verificamos a qué sector pertenece su empleado vinculado
    if perfil and perfil.empleado and perfil.empleado.sector:
        sector_usuario = perfil.empleado.sector
        subsector_usuario = perfil.empleado.subsector
        
        # Si de casualidad el sector es directamente el departamento de RRHH, podría ver todo
        # pero para mantener el principio de menor privilegio, si no tiene la función admin_total,
        # solo ve a los de su área. El super admin le dará 'rrhh_admin_total' a los de la sec de rrhh.
        
        filtros = {'sector': sector_usuario}
        if subsector_usuario:
            filtros['subsector'] = subsector_usuario
            
        return Empleado.objects.filter(**filtros)

    # Si no cumple ninguna condición de privilegio ni tiene empleado asignado, retorna vacío
    return Empleado.objects.none()
def verificar_solapamiento(empleado, fecha, hora_inicio_str, hora_fin_str):
    """
    Verifica si un rango horario se solapa con registros existentes de horas extras.
    """
    from rrhh.models import RegistroHoraExtra
    from datetime import datetime

    h_ini = datetime.strptime(hora_inicio_str, '%H:%M').time()
    h_fin = datetime.strptime(hora_fin_str, '%H:%M').time()

    registros = RegistroHoraExtra.objects.filter(empleado=empleado, fecha=fecha)

    for reg in registros:
        # Lógica de solapamiento: (StartA < EndB) y (EndA > StartB)
        if (h_ini < reg.hora_fin) and (h_fin > reg.hora_inicio):
            return True
            
    return False
