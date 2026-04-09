import os
from datetime import date
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# =====================================================
#  1. FUNCIONES AUXILIARES (Rutas dinámicas)
# =====================================================

def get_upload_path(instance, filename, subfolder):
    """Función genérica para organizar archivos: [DNI]/[SUBFOLDER]/[ARCHIVO]"""
    # Si la instancia es Empleado, tomamos su DNI directamente
    if isinstance(instance, Empleado):
        dni = instance.dni
    # Si la instancia tiene relación con un Empleado (documentos, licencias, etc.)
    elif hasattr(instance, 'empleado') and instance.empleado:
        dni = instance.empleado.dni
    else:
        dni = "otros"
    
    dni = dni if dni else "sin_dni"
    return f"{dni}/{subfolder}/{filename}"

def foto_path(instance, filename):
    return get_upload_path(instance, filename, "foto")

def documento_path(instance, filename):
    return get_upload_path(instance, filename, "documentos")

def licencia_path(instance, filename):
    return get_upload_path(instance, filename, "licencia")

def vacaciones_path(instance, filename):
    return get_upload_path(instance, filename, "vacaciones")

def comprobante_path(instance, filename):
    return get_upload_path(instance, filename, "indumentaria")

def asistencia_path(instance, filename):
    return get_upload_path(instance, filename, "asistencia")

def registro_path(instance, filename):
    return get_upload_path(instance, filename, "registro")

# =====================================================
#  2. OPCIONES (CHOICES)
# =====================================================

SEXO_CHOICES = [("masculino", "Masculino"), ("femenino", "Femenino"), ("otro", "Otro")]
ESTADO_CIVIL_CHOICES = [
    ("soltero", "Soltero/a"), ("casado", "Casado/a"), 
    ("divorciado", "Divorciado/a"), ("viudo", "Viudo/a"), ("union", "Unión convivencial"),
]
TURNO_CHOICES = [("manana", "Mañana"), ("tarde", "Tarde"), ("noche", "Noche")]
TIPOS_PRENDA_CHOICES = [
    ("PANTALON", "Pantalón"), ("AMBO", "Ambo"), ("CHOMBA", "Chomba"), 
    ("CAMISA", "Camisa"), ("BORCEGO", "Borcego"), ("ZAPATOS", "Zapatos de Seguridad"), 
    ("CAMPERA", "Campera / Abrigo"), ("OTRO", "Otro..."),
]

# =====================================================
#  3. ESTRUCTURA ORGANIZATIVA (ABMs Maestros)
# =====================================================

class Sector(models.Model):
    nombre = models.CharField(max_length=100)
    padre = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subsectores')
    
    def __str__(self):
        if self.padre:
            return f"{self.padre.nombre} > {self.nombre}"
        return self.nombre

    class Meta:
        verbose_name = "Sector/Subsector"
        verbose_name_plural = "Sectores y Subsectores"
        ordering = ['nombre']
        unique_together = ('nombre', 'padre')

class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True) 
    remuneracion_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    def __str__(self): return self.nombre

class CondicionLaboral(models.Model):
    nombre = models.CharField(max_length=50, unique=True) 
    def __str__(self): return self.nombre
    class Meta:
        verbose_name_plural = "Condiciones Laborales"

