from django.views.generic import ListView, CreateView, UpdateView, TemplateView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from ..models import SolicitudLicencia, SeguimientoMedico, Empleado, TipoLicencia, CategoriaLicencia
from ..forms import (
    SolicitudLicenciaForm, SeguimientoMedicoForm, CategoriaLicenciaForm, 
    TipoLicenciaForm, LicenciaExtensionForm
)
from ..utils import obtener_personal_permitido
import json

def es_rrhh(user):
    if user.is_superuser:
        return True
    perfil = getattr(user, 'perfil_innovacion', None)
    if perfil and perfil.esta_activo:
        # RRHH total o función de aprobación específica
        return perfil.funciones.filter(codigo_interno__in=[
            'rrhh_admin_total', 
            'rrhh_aprobar_licencia',
            'rrhh_control_total_licencias'
        ]).exists()
    return False

def puede_cargar_licencias(user):
    if user.is_superuser:
        return True
    perfil = getattr(user, 'perfil_innovacion', None)
    if perfil and perfil.esta_activo:
        return perfil.funciones.filter(codigo_interno__in=[
            'rrhh_admin_total', 
            'rrhh_cargar_licencia',
            'rrhh_carga_inicial_licencias',
            'rrhh_control_total_licencias'
        ]).exists()
    return False

class BaseLicenciaContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_rrhh'] = es_rrhh(self.request.user)
        return context

