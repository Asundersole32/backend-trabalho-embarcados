from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets
from django.contrib.auth.models import User
from django.conf import settings
from core.models import SensorLog, Alert, ManualControl, Classification, Sensor, Actuator
from core.serializers import ProfileSerializer, SensorDataSerializer, ActuatorDataSerializer, AlertSerializer, ManualControlSerializer, UserRegistrationSerializer, SensorLogSerializer, ClassificationSerializer, SensorSerializer, ActuatorSerializer
from core.services.mqtt_client import mqtt_client
import json
from datetime import datetime

def get_system_user():
        try:
            return User.objects.get_or_create(username='sistema')[0]
        except User.DoesNotExist:
            return User.objects.create_user(username='sistema', password='senha_temporaria')

class SensorDataView(APIView):
    def post(self, request):
        """Endpoint /api/sensor-data - recebe dados via HTTP (post)"""
        serializer = SensorDataSerializer(data=request.data)
        if serializer.is_valid():
            # Salva o log (necessário associar um Sensor)
            # Para simplificar, busca o sensor padrão
            from core.models import Sensor
            sensor, _ = Sensor.objects.get_or_create(nome="RPi3Bplus-01", tipo="DHT22/BMP280")
            user = get_system_user()
            log = SensorLog.objects.create(
                user=user,
                sensor=sensor,
                temperatura=serializer.validated_data['temperatura'],
                umidade=serializer.validated_data['umidade'],
                pressao=serializer.validated_data['pressao'],
                validacao=serializer.validated_data.get('validacao', True)
            )
            # Reutilizar a lógica de classificação e atuação do MQTT
            from core.services.classification_service import ClassificationService
            ClassificationService().classify(log.id)
            # Disparar a decisão manual via função auxiliar (copiada do mqtt_client)
            self._processar_decisao(log)
            return Response({"status": "success", "message": "Dados recebidos com sucesso"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _processar_decisao(self, sensor_log):
        """Similar ao process_sensor_data do MQTT, mas usando o log já salvo."""
        from core.models import ManualControl
        override = ManualControl.objects.filter(ativo=True).first()
        if override and override.estado_desejado != 'AUTO':
            mqtt_client.acionar_tenda(abrir=(override.estado_desejado == 'ABRIR'))
            return
        # Reclassificar (já tem classification? vamos buscar)
        classification = sensor_log.classification  # via OneToOne
        if classification.resultado in ['CHUVA_FRACA', 'CHUVA_FORTE']:
            user = sensor_log.user
            if user.profile.celular:
                from core.services.sms_service import SMSService
                
                mensagem_sms = f"Alerta: {classification.get_resultado_display()} detectada. Tenda fechada automaticamente."
                SMSService.send_sms(user.profile.celular, mensagem_sms)

            mqtt_client.acionar_tenda(abrir=False)
        else:
            mqtt_client.acionar_tenda(abrir=True)
    
    def get_system_user():
        try:
            return User.objects.get(id=settings.SYSTEM_USER_ID)
        except User.DoesNotExist:
            return User.objects.create_user(username='sistema', password='senha_temporaria')

class ActuatorDataView(APIView):
    def post(self, request):
        serializer = ActuatorDataSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AlertsDataView(APIView):
    def get(self, request):
        alerts = Alert.objects.all().order_by('-created_at')
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)

class ManualControlView(APIView):
    def post(self, request):
        serializer = ManualControlSerializer(data=request.data)
        if serializer.is_valid():
            # Desativa overrides anteriores e cria novo
            ManualControl.objects.filter(ativo=True).update(ativo=False)
            ManualControl.objects.create(
                user=request.user if request.user.is_authenticated else None,
                estado_desejado=serializer.validated_data['estado_desejado'],
                ativo=True
            )
            return Response({"status": "override aplicado"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "Usuário criado com sucesso"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Listagem de logs de sensores do usuário autenticado
class UserSensorLogsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        logs = SensorLog.objects.filter(user=request.user).order_by('-created_at')
        serializer = SensorLogSerializer(logs, many=True)
        return Response(serializer.data)

# Listagem de classificações do usuário autenticado
class UserClassificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        classifications = Classification.objects.filter(user=request.user).order_by('-created_at')
        serializer = ClassificationSerializer(classifications, many=True)
        return Response(serializer.data)

# Listagem de alertas do usuário autenticado (substitui o endpoint anterior /api/alerts-data)
class UserAlertsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        alerts = Alert.objects.filter(user=request.user).order_by('-created_at')
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)
    
class SensorViewSet(viewsets.ModelViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    permission_classes = [permissions.IsAuthenticated]

class ActuatorViewSet(viewsets.ModelViewSet):
    queryset = Actuator.objects.all()
    serializer_class = ActuatorSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile)
        return Response({
            'username': request.user.username,
            'email': request.user.email,
            **serializer.data
        })

    def patch(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)