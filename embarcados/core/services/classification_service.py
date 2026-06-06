import joblib
import os
import logging
from django.conf import settings
from core.models import SensorLog, Classification

logger = logging.getLogger(__name__)

class ClassificationService:
    def __init__(self):
        self.model = None
        if os.path.exists(settings.ML_MODEL_PATH):
            try:
                self.model = joblib.load(settings.ML_MODEL_PATH)
                logger.info(f"Modelo carregado com sucesso de {settings.ML_MODEL_PATH}")
            except Exception as e:
                logger.error(f"Erro ao carregar modelo: {e}. Usando regras de limiar.")
        else:
            logger.warning(f"Arquivo do modelo não encontrado em {settings.ML_MODEL_PATH}. Usando regras de limiar.")

    def classify(self, sensor_log_id):
        log = SensorLog.objects.get(id=sensor_log_id)
        temp = log.temperatura
        umid = log.umidade
        press = log.pressao

        if self.model:
            try:
                features = [[temp, umid, press]]
                pred = self.model.predict(features)[0]
                prob = max(self.model.predict_proba(features)[0])
                resultado = dict(enumerate(['LIMPO', 'CHUVA_FRACA', 'CHUVA_FORTE']))[pred]
            except Exception as e:
                logger.error(f"Erro na predição: {e}. Usando fallback.")
                resultado = self._fallback_classify(temp, umid, press)
                prob = None
        else:
            resultado = self._fallback_classify(temp, umid, press)
            prob = None

        classification = Classification.objects.create(
            user=log.user,
            sensor_log=log,
            resultado=resultado,
            probabilidade=prob
        )
        return classification

    def _fallback_classify(self, temp, umid, press):
        """Regras de limiar simples (fallback)"""
        if umid > 80 and temp < 25:
            return 'CHUVA_FORTE'
        elif umid > 65:
            return 'CHUVA_FRACA'
        else:
            return 'LIMPO'