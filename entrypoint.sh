#!/bin/bash
# Entrypoint script para container Docker

set -e

export APP_HOME="/opt/megalog"
export VENV="${APP_HOME}/venv"

# Função para aguardar saúde
wait_for_health() {
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf http://127.0.0.1/health > /dev/null 2>&1; then
            echo "✅ Aplicação saudável"
            return 0
        fi
        echo "⏳ Aguardando saúde da aplicação ($attempt/$max_attempts)..."
        sleep 1
        ((attempt++))
    done
    
    echo "❌ Timeout aguardando saúde da aplicação"
    return 1
}

case "$1" in
    start)
        echo "🚀 Iniciando MEGA LOG V2.0..."
        
        # Ativar venv
        source ${VENV}/bin/activate
        
        # Limpar cache Python
        find ${APP_HOME} -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
        find ${APP_HOME} -name "*.pyc" -delete
        
        # Inicializar banco de dados
        echo "🔧 Inicializando bancos de dados..."
        python3 << 'PYEOF'
import sys
sys.path.insert(0, '/opt/megalog')
from app import database, config

database.initialize_databases()
print("✅ Bancos de dados inicializados")
PYEOF
        
        # Iniciar Nginx em background
        echo "🌐 Iniciando Nginx..."
        nginx
        sleep 1
        
        # Iniciar Gunicorn
        echo "🔧 Iniciando Gunicorn..."
        exec ${VENV}/bin/gunicorn \
            --config ${APP_HOME}/gunicorn_config.py \
            --bind 127.0.0.1:5000 \
            --user megalog \
            --group megalog \
            wsgi:app &
        
        GUNICORN_PID=$!
        
        sleep 2
        
        # Iniciar Processor em background
        echo "⚙️  Iniciando Processor..."
        su - megalog -s /bin/bash -c "source ${VENV}/bin/activate && python3 ${APP_HOME}/processor_service.py" &
        PROCESSOR_PID=$!
        
        # Aguardar saúde
        wait_for_health
        
        echo "✅ MEGA LOG V2.0 iniciado com sucesso"
        echo ""
        echo "URL:      http://localhost/login"
        echo "Usuário:  superadmin"
        echo "Senha:    admin123"
        echo ""
        
        # Aguardar sinais
        wait $GUNICORN_PID $PROCESSOR_PID
        ;;
        
    web)
        echo "🚀 Iniciando apenas Web Service..."
        source ${VENV}/bin/activate
        
        # Inicializar DB
        python3 << 'PYEOF'
import sys
sys.path.insert(0, '/opt/megalog')
from app import database
database.initialize_databases()
PYEOF
        
        exec ${VENV}/bin/gunicorn \
            --config ${APP_HOME}/gunicorn_config.py \
            --bind 0.0.0.0:5000 \
            wsgi:app
        ;;
        
    processor)
        echo "🚀 Iniciando apenas Processor..."
        source ${VENV}/bin/activate
        exec python3 ${APP_HOME}/processor_service.py
        ;;
        
    shell)
        echo "🔧 Abrindo shell interativo..."
        source ${VENV}/bin/activate
        exec /bin/bash
        ;;
        
    *)
        echo "Uso: $0 {start|web|processor|shell}"
        exit 1
        ;;
esac
