# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from core.models import (
    Sensor, Actuator, SensorLog, ActuatorLog,
    Classification, Alert, ManualControl, Profile
)

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False

class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'email', 'get_celular', 'is_staff')

    def get_celular(self, obj):
        return obj.profile.celular
    get_celular.short_description = 'Celular'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'tipo', 'status', 'created_at')
    list_filter = ('tipo', 'status')
    search_fields = ('nome', 'tipo')
    readonly_fields = ('created_at',)

@admin.register(Actuator)
class ActuatorAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'tipo', 'status', 'created_at')
    list_filter = ('tipo', 'status')
    search_fields = ('nome', 'tipo')
    readonly_fields = ('created_at',)

@admin.register(SensorLog)
class SensorLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'sensor', 'temperatura', 'umidade', 'pressao', 'validacao', 'created_at')
    list_filter = ('validacao', 'created_at', 'user')
    search_fields = ('user__username', 'sensor__nome')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'sensor')

@admin.register(ActuatorLog)
class ActuatorLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'actuator', 'acionado', 'created_at')
    list_filter = ('acionado', 'created_at')
    search_fields = ('user__username', 'actuator__nome')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'actuator')

@admin.register(Classification)
class ClassificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'sensor_log', 'resultado', 'probabilidade', 'created_at')
    list_filter = ('resultado', 'created_at')
    search_fields = ('user__username', 'sensor_log__id')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'sensor_log')

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'classification', 'mensagem', 'enviado_mqtt', 'created_at')
    list_filter = ('enviado_mqtt', 'created_at')
    search_fields = ('user__username', 'mensagem')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'classification')

@admin.register(ManualControl)
class ManualControlAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'estado_desejado', 'ativo', 'updated_at')
    list_filter = ('estado_desejado', 'ativo', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('updated_at',)
    raw_id_fields = ('user',)