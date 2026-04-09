from pathlib import Path
import os

# ===================================================
# 📁 BASE GENERAL
# ===================================================
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'cambiame-por-uno-seguro'
DEBUG = True
ALLOWED_HOSTS = []  # En producción agregar IP o dominio

# ===================================================
# 🔌 APLICACIONES
# ===================================================
INSTALLED_APPS = [
    # Django base
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps institucionales
    'central',
    'rrhh',
    'innovacion',
     'widget_tweaks',
     
     
    # Extras útiles
    'django.contrib.humanize',
    'rest_framework',
    'django_filters',
    
]

# ===================================================
# ⚙️ MIDDLEWARE
# ===================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'muni_sistema.middleware.ForcePasswordChangeMiddleware',
    'innovacion.middleware.InnovacionMiddleware'
    
]

# ===================================================
# 🔗 URL RAÍZ DEL PROYECTO
# ===================================================
ROOT_URLCONF = 'muni_sistema.urls'

# ===================================================
# 🎨 TEMPLATES
# ===================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                # Contexto adicional (si existe este archivo)
                'muni_sistema.context_processors.system_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'muni_sistema.wsgi.application'

# ===================================================
# 🧩 BASE DE DATOS
# ===================================================
DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': 'MUNI_SISTEMA',
        'USER': 'sa',
        'PASSWORD': 'Fernando1234', 
        'HOST': '127.0.0.1',  # Cambiamos localhost por la IP local
        'PORT': '',
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'extra_params': 'TrustServerCertificate=yes;',
        },
    }
}

# Este print ahora te dirá el motor REAL que está cargando Django
import django
print(f"✅ Motor Activo: {DATABASES['default']['ENGINE']} | BD: {DATABASES['default']['NAME']}")


# ===================================================
# 🔐 VALIDADORES DE CONTRASEÑAS
# ===================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===================================================
# 🌍 IDIOMA Y ZONA HORARIA
# ===================================================
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True

# ===================================================
# 🖼️ STATIC & MEDIA
# ===================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [ BASE_DIR / "static" ]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Almacenamiento externo para archivos de RRHH
MEDIA_ROOT = Path("D:/ARCHIVOS RRHH")
MEDIA_URL = "/ARCHIVOS_RRHH/"


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===================================================
# 🔐 LOGIN / LOGOUT
# ===================================================
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/modulos/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
PASSWORD_CHANGE_URL = 'innovacion:cambiar_password_inicio'
# ===================================================
# ⏱️ SESIONES
# ===================================================
SESSION_COOKIE_AGE = 60 * 60  # 1 hora
SESSION_SAVE_EVERY_REQUEST = True
IDLE_TIMEOUT_SECONDS = 60 * 10  # 10 minutos
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ===================================================
# 🏛️ METADATOS DEL SISTEMA
# ===================================================
SYSTEM_NAME = "Sistema Central Municipal"
SYSTEM_VERSION = os.getenv("SYSTEM_VERSION", "1.0.0")
SYSTEM_OWNER = "Municipalidad de San Vicente"
SYSTEM_VENDOR = "Secretaría de Innovación Tecnológica"