class TipoMovimiento(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    icono = models.CharField(max_length=30, default="fa-exchange-alt")
    def __str__(self): return self.nombre

class MotivoBaja(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nombre

class ModuloSistema(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    url_acceso = models.CharField(max_length=100)
    icono = models.CharField(max_length=50, default="fa-cube")
    def __str__(self): return self.nombre

# =====================================================
#  4. MODELO PRINCIPAL: EMPLEADO
# =====================================================

class Empleado(models.Model):
    dni = models.CharField(max_length=15, unique=True)
    apellido = models.CharField(max_length=100)
    nombre = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    nacionalidad = models.CharField(max_length=100, blank=True, default="Argentina")
    sexo = models.CharField(max_length=20, choices=SEXO_CHOICES, blank=True)
    
    ciudad = models.CharField(max_length=100, blank=True)
    barrio = models.CharField(max_length=100, blank=True)
    calle = models.CharField(max_length=120, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    estado_civil = models.CharField(max_length=30, choices=ESTADO_CIVIL_CHOICES, blank=True)

    legajo = models.CharField(max_length=20, unique=True)
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="empleados_sector")
    subsector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="empleados_subsector")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    condicion = models.ForeignKey(CondicionLaboral, on_delete=models.SET_NULL, null=True, blank=True)
    turno = models.CharField(max_length=10, choices=TURNO_CHOICES, blank=True)

    fecha_inicio_contrato = models.DateField(null=True, blank=True)
    fecha_fin_contrato = models.DateField(null=True, blank=True)
    inicio_actividad = models.DateField(null=True, blank=True)
    
    activo = models.BooleanField(default=True)
    motivo_baja = models.ForeignKey(MotivoBaja, on_delete=models.SET_NULL, null=True, blank=True)

    correo = models.EmailField(blank=True)
    celular = models.CharField(max_length=30, blank=True)
    contacto_emergencia_nombre = models.CharField(max_length=150, blank=True)
    contacto_emergencia_cel = models.CharField(max_length=30, blank=True)

    foto = models.ImageField(upload_to=foto_path, blank=True, null=True)
    antiguedad_anios = models.PositiveIntegerField(default=0, editable=False)

    def calcular_antiguedad(self):
        if self.inicio_actividad:
            hoy = date.today()
            anios = hoy.year - self.inicio_actividad.year
            if (hoy.month, hoy.day) < (self.inicio_actividad.month, self.inicio_actividad.day):
                anios -= 1
            return max(0, anios)
        return 0

    def save(self, *args, **kwargs):
        self.antiguedad_anios = self.calcular_antiguedad()
        self.apellido = self.apellido.upper() if self.apellido else ""
        self.nombre = self.nombre.upper() if self.nombre else ""
        super().save(*args, **kwargs)
        
        try:
            if self.dni:
                # Aseguramos que existan las carpetas base en el almacenamiento externo
                base = os.path.join(settings.MEDIA_ROOT, self.dni)
                subcarpetas = [
                    "foto", "documentos", "licencia", "vacaciones", 
                    "indumentaria", "asistencia", "registro", "sanciones"
                ]
                for sub in subcarpetas:
                    os.makedirs(os.path.join(base, sub), exist_ok=True)
        except Exception as e:
            print(f"Error creando carpetas para DNI {self.dni}: {e}")

    def __str__(self):
        return self.get_short_name()

    def get_full_name(self):
        return f"{self.nombre} {self.apellido}"

    def get_short_name(self):
        """Retorna 'Apellido, Primer Nombre'"""
        primer_nombre = self.nombre.split()[0] if self.nombre else ""
        return f"{self.apellido}, {primer_nombre}"

# =====================================================
#  5. FAMILIA Y DOCUMENTOS
# =====================================================

class Conyuge(models.Model):
    empleado = models.OneToOneField(Empleado, on_delete=models.CASCADE, related_name="conyuge")
    dni = models.CharField(max_length=15, blank=True)
    nombre = models.CharField(max_length=100, blank=True)
    apellido = models.CharField(max_length=100, blank=True)
    def __str__(self): return f"Cónyuge de {self.empleado}"

class Hijo(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="hijos")
    dni = models.CharField(max_length=15, blank=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    def __str__(self): return f"Hijo de {self.empleado}"

class DocumentoEmpleado(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="documentos")
    tipo = models.CharField(max_length=120)
    archivo = models.FileField(upload_to=documento_path)
    fecha = models.DateField(auto_now_add=True)

# =====================================================
#  6. GESTIÓN DE USUARIOS Y ACCESOS
# =====================================================

class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    empleado = models.OneToOneField(Empleado, on_delete=models.CASCADE)
    es_jefe_area = models.BooleanField(default=False)
    sector_gestion = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True)
    sistemas_habilitados = models.ManyToManyField(ModuloSistema, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.empleado.apellido}"

class SolicitudCuenta(models.Model):
    ESTADOS = [('pendiente', 'Pendiente'), ('creada', 'Cuenta Creada'), ('rechazada', 'Rechazada')]
    jefe_solicitante = models.ForeignKey(User, on_delete=models.CASCADE)
    empleado_a_habilitar = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    motivo_acceso = models.TextField()
    permiso_vacaciones = models.BooleanField(default=False)
    permiso_asistencia = models.BooleanField(default=False)
    permiso_horas_extras = models.BooleanField(default=False)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')

# =====================================================
#  7. RRHH Y VACACIONES
# =====================================================

class Feriado(models.Model):
    nombre = models.CharField(max_length=100)
    fecha = models.DateField(unique=True)
    def __str__(self): return f"{self.nombre} ({self.fecha})"

class Vacacion(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("visto_bueno", "Avalado por Jefe"), ("aprobada", "Aprobada"), ("rechazada", "Rechazada")]
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="vacaciones")
    anio = models.PositiveIntegerField(default=date.today().year)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    fecha_reintegro = models.DateField(null=True, blank=True)
    dias_habiles = models.PositiveIntegerField(default=0, editable=False)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="vacaciones_creadas")
    aprobado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="vacaciones_aprobadas")
    adjunto_solicitud = models.FileField(upload_to=vacaciones_path, null=True, blank=True)
    observaciones = models.TextField(blank=True)

