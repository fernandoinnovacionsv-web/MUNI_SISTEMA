from django.conf import settings

def system_info(request):
    """
    Contexto global con información institucional del sistema.
    Permite usar {{ SYSTEM_NAME }}, {{ SYSTEM_VERSION }}, {{ SYSTEM_OWNER }}, {{ SYSTEM_VENDOR }}
    en todos los templates.
    """
    return {
        'SYSTEM_NAME': getattr(settings, 'SYSTEM_NAME', ''),
        'SYSTEM_VERSION': getattr(settings, 'SYSTEM_VERSION', ''),
        'SYSTEM_OWNER': getattr(settings, 'SYSTEM_OWNER', ''),
        'SYSTEM_VENDOR': getattr(settings, 'SYSTEM_VENDOR', ''),
    }

# muni_sistema/context_processors.py

def global_vars(request):
    return {
        'MUNI_COPY': 'Municipalidad de San Vicente',
        'DEV_COPY': 'Secretaría de Innovación Tecnológica',
        'APP_VERSION': '1.0.0',
    }
