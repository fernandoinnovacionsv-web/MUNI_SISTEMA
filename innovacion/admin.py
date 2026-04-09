from django.contrib import admin
from django import forms
from .models import SistemaMunicipal, FuncionSistema, PerfilAcceso, SolicitudAcceso

# innovacion/admin.py

class PerfilAccesoForm(forms.ModelForm):
    class Meta:
        model = PerfilAcceso
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Forzamos el widget de checkboxes
        self.fields['funciones'].widget = forms.CheckboxSelectMultiple()
        # Mejoramos la etiqueta para que se vea el Sistema y la Función
        self.fields['funciones'].queryset = FuncionSistema.objects.select_related('sistema').order_by('sistema__nombre', 'nombre_visible')

@admin.register(PerfilAcceso)
class PerfilAccesoAdmin(admin.ModelAdmin):
    form = PerfilAccesoForm
    list_display = ('user', 'esta_activo')
    
    # --- AQUÍ VA EL BLOQUE QUE PREGUNTASTE ---
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
    # ----------------------------------------

    fieldsets = (
        ('Usuario y Estado', {
            'fields': ('user', 'esta_activo', 'observaciones')
        }),
        ('Permisos del Sistema', {
            'description': "Marque las funciones que este usuario tiene permitidas:",
            'fields': ('funciones',),
        }),
    )

admin.site.register(SistemaMunicipal)
admin.site.register(FuncionSistema)
admin.site.register(SolicitudAcceso)