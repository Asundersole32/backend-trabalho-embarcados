import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class SMSService:
    @staticmethod
    def send_sms(to_number, message):
        if not to_number:
            logger.warning("Número de telefone não informado. SMS não enviado.")
            return False

        # Se mock estiver explicitamente ativado, apenas log
        if settings.SMS_MOCK_MODE:
            print(f"[MOCK SMS] Para: {to_number} | Mensagem: {message}")
            return True

        # Se não estiver em mock, mas faltam credenciais, também log (evita erro)
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.warning("Credenciais Twilio não configuradas. SMS não enviado (modo sem mock).")
            return False

        # Envio real
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to_number
            )
            logger.info(f"SMS enviado para {to_number}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar SMS: {e}")
            return False