#!/bin/bash
# entrypoint.sh

set -e

echo "Aguardando MySQL em $DB_HOST:$DB_PORT..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
echo "MySQL pronto!"

# Aplica migrações (sem criar novas, apenas executa as pendentes)
echo "Aplicando migrações..."
python manage.py migrate --noinput

# Opcional: criar novas migrações se houver mudanças nos modelos (cuidado em produção)
# python manage.py makemigrations --noinput
# python manage.py migrate --noinput

# Cria o usuário "sistema" (representante do hardware) se não existir
echo "Criando usuário sistema (se não existir)..."
python manage.py shell <<EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='sistema').exists():
    User.objects.create_user(username='sistema', password='senha_padrao_troque_em_producao')
    print("Usuário 'sistema' criado com sucesso.")
else:
    print("Usuário 'sistema' já existe.")
EOF

# Inicia o cliente MQTT em background
echo "Iniciando cliente MQTT..."
python manage.py start_mqtt &
MQTT_PID=$!
echo "Cliente MQTT rodando (PID: $MQTT_PID)"

# Aguarda 2 segundos para garantir que o MQTT conectou
sleep 2

# Inicia o servidor Django (em foreground)
echo "Iniciando servidor Django..."
exec python manage.py runserver 0.0.0.0:8000