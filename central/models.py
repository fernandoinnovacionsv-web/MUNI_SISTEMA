from django.db import models
from django.utils import timezone

class Movimiento(models.Model):
    """Registro de movimientos o novedades en el sistema (alta, baja, cambio de área, etc.)"""
    TIPO_CHOICES = [
        ('alta', 'Alta de Personal'),
        ('baja', 'Baja de Personal'),
        ('cambio', 'Cambio de Área'),
        ('licencia', 'Licencia'),
        ('otro', 'Otro'),
    ]

    empleado = models.CharField(max_length=100, verbose_name="Empleado")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Movimiento")
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha del Movimiento")
    observacion = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.empleado} - {self.get_tipo_display()} ({self.fecha})"
