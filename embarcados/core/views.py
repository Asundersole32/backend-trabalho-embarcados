from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets
from django.contrib.auth.models import User
from django.conf import settings
from core.models import SensorLog, Alert, ManualControl, Classification, Sensor, Actuator, ActuatorLog
from core.serializers import ProfileSerializer, SensorDataSerializer, ActuatorDataSerializer, AlertSerializer, ManualControlSerializer, UserRegistrationSerializer, SensorLogSerializer, ClassificationSerializer, SensorSerializer, ActuatorSerializer, ActuatorLogSerializer
from core.services.mqtt_client import mqtt_client
from core.services.classification_service import ClassificationService
from core.services.sms_service import SMSService
import json
from datetime import datetime

# ---------- FUNÇÃO GLOBAL PARA OBTER USUÁRIO SISTEMA ----------
def get_system_user():
    try:
        return User.objects.get(username='sistema')
    except User.DoesNotExist:
        return User.objects.create_user(username='sistema', password='senha_temporaria')


# ---------- VIEWS ----------
class SensorDataView(APIView):
    def post(self, request):
        serializer = SensorDataSerializer(data=request.data)
        if serializer.is_valid():
            sensor, _ = Sensor.objects.get_or_create(nome="RPi3Bplus-01", tipo="DHT22/BMP280")
            user = get_system_user()   # usa função global
            log = SensorLog.objects.create(
                user=user,
                sensor=sensor,
                temperatura=serializer.validated_data['temperatura'],
                umidade=serializer.validated_data['umidade'],
                pressao=serializer.validated_data['pressao'],
                validacao=serializer.validated_data.get('validacao', True)
            )
            ClassificationService().classify(log.id)
            self._processar_decisao(log)
            return Response({"status": "success", "message": "Dados recebidos com sucesso"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _processar_decisao(self, sensor_log):
        override = ManualControl.objects.filter(ativo=True).first()
        if override and override.estado_desejado != 'AUTO':
            mqtt_client.acionar_tenda(abrir=(override.estado_desejado == 'ABRIR'))
            return
        classification = sensor_log.classification
        if classification.resultado in ['CHUVA_FRACA', 'CHUVA_FORTE']:
            user = sensor_log.user
            if user.profile.celular:
                mensagem_sms = f"Alerta: {classification.get_resultado_display()} detectada. Tenda fechada automaticamente."
                SMSService.send_sms(user.profile.celular, mensagem_sms)
            mqtt_client.acionar_tenda(abrir=False)
        else:
            mqtt_client.acionar_tenda(abrir=True)


class ActuatorDataView(APIView):
    def post(self, request):
        serializer = ActuatorDataSerializer(data=request.data)
        if serializer.is_valid():
            # associa ao usuário sistema
            user = get_system_user()
            actuator = Actuator.objects.get_or_create(nome='servo_motor', tipo='servo')[0]
            ActuatorLog.objects.create(
                user=user,
                actuator=actuator,
                acionado=serializer.validated_data.get('atuadores_status', False),
                parametros={
                    'angulo_servo1': serializer.validated_data.get('angulo_servo1', 0),
                    'angulo_servo2': serializer.validated_data.get('angulo_servo2', 0)
                }
            )
            return Response({"status": "success"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AlertsDataView(APIView):
    def get(self, request):
        alerts = Alert.objects.all().order_by('-created_at')
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)


class ManualControlView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ManualControlSerializer(data=request.data)
        if serializer.is_valid():
            ManualControl.objects.filter(ativo=True).update(ativo=False)
            ManualControl.objects.create(
                user=request.user,
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
            serializer.save()
            return Response({"message": "Usuário criado com sucesso"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- ENDPOINTS COM FILTRO: USUÁRIO + SISTEMA ----------
class UserSensorLogsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        system_user = get_system_user()
        logs = SensorLog.objects.filter(
            user__in=[request.user, system_user]
        ).order_by('-created_at')
        serializer = SensorLogSerializer(logs, many=True)
        return Response(serializer.data)


class UserClassificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        system_user = get_system_user()
        classifications = Classification.objects.filter(
            user__in=[request.user, system_user]
        ).order_by('-created_at')
        serializer = ClassificationSerializer(classifications, many=True)
        return Response(serializer.data)


class UserAlertsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        system_user = get_system_user()
        alerts = Alert.objects.filter(
            user__in=[request.user, system_user]
        ).order_by('-created_at')
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)


class UserActuatorLogsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        system_user = get_system_user()
        logs = ActuatorLog.objects.filter(
            user__in=[request.user, system_user]
        ).order_by('-created_at')[:50]
        serializer = ActuatorLogSerializer(logs, many=True)   # Serializer específico
        return Response(serializer.data)


# ---------- OUTROS VIEWSETS ----------
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