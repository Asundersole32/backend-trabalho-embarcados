import paho.mqtt.client as mqtt
import json
from django.contrib.auth.models import User
from django.conf import settings
from core.models import Sensor, SensorLog, Actuator, ActuatorLog, Alert
from core.services.classification_service import ClassificationService

def get_system_user():
        try:
            return User.objects.get_or_create(username='sistema')[0]
        except User.DoesNotExist:
            return User.objects.create_user(username='sistema', password='senha_temporaria')

class MQTTClient:
    def __init__(self):
        self.broker = settings.MQTT_BROKER
        self.port = settings.MQTT_PORT
        self.topics = settings.MQTT_TOPICS
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.classifier = ClassificationService()
        self.running = False

    def on_connect(self, client, userdata, flags, rc):
        print(f"Conectado ao broker MQTT com código {rc}")
        # Inscreve nos tópicos de interesse
        client.subscribe(self.topics['sensor_data'])
        client.subscribe(self.topics['actuator_status'])
        client.subscribe(self.topics['actuator_activate'])

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        print(f"Mensagem recebida no tópico {topic}: {payload}")

        if topic == self.topics['sensor_data']:
            self.process_sensor_data(payload)
        elif topic == self.topics['actuator_status']:
            self.process_actuator_status(payload)
        elif topic == self.topics['actuator_activate']:
            self.process_actuator_command(payload)

    def process_sensor_data(self, data):
        """Salva leitura, classifica e aciona atuadores conforme necessário."""
        # Obter ou criar sensor (supondo que o id no payload é o nome)
        sensor, _ = Sensor.objects.get_or_create(nome=data.get('id', 'RPi3Bplus-01'), tipo='DHT22/BMP280')
        user = get_system_user()
        log = SensorLog.objects.create(
            user=user,
            sensor=sensor,
            temperatura=data['temperatura'],
            umidade=data['umidade'],
            pressao=data['pressao'],
            validacao=data.get('validacao', True)
        )
        # Classificar o dado
        classification = self.classifier.classify(log.id)

        # Verificar override manual do usuário (pelo primeiro usuário ativo)
        from core.models import ManualControl
        override = ManualControl.objects.filter(ativo=True).first()
        if override and override.estado_desejado != 'AUTO':
            # Respeita comando manual
            if override.estado_desejado == 'ABRIR':
                self.acionar_tenda(abrir=True)
            else:
                self.acionar_tenda(abrir=False)
            return

        # Decisão automática baseada na classificação
        if classification.resultado in ['CHUVA_FRACA', 'CHUVA_FORTE']:
            self.acionar_tenda(abrir=False)   # Fechar tenda
            # Gerar alerta
            user = get_system_user()
            if user.profile.celular:
                from core.services.sms_service import SMSService
                
                mensagem_sms = f"Alerta: {classification.get_resultado_display()} detectada. Tenda fechada automaticamente."
                SMSService.send_sms(user.profile.celular, mensagem_sms)
            
            alert = Alert.objects.create(
                user=user,
                classification=classification,
                mensagem=f"Alerta de {classification.get_resultado_display()} detectada. Tenda fechada."
            )
            # Publicar alerta no tópico MQTT
            self.client.publish(self.topics['alert'], json.dumps({
                'alerta_id': alert.id,
                'mensagem': alert.mensagem,
                'classificacao': classification.resultado
            }))
        else:
            self.acionar_tenda(abrir=True)    # Abrir tenda (clima limpo)

    def acionar_tenda(self, abrir):
        """Publica comando para os servos motores."""
        angulo = 0 if abrir else 90   # 0° aberto, 90° fechado (exemplo)
        comando = {
            'atuadores_status': not abrir,  # False = aberto? Conforme payload exemplo
            'angulo_servo1': angulo,
            'angulo_servo2': angulo,
            'created_at': '2026-05-17T23:54:06'  # Preencher com datetime.now()
        }
        self.client.publish(self.topics['actuator_activate'], json.dumps(comando))
        # Registrar log do atuador
        servo = Actuator.objects.get_or_create(nome='servo_motor', tipo='servo')[0]
        user = get_system_user()
        ActuatorLog.objects.create(
            user=user,
            actuator=servo,
            acionado=True,
            parametros={'angulo': angulo, 'abrir': abrir}
        )

    def process_actuator_status(self, payload):
        print(f"Status atual dos atuadores: {payload}")

    def process_actuator_command(self, payload):
        print(f"Comando de atuação recebido: {payload}")

    def start(self):
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        self.running = True

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.running = False

# Instância global (será inicializada pelo comando)
mqtt_client = MQTTClient()