from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from .models import Empleado, Movimiento

@receiver(post_save, sender=Empleado)
def calcular_antiguedad(sender, instance, created, **kwargs):
    """Actualiza automáticamente la antigüedad y crea movimiento al registrar."""
    if instance.inicio_actividad:
        today = date.today()
        diff = today.year - instance.inicio_actividad.year
        if (today.month, today.day) < (instance.inicio_actividad.month, instance.inicio_actividad.day):
            diff -= 1
        instance.antiguedad_anios = diff
        instance.save(update_fields=["antiguedad_anios"])

    if created:
        from .models import TipoMovimiento
        tipo_alta = TipoMovimiento.objects.filter(nombre='ALTA').first()
        if tipo_alta:
            Movimiento.objects.create(
                tipo=tipo_alta,
                empleado=instance,
                detalle=f"Registro inicial del agente en el sistema.",
                usuario=None # Opcional: podrías intentar obtener el usuario actual si fuera posible
            )