class Movimiento(models.Model):
    tipo = models.ForeignKey(TipoMovimiento, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    detalle = models.TextField(blank=True)

# =====================================================
#  8. INDUMENTARIA (Stock y Entregas)
# =====================================================

class IndumentariaStock(models.Model):
    prenda = models.CharField(max_length=100)
    talle = models.CharField(max_length=20)
    cantidad = models.PositiveIntegerField(default=0)
    def __str__(self): return f"{self.prenda} - Talle {self.talle} ({self.cantidad})"

class EmpleadoTalle(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='talles')
    tipo_prenda = models.CharField(max_length=50, choices=TIPOS_PRENDA_CHOICES) 
    talle = models.CharField(max_length=20)
    class Meta: 
        unique_together = ('empleado', 'tipo_prenda')

class EntregaIndumentaria(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha = models.DateField(auto_now_add=True) 
    prenda = models.CharField(max_length=100)
    talle = models.CharField(max_length=20)
    cantidad = models.PositiveIntegerField(default=1)
    comprobante = models.FileField(upload_to=comprobante_path, null=True, blank=True)
    
# =====================================================
#  9. REGISTRO DE ASISTENCIA Y HORAS EXTRAS
# =====================================================

class RegistroAsistencia(models.Model):
    ESTADOS_ASISTENCIA = [
        ('PRESENTE', 'Presente'),
        ('TARDANZA', 'Tardanza'),
        ('AUSENTE_SIN_AVISO', 'Ausente sin Aviso'),
        ('AUSENTE_CON_AVISO', 'Ausente con Aviso'),
        ('LICENCIA', 'Licencia Médica/Gremial (Bloqueado)'),
        ('SANCION', 'Sanción Disciplinaria'),
    ]

    fecha = models.DateField(default=date.today, verbose_name="Fecha de Registro")
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='asistencias')
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Registrado por")
    estado = models.CharField(max_length=20, choices=ESTADOS_ASISTENCIA, default='PRESENTE')
    
    # Nuevo Campo para Horas Extras
    horas_extras = models.DecimalField(max_digits=4, decimal_places=1, default=0.0)
    
    bloqueado = models.BooleanField(default=False, verbose_name="Bloqueado por Cierre de Mes")
    
    motivo_ausencia = models.TextField(blank=True, null=True, verbose_name="Motivo (si aplica)")
    adjunto_justificativo = models.FileField(
        upload_to=asistencia_path, 
        blank=True, 
        null=True, 
        verbose_name="Certificado/Justificativo"
    )

    class Meta:
        verbose_name = "Registro de Asistencia"
        verbose_name_plural = "Registros de Asistencia"
        unique_together = ('fecha', 'empleado')
        ordering = ['-fecha', 'empleado__apellido']

    def __str__(self):
        return f"{self.fecha} - {self.empleado.get_full_name()} ({self.get_estado_display()})"


class RegistroHoraExtra(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='horas_extras')
    fecha = models.DateField(verbose_name="Fecha de la Actividad")
    hora_inicio = models.TimeField(verbose_name="Hora Incial")
    hora_fin = models.TimeField(verbose_name="Hora Final")
    horas_totales = models.DecimalField(max_digits=5, decimal_places=2, help_text="Calculado automáticamente", verbose_name="Total Horas")
    motivo_actividad = models.TextField(verbose_name="Detalle de la Actividad")
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Registrado por")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Hora Extra"
        verbose_name_plural = "Registros de Horas Extras"
        ordering = ['-fecha', 'empleado__apellido']

    def __str__(self):
        return f"{self.fecha} - {self.empleado.get_full_name()} ({self.horas_totales} hs)"


# =====================================================
#  10. BANCO DE HORAS Y FRANCOS
# =====================================================

class TransaccionBancoHoras(models.Model):
    TIPO_CHOICES = [
        ('HORA_EXTRA', 'Horas Extras Realizadas'),
        ('FRANCO', 'Día de Franco Tomado'),
        ('PAGO', 'Horas Cobradas / Pagas'),
        ('AJUSTE', 'Ajuste Manual'),
    ]

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='transacciones_banco')
    fecha = models.DateField(default=date.today)
    cantidad = models.DecimalField(max_digits=6, decimal_places=2, help_text="Positivo para suma, Negativo para resta")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    referencia_id = models.PositiveIntegerField(null=True, blank=True, help_text="ID del registro relacionado (si aplica)")
    detalle = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Transacción de Banco de Horas"
        verbose_name_plural = "Transacciones de Banco de Horas"
        ordering = ['-fecha', '-fecha_registro']

    def __str__(self):
        return f"{self.empleado.get_short_name()} | {self.tipo} | {self.cantidad} hs"

class FrancoProgramado(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='francos_programados')
    fecha = models.DateField()
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Franco Programado"
        verbose_name_plural = "Francos Programados"
        unique_together = ('empleado', 'fecha')
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.fecha} - {self.empleado.get_short_name()} (Franco)"

# =====================================================
#  11. GESTIÓN DE LICENCIAS
# =====================================================

class CategoriaLicencia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    requiere_seguimiento_medico = models.BooleanField(default=False)
    requiere_certificado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Categoría de Licencia"
        verbose_name_plural = "Categorías de Licencia"

    def __str__(self):
        return self.nombre

class TipoLicencia(models.Model):
    categoria = models.ForeignKey(CategoriaLicencia, on_delete=models.CASCADE, related_name='tipos')
    nombre = models.CharField(max_length=100)
    limite_dias_anual = models.PositiveIntegerField(help_text="Límite de días por año calendario")
    es_dias_habiles = models.BooleanField(default=True, help_text="Si es True, descuenta sábados, domingos y feriados")
    detalle = models.TextField(blank=True)

    class Meta:
        verbose_name = "Tipo de Licencia"
        verbose_name_plural = "Tipos de Licencia"

    def __str__(self):
        return self.nombre

class SolicitudLicencia(models.Model):
    ESTADOS = [
        ('Pendiente_Certificado', 'Pendiente de Certificado (Provisorio)'),
        ('Entregado', 'Certificado Entregado'),
        ('Aprobada', 'Aprobada'),
        ('Rechazada', 'Rechazada'),
    ]

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='solicitudes_licencia')
    tipo_licencia = models.ForeignKey(TipoLicencia, on_delete=models.CASCADE)
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField()
    estado = models.CharField(max_length=30, choices=ESTADOS, default='Pendiente_Certificado')
    adjunto_pdf = models.FileField(upload_to=licencia_path, blank=True, null=True)
    observaciones = models.TextField(blank=True)
    motivo_rechazo = models.TextField(blank=True, verbose_name="Motivo de Rechazo")

    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Solicitud de Licencia"
        verbose_name_plural = "Solicitudes de Licencias"
        ordering = ['-fecha_desde', 'empleado__apellido']
        permissions = [
            ("can_audit_licencias", "Puede auditar, seguir y aprobar licencias"),
        ]

    def calcular_dias_habiles(self):
        """Calcula la cantidad de días que consume la licencia"""
        dias_totales = (self.fecha_hasta - self.fecha_desde).days + 1
        if not self.tipo_licencia.es_dias_habiles:
            return max(0, dias_totales)
            
        import datetime
        dias = 0
        feriados_fechas = list(Feriado.objects.filter(
            fecha__range=[self.fecha_desde, self.fecha_hasta]
        ).values_list('fecha', flat=True))

        current = self.fecha_desde
        while current <= self.fecha_hasta:
            if current.weekday() < 5 and current not in feriados_fechas:
                dias += 1
            current += datetime.timedelta(days=1)
        return dias

    def __str__(self):
        return f"Licencia {self.tipo_licencia.nombre} - {self.empleado.get_short_name()}"

    def save(self, *args, **kwargs):
        # Transición automática: si hay archivo y el estado es 'Pendiente', pasa a 'Entregado'
        if self.adjunto_pdf and self.estado == 'Pendiente_Certificado':
            self.estado = 'Entregado'
        # Si NO hay archivo y está en 'Entregado' (ej: se borró el archivo), vuelve a 'Pendiente'
        elif not self.adjunto_pdf and self.estado == 'Entregado':
            self.estado = 'Pendiente_Certificado'
            
        super().save(*args, **kwargs)

        # Al aprobar una licencia, sincronizar con el registro de asistencia
        if self.estado == 'Aprobada':
            from datetime import timedelta
            curr_f = self.fecha_desde
            while curr_f <= self.fecha_hasta:
                RegistroAsistencia.objects.update_or_create(
                    empleado=self.empleado,
                    fecha=curr_f,
                    defaults={
                        'estado': 'LICENCIA',
                        'motivo_ausencia': f"Licencia Aprobada: {self.tipo_licencia.nombre}"
                    }
                )
                curr_f += timedelta(days=1)

    def clean(self):
        from django.core.exceptions import ValidationError
        import datetime
        
        if self.fecha_hasta and self.fecha_desde and self.fecha_hasta < self.fecha_desde:
            raise ValidationError({'fecha_hasta': "La fecha de fin no puede ser anterior a la fecha de inicio."})

        if self.fecha_desde and self.fecha_hasta and self.tipo_licencia:
            anio_actual = datetime.date.today().year
            
            solicitudes_anio = SolicitudLicencia.objects.filter(
                empleado=self.empleado,
                tipo_licencia=self.tipo_licencia,
                fecha_desde__year=anio_actual
            ).exclude(estado='Rechazada')
            
            if self.pk:
                solicitudes_anio = solicitudes_anio.exclude(pk=self.pk)

            dias_consumidos = sum(sol.calcular_dias_habiles() for sol in solicitudes_anio)
            dias_solicitados = self.calcular_dias_habiles()
            
            if (dias_consumidos + dias_solicitados) > self.tipo_licencia.limite_dias_anual:
                raise ValidationError(
                    f"Supera el límite anual. Límite: {self.tipo_licencia.limite_dias_anual} días. "
                    f"Consumidos: {dias_consumidos}. Solicitados: {dias_solicitados}."
                )

        if hasattr(self, 'tipo_licencia') and getattr(self.tipo_licencia, 'categoria', None):
            if self.tipo_licencia.categoria.requiere_certificado:
                if self.estado == 'Aprobada' and not self.adjunto_pdf:
                    raise ValidationError({'adjunto_pdf': "No se puede aprobar la licencia sin un PDF adjunto."})

class SeguimientoMedico(models.Model):
    solicitud = models.ForeignKey(SolicitudLicencia, on_delete=models.CASCADE, related_name='seguimientos')
    fecha_consulta = models.DateField(default=date.today)
    medico = models.CharField(max_length=150)
    evolucion = models.TextField()
    proximo_control = models.DateField(null=True, blank=True)
    es_alta_medica = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Seguimiento Médico"
        verbose_name_plural = "Seguimientos Médicos"
        ordering = ['-fecha_consulta']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Si es Alta Médica, desbloqueamos los días restantes en la asistencia
        if self.es_alta_medica:
            from datetime import timedelta
            # Buscamos los registros de asistencia de este empleado que tengan estado LICENCIA
            # desde el día siguiente al alta hasta el final de la licencia original
            solicitud = self.solicitud
            fecha_referencia = self.fecha_consulta + timedelta(days=1)
            
            if fecha_referencia <= solicitud.fecha_hasta:
                RegistroAsistencia.objects.filter(
                    empleado=solicitud.empleado,
                    fecha__range=[fecha_referencia, solicitud.fecha_hasta],
                    estado='LICENCIA'
                ).delete() # O podríamos pasarlos a PRESENTE, pero eliminarlos permite al jefe volver a tomarlos.

    def __str__(self):
        return f"Seguimiento para {self.solicitud.empleado.get_short_name()} el {self.fecha_consulta}"