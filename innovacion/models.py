from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# --- MODELOS PARA PERMISOS GRANULARES ---

class SistemaMunicipal(models.Model):
    nombre = models.CharField(max_length=100) # Ej: Recursos Humanos
    codigo = models.SlugField(unique=True)     # Ej: rrhh
    icono = models.CharField(max_length=50, default="fas fa-desktop")

    def __str__(self):
        return self.nombre

class FuncionSistema(models.Model):
    sistema = models.ForeignKey(SistemaMunicipal, related_name='funciones', on_delete=models.CASCADE)
    nombre_visible = models.CharField(max_length=100) 
    codigo_interno = models.CharField(max_length=100, unique=True) 

    def __str__(self):
        return f"{self.sistema.nombre} - {self.nombre_visible}"

class PerfilAcceso(models.Model):
    """Asocia un usuario con sus funciones permitidas y estado de cuenta"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_innovacion')
    
    # Vinculamos el usuario con su legajo de RRHH
    empleado = models.OneToOneField('rrhh.Empleado', on_delete=models.SET_NULL, null=True, blank=True, related_name='usuario_sistema')
    
    funciones = models.ManyToManyField(FuncionSistema, blank=True)
    esta_activo = models.BooleanField(default=True)
    puede_solicitar = models.BooleanField(default=True, help_text="Habilita al usuario para cargar vacaciones/tramites")
    observaciones = models.TextField(blank=True)

    def __str__(self):
        nombre_emp = f"{self.empleado.apellido} {self.empleado.nombre}" if self.empleado else self.user.username
        return f"Perfil de {nombre_emp}"

    def save(self, *args, **kwargs):
        # CORRECCIÓN DE SEGURIDAD: 
        # Solo validamos si el objeto YA EXISTE (para no trabar la creación inicial)
        # y si efectivamente se está intentando activar.
        if self.esta_activo:
            if not self.empleado:
                raise ValidationError("No se puede activar un acceso sin vincularlo a un Empleado de RRHH.")
            
            # Verificamos que el empleado tenga sector
            if not self.empleado.sector:
                raise ValidationError(f"El empleado {self.empleado} no tiene un SECTOR asignado en su ficha de RRHH.")
        
        super().save(*args, **kwargs)

# --- MODELO DE SOLICITUD ---

class SolicitudAcceso(models.Model):
    ESTADOS = (
        ('PENDIENTE', 'Pendiente'),
        ('PROCESADO', 'Procesado'),
        ('RECHAZADO', 'Solicitud Rechazada'),
    )
    empleado = models.ForeignKey('rrhh.Empleado', on_delete=models.CASCADE)
    solicitado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')

    def __str__(self):
        return f"{self.empleado.apellido} - {self.estado}"