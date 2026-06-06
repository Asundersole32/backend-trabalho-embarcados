from django.core.management.base import BaseCommand
from core.services.mqtt_client import mqtt_client
import time

class Command(BaseCommand):
    help = 'Inicia o cliente MQTT em uma thread separada'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando cliente MQTT...")
        mqtt_client.start()
        self.stdout.write("Cliente MQTT rodando. Pressione Ctrl+C para parar.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            mqtt_client.stop()
            self.stdout.write("Cliente MQTT finalizado.")