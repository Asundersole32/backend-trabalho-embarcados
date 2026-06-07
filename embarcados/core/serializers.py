from rest_framework import serializers
from core.models import SensorLog, ActuatorLog, Alert, Classification, ManualControl, Sensor, Actuator, Profile
from django.contrib.auth.models import User


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['celular']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    celular = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'celular']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("As senhas não coincidem")
        return data

    def create(self, validated_data):
        celular = validated_data.pop('celular', '')
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        if celular:
            user.profile.celular = celular
            user.profile.save()
        return user

class SensorLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorLog
        fields = ['id', 'temperatura', 'umidade', 'pressao', 'created_at']

class ClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classification
        fields = ['id', 'resultado', 'probabilidade', 'created_at']

class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorLog
        fields = ['id', 'temperatura', 'umidade', 'pressao', 'validacao', 'created_at']
        extra_kwargs = {'id': {'read_only': True}}

class ActuatorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActuatorLog
        fields = ['id', 'actuator', 'acionado', 'parametros', 'created_at']

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'

class ManualControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManualControl
        fields = ['estado_desejado', 'ativo']

class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ['id', 'nome', 'tipo', 'status', 'created_at']
        read_only_fields = ['created_at']

class ActuatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actuator
        fields = ['id', 'nome', 'tipo', 'status', 'created_at']
        read_only_fields = ['created_at']

class ActuatorLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActuatorLog
        fields = '__all__'