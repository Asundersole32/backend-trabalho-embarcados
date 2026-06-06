from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import post_save

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    celular = models.CharField('Celular com DDD', max_length=20, blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} - {self.celular or "sem celular"}'

# Sinal: cria Profile automaticamente quando um User é criado
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Sensor(models.Model):
    nome = models.CharField(max_length=50)
    tipo = models.CharField(max_length=30)  # "DHT22", "BMP280"
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

class Actuator(models.Model):
    nome = models.CharField(max_length=50)
    tipo = models.CharField(max_length=30)  # "servo", "buzzer", "led"
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

class SensorLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sensor_logs')
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    temperatura = models.FloatField()
    umidade = models.FloatField()
    pressao = models.FloatField()
    validacao = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ActuatorLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actuator_logs')
    actuator = models.ForeignKey(Actuator, on_delete=models.CASCADE)
    acionado = models.BooleanField()
    parametros = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

class Classification(models.Model):
    CLIMA_CHOICES = [
        ('LIMPO', 'Clima Limpo'),
        ('CHUVA_FRACA', 'Chuva Fraca'),
        ('CHUVA_FORTE', 'Chuva Forte'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='classifications')
    sensor_log = models.OneToOneField(SensorLog, on_delete=models.CASCADE)
    resultado = models.CharField(max_length=20, choices=CLIMA_CHOICES)
    probabilidade = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Alert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    classification = models.ForeignKey(Classification, on_delete=models.CASCADE)
    mensagem = models.TextField()
    enviado_mqtt = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class ManualControl(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    estado_desejado = models.CharField(max_length=10, choices=[('ABRIR', 'Abrir'), ('FECHAR', 'Fechar'), ('AUTO', 'Automático')], default='AUTO')
    ativo = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)