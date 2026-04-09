# central/urls.py
from django.urls import path
from .views import seleccionar_modulo

app_name = 'central'

urlpatterns = [
    path('', seleccionar_modulo, name='seleccionar_modulo'),
]
