
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muni_sistema.settings')
django.setup()

from innovacion.models import SistemaMunicipal, FuncionSistema

def seed_functions():
    # Obtener el sistema de RRHH
    rrhh, created = SistemaMunicipal.objects.get_or_create(
        codigo='rrhh',
        defaults={'nombre': 'Recursos Humanos', 'icono': 'fas fa-users-cog'}
    )

    # Definir las nuevas funciones
    nuevas_funciones = [
        ('rrhh_cargar_hs_extras', 'Cargar y gestionar Horas Extras'),
        ('rrhh_cierre_mes', 'Cierre del Mes (Asistencia)'),
        ('rrhh_liquidacion_hs_extras', 'Liquidación de Horas Extras'),
        ('rrhh_reporte_hs_extras', 'Descargar Reporte de Horas Extras'),
        ('rrhh_descargar_liquidaciones', 'Descargar Liquidaciones (PDF)'),
        ('rrhh_descargar_asistencia', 'Descargar Asistencia (PDF/Excel)'),
    ]

    for codigo, nombre in nuevas_funciones:
        funcion, created = FuncionSistema.objects.get_or_create(
            codigo_interno=codigo,
            defaults={'nombre_visible': nombre, 'sistema': rrhh}
        )
        if created:
            print(f"Función creada: {nombre}")
        else:
            print(f"La función ya existe: {nombre}")

if __name__ == '__main__':
    seed_functions()
