from django.contrib import admin
from .models import Movimiento

@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo', 'fecha')
    search_fields = ('empleado', 'tipo')
    list_filter = ('tipo', 'fecha')