class LicenciasConfigView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'rrhh/licencias/config.html'

    def test_func(self): return es_rrhh(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CategoriaLicencia.objects.all()
        context['tipos'] = TipoLicencia.objects.all()
        return context

class CategoriaLicenciaCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = CategoriaLicencia
    form_class = CategoriaLicenciaForm
    template_name = 'rrhh/licencias/config_form.html'
    success_url = reverse_lazy('rrhh:licencias_config')

    def test_func(self): return es_rrhh(self.request.user)

class TipoLicenciaCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = TipoLicencia
    form_class = TipoLicenciaForm
    template_name = 'rrhh/licencias/config_form.html'
    success_url = reverse_lazy('rrhh:licencias_config')

    def test_func(self): return es_rrhh(self.request.user)


class LicenciaListView(LoginRequiredMixin, BaseLicenciaContextMixin, ListView):
    model = SolicitudLicencia
    template_name = 'rrhh/licencias/lista_solicitudes.html'
    context_object_name = 'solicitudes'

    def get_queryset(self):
        qs = super().get_queryset()
        personal_permitido = obtener_personal_permitido(self.request.user)
        qs = qs.filter(empleado__in=personal_permitido)
                
        estado = self.request.GET.get('estado')
        empleado = self.request.GET.get('empleado')
        if estado:
            qs = qs.filter(estado=estado)
        if empleado:
            qs = qs.filter(empleado__apellido__icontains=empleado)
            
        return qs


class LicenciaCreateView(LoginRequiredMixin, BaseLicenciaContextMixin, UserPassesTestMixin, CreateView):
    model = SolicitudLicencia
    form_class = SolicitudLicenciaForm
    template_name = 'rrhh/licencias/solicitud_form.html'
    success_url = reverse_lazy('rrhh:licencias_list')

    def test_func(self):
        return puede_cargar_licencias(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_rrhh'] = es_rrhh(self.request.user)
        return kwargs

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['empleado'].queryset = obtener_personal_permitido(self.request.user).filter(activo=True)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tipos = TipoLicencia.objects.all().values('id', 'es_dias_habiles')
        context['tipos_json'] = json.dumps({t['id']: {'es_dias_habiles': t['es_dias_habiles']} for t in tipos})
        return context


class LicenciaUpdateView(LoginRequiredMixin, BaseLicenciaContextMixin, UserPassesTestMixin, UpdateView):
    model = SolicitudLicencia
    form_class = SolicitudLicenciaForm
    template_name = 'rrhh/licencias/solicitud_form.html'
    success_url = reverse_lazy('rrhh:licencias_list')

    def get_queryset(self):
        return super().get_queryset().filter(empleado__in=obtener_personal_permitido(self.request.user))

    def test_func(self):
        # Puede editar si puede cargar o si puede aprobar
        return puede_cargar_licencias(self.request.user) or es_rrhh(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_rrhh'] = es_rrhh(self.request.user)
        return kwargs

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['empleado'].queryset = obtener_personal_permitido(self.request.user).filter(activo=True)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tipos = TipoLicencia.objects.all().values('id', 'es_dias_habiles')
        context['tipos_json'] = json.dumps({t['id']: {'es_dias_habiles': t['es_dias_habiles']} for t in tipos})
        return context


class LicenciaExtensionView(LoginRequiredMixin, BaseLicenciaContextMixin, UserPassesTestMixin, UpdateView):
    model = SolicitudLicencia
    form_class = LicenciaExtensionForm
    template_name = 'rrhh/licencias/extender_licencia.html'
    success_url = reverse_lazy('rrhh:licencias_list')

    def get_queryset(self):
        return super().get_queryset().filter(empleado__in=obtener_personal_permitido(self.request.user))

    def test_func(self):
        return puede_cargar_licencias(self.request.user) or es_rrhh(self.request.user)

    def form_valid(self, form):
        # Al extender, el estado vuelve a Pendiente de Certificado o Entregado si subió archivo
        # para que RRHH vuelva a auditar la extensión.
        instance = form.save(commit=False)
        if instance.adjunto_pdf:
            instance.estado = 'Entregado'
        else:
            instance.estado = 'Pendiente_Certificado'
        return super().form_valid(form)


class SeguimientoMedicoDetailView(LoginRequiredMixin, BaseLicenciaContextMixin, DetailView):
    model = SolicitudLicencia
    template_name = 'rrhh/licencias/detalle_seguimiento_medico.html'
    context_object_name = 'solicitud'

    def get_queryset(self):
        return super().get_queryset().filter(empleado__in=obtener_personal_permitido(self.request.user))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['seguimientos'] = self.object.seguimientos.all().order_by('-fecha_consulta')
        return context


class SeguimientoMedicoCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = SeguimientoMedico
    form_class = SeguimientoMedicoForm
    template_name = 'rrhh/licencias/seguimiento_form.html'

    def test_func(self): return es_rrhh(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['solicitud_id'] = self.kwargs['solicitud_id']
        return context

    def form_valid(self, form):
        form.instance.solicitud_id = self.kwargs['solicitud_id']
        response = super().form_valid(form)
        
        # Procesar Extensión Opcional
        ext_hasta = form.cleaned_data.get('extender_hasta')
        ext_cert = form.cleaned_data.get('nuevo_certificado')
        
        if ext_hasta or ext_cert:
            solicitud = form.instance.solicitud
            if ext_hasta:
                solicitud.fecha_hasta = ext_hasta
            if ext_cert:
                solicitud.adjunto_pdf = ext_cert
            
            # Al extender por seguimiento, reseteamos a Entregado o Pendiente según el archivo
            if solicitud.adjunto_pdf:
                solicitud.estado = 'Entregado'
            else:
                solicitud.estado = 'Pendiente_Certificado'
            
            solicitud.save()
            
        return response

    def get_success_url(self):
        return reverse_lazy('rrhh:seguimiento_detalle', kwargs={'pk': self.kwargs['solicitud_id']})


class SeguimientoMedicoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = SeguimientoMedico
    form_class = SeguimientoMedicoForm
    template_name = 'rrhh/licencias/seguimiento_form.html'

    def test_func(self): return es_rrhh(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['solicitud_id'] = self.object.solicitud_id
        return context

    def get_success_url(self):
        return reverse_lazy('rrhh:seguimiento_detalle', kwargs={'pk': self.object.solicitud_id})
