from django import forms
from django.forms import ModelForm, inlineformset_factory
from django.contrib.auth.forms import PasswordChangeForm # Nuevo import
from .models import (
    Conyuge, DocumentoEmpleado, Empleado, EntregaIndumentaria, Hijo, 
    IndumentariaStock, Movimiento, Vacacion, Feriado, EmpleadoTalle,
    Sector, Categoria, CondicionLaboral,
    SolicitudLicencia, SeguimientoMedico,
    CategoriaLicencia, TipoLicencia
)
from datetime import date

# ===============================================================
#   MIXIN PARA APLICAR CLASES DE BOOTSTRAP
# ===============================================================
class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            existing_classes = field.widget.attrs.get('class', '')
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                new_class = 'form-select'
            elif isinstance(field.widget, forms.CheckboxInput):
                new_class = 'form-check-input'
            else:
                new_class = 'form-control'
            
            if new_class not in existing_classes:
                field.widget.attrs['class'] = f"{existing_classes} {new_class}".strip()

# ===============================================================
#   FORMULARIO EMPLEADO (CON FILTRADO DE SECTORES)
# ===============================================================
class EmpleadoForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = Empleado
        fields = "__all__"
        exclude = ['antiguedad_anios', 'activo', 'motivo_baja']
        widgets = {
            "fecha_nacimiento": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "fecha_inicio_contrato": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "fecha_fin_contrato": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "inicio_actividad": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "apellido": forms.TextInput(attrs={'placeholder': 'APELLIDO EN MAYÚSCULAS'}),
            "nombre": forms.TextInput(attrs={'placeholder': 'NOMBRES EN MAYÚSCULAS'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Filtramos 'sector' para que solo muestre Secretarías (Sectores sin padre)
        self.fields['sector'].queryset = Sector.objects.filter(padre__isnull=True)
        self.fields['sector'].empty_label = "-- Seleccionar Secretaría --"

        # 2. Inicializamos 'subsector' vacío (se llenará vía AJAX en el template)
        self.fields['subsector'].queryset = Sector.objects.none()
        self.fields['subsector'].empty_label = "-- Seleccione Secretaría primero --"

        # 3. Lógica para mantener subsectores en caso de error de validación o edición
        if 'emp-sector' in self.data: # Prefijo 'emp' usado en el wizard
            try:
                sector_id = int(self.data.get('emp-sector'))
                self.fields['subsector'].queryset = Sector.objects.filter(padre_id=sector_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.sector: # Caso edición
            self.fields['subsector'].queryset = Sector.objects.filter(padre=self.instance.sector)

        # 4. Forzamos labels descriptivos en los selectores obligatorios
        self.fields['condicion'].empty_label = "-- Seleccionar Condición --"
        self.fields['categoria'].empty_label = "-- Seleccionar Categoría --"

# ===============================================================
#   FORMULARIO CÓNYUGE
# ===============================================================
class ConyugeForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = Conyuge
        fields = ["dni", "apellido", "nombre"]

# ===============================================================
#   FORMSETS (HIJOS, DOCS, ROPA)
# ===============================================================
class HijoForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = Hijo
        fields = ["dni", "apellido", "nombre", "fecha_nacimiento"]
        widgets = {
            "fecha_nacimiento": forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
        }

HijoFormSet = inlineformset_factory(
    Empleado, Hijo, form=HijoForm, extra=0, can_delete=True
)

class DocumentoForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = DocumentoEmpleado
        fields = ["tipo", "archivo"]

DocumentoFormSet = inlineformset_factory(
    Empleado, DocumentoEmpleado, form=DocumentoForm, extra=0, can_delete=True
)

class EmpleadoTalleForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = EmpleadoTalle
        fields = ["tipo_prenda", "talle"]
        widgets = {
            "talle": forms.TextInput(attrs={"placeholder": "Ej: 42, L"}),
        }

IndumentariaFormSet = inlineformset_factory(
    Empleado, EmpleadoTalle, form=EmpleadoTalleForm, extra=0, can_delete=True
)

# ===============================================================
#   OTROS FORMULARIOS (VACACIONES, MOVIMIENTOS, STOCK)
# ===============================================================

class VacacionForm(forms.ModelForm):
    dias_habiles = forms.IntegerField(widget=forms.HiddenInput(), required=False, initial=0)

    class Meta:
        model = Vacacion
        fields = ["empleado", "anio", "fecha_inicio", "fecha_fin", "adjunto_solicitud", "observaciones"]
        widgets = {
            "empleado": forms.HiddenInput(),
            "anio": forms.NumberInput(attrs={
                "class": "form-control", 
                "id": "id_anio_form", 
                "onchange": "actualizarPeriodo()" 
            }),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-control", "id": "id_fecha_inicio"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-control", "id": "id_fecha_fin"}),
            "observaciones": forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": "Justifique si es un adelanto..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and 'anio' not in self.initial:
            self.initial['anio'] = date.today().year - 1

class MovimientoForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = Movimiento
        fields = "__all__"
        widgets = {
            "detalle": forms.Textarea(attrs={"rows": 2}),
        }

class IndumentariaStockForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = IndumentariaStock
        fields = ["prenda", "talle", "cantidad"]

class EntregaIndumentariaForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = EntregaIndumentaria
        fields = ["empleado"]

class FeriadoForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = Feriado
        fields = ["nombre", "fecha"]
        widgets = {
            "fecha": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"})
        }
        
# ===============================================================
#   NUEVO FORMULARIO PARA CAMBIO DE CLAVE OBLIGATORIO
# ===============================================================
class PasswordFirstTimeForm(PasswordChangeForm):
    """
    Hereda de PasswordChangeForm para asegurar que se cumplan las 
    políticas de seguridad de Django.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control rounded-pill'

# ===============================================================
#   FORMULARIOS DE LICENCIAS
# ===============================================================

class EmpleadoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        legajo = obj.legajo if obj.legajo else "S/L"
        dni = obj.dni if obj.dni else "S/D"
        return f"{obj.apellido}, {obj.nombre} | DNI: {dni} | Leg: {legajo}"

class SolicitudLicenciaForm(BootstrapFormMixin, ModelForm):
    aprobar_licencia = forms.BooleanField(
        required=False,
        label="✅ Aprobar Licencia",
        help_text="Marque esta casilla para aprobar definitivamente la solicitud médica."
    )
    rechazar_licencia = forms.BooleanField(
        required=False,
        label="❌ Rechazar Pedido",
        help_text="Marque esta casilla si desea rechazar la solicitud."
    )
    motivo_rechazo = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        label="Motivo del Rechazo",
        help_text="Explique por qué se rechaza (ej: excede cupo, falta documentación)."
    )

    empleado = EmpleadoChoiceField(
        queryset=Empleado.objects.all(),
        empty_label="-- Seleccionar o buscar empleado --"
    )

    def __init__(self, *args, **kwargs):
        is_rrhh = kwargs.pop('is_rrhh', False)
        super().__init__(*args, **kwargs)
        if not is_rrhh:
            self.fields.pop('aprobar_licencia', None)
            self.fields.pop('rechazar_licencia', None)
            self.fields.pop('motivo_rechazo', None)
        else:
            if self.instance and self.instance.pk:
                if self.instance.estado == 'Aprobada':
                    self.fields['aprobar_licencia'].initial = True
                elif self.instance.estado == 'Rechazada':
                    self.fields['rechazar_licencia'].initial = True
                    self.fields['motivo_rechazo'].initial = self.instance.motivo_rechazo

    def save(self, commit=True):
        instance = super().save(commit=False)
        if 'aprobar_licencia' in self.fields:
            if self.cleaned_data.get('rechazar_licencia'):
                instance.estado = 'Rechazada'
                instance.motivo_rechazo = self.cleaned_data.get('motivo_rechazo')
            elif self.cleaned_data.get('aprobar_licencia'):
                instance.estado = 'Aprobada'
            elif instance.estado in ['Aprobada', 'Rechazada']:
                # Si se destildó, vuelve a estado previo lógico
                instance.estado = 'Entregado' if instance.adjunto_pdf else 'Pendiente_Certificado'
        
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    class Meta:
        model = SolicitudLicencia
        fields = ["empleado", "tipo_licencia", "fecha_desde", "fecha_hasta", "adjunto_pdf", "observaciones"]
        labels = {
            "adjunto_pdf": "Certificado Médico (Imagen o PDF)",
        }
        help_text = {
            "adjunto_pdf": "Obligatorio para la aprobación de licencias médicas."
        }
        widgets = {
            "fecha_desde": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "fecha_hasta": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
        }

class SeguimientoMedicoForm(BootstrapFormMixin, ModelForm):
    # Campos opcionales para extender la licencia desde el seguimiento
    extender_hasta = forms.DateField(
        required=False, 
        label="📅 Extender Licencia Hasta", 
        widget=forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
        help_text="Si el médico indica continuar la licencia, coloque aquí la nueva fecha de finalización."
    )
    nuevo_certificado = forms.FileField(
        required=False, 
        label="📄 Nuevo Certificado/Prórroga",
        help_text="Suba el nuevo certificado médico que avala la extensión."
    )

    class Meta:
        model = SeguimientoMedico
        fields = ["fecha_consulta", "medico", "evolucion", "proximo_control", "es_alta_medica"]
        widgets = {
            "fecha_consulta": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "proximo_control": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "evolucion": forms.Textarea(attrs={"rows": 3}),
        }

class LicenciaExtensionForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = SolicitudLicencia
        fields = ["fecha_hasta", "adjunto_pdf", "observaciones"]
        labels = {
            "fecha_hasta": "Nueva Fecha de Finalización",
            "adjunto_pdf": "Nuevo Certificado de Prórroga",
            "observaciones": "Motivo de la Extensión"
        }
        widgets = {
            "fecha_hasta": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

class CategoriaLicenciaForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = CategoriaLicencia
        fields = '__all__'

class TipoLicenciaForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = TipoLicencia
        fields = '__all__'