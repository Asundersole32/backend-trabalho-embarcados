import joblib
import os
from django.conf import settings
from core.models import SensorLog, Classification

class ClassificationService:
    def __init__(self):
        self.model = None
        if os.path.exists(settings.ML_MODEL_PATH):
            self.model = joblib.load(settings.ML_MODEL_PATH)
            print("Modelo Random Forest carregado com sucesso.")
        else:
            print("Arquivo do modelo não encontrado. Usando regras de limiar.")

    def classify(self, sensor_log_id):
        """Classifica um SensorLog e retorna a categoria."""
        log = SensorLog.objects.get(id=sensor_log_id)
        temp = log.temperatura
        umid = log.umidade
        press = log.pressao

        if self.model:
            # Se modelo treinado disponível
            features = [[temp, umid, press]]
            pred = self.model.predict(features)[0]  # 0: LIMPO, 1: CHUVA_FRACA, 2: CHUVA_FORTE
            prob = max(self.model.predict_proba(features)[0])
            resultado = dict(enumerate(['LIMPO', 'CHUVA_FRACA', 'CHUVA_FORTE']))[pred]
        else:
            # Regras de limiar (fallback) baseadas na documentação
            if umid > 80 and temp < 25:
                resultado = 'CHUVA_FORTE'
            elif umid > 65:
                resultado = 'CHUVA_FRACA'
            else:
                resultado = 'LIMPO'
            prob = None

        classification = Classification.objects.create(
            user=log.user,
            sensor_log=log,
            resultado=resultado,
            probabilidade=prob
        )
        return classification