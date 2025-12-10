#!/bin/bash
# run_docker.sh - Script rápido para rodar MEGA LOG em Docker

set -e

COMMAND="${1:-help}"
CONTAINER_NAME="megalog-app"
IMAGE_NAME="megalog:v2.0"
VOLUME_HOT="${VOLUME_HOT:-./data/hot}"
VOLUME_COLD="${VOLUME_COLD:-./data/cold}"
VOLUME_LOGS="${VOLUME_LOGS:-./data/logs}"

# Criar diretórios
mkdir -p "${VOLUME_HOT}" "${VOLUME_COLD}" "${VOLUME_LOGS}"

case "$COMMAND" in
    build)
        echo "🔨 Building Docker image..."
        docker build -t ${IMAGE_NAME} -f Dockerfile .
        echo "✅ Build concluído: ${IMAGE_NAME}"
        ;;
    
    run)
        echo "🚀 Starting container..."
        docker run -d \
            --name ${CONTAINER_NAME} \
            -p 80:80 \
            -p 443:443 \
            -v "${VOLUME_HOT}":/dados1/system-log/hot \
            -v "${VOLUME_COLD}":/dados2/system-log/cold \
            -v "${VOLUME_LOGS}":/var/log/megalog \
            -e FLASK_ENV=production \
            -e PYTHONUNBUFFERED=1 \
            --restart unless-stopped \
            --health-interval=30s \
            --health-timeout=10s \
            --health-retries=3 \
            ${IMAGE_NAME}
        
        sleep 3
        echo "✅ Container iniciado"
        echo ""
        echo "🌐 Acesso: http://localhost/login"
        echo "👤 Usuário: superadmin"
        echo "🔑 Senha: admin123"
        ;;
    
    compose)
        echo "🐳 Starting with Docker Compose..."
        docker-compose up -d
        echo "✅ Compose iniciado"
        docker-compose ps
        ;;
    
    stop)
        echo "🛑 Stopping container..."
        docker stop ${CONTAINER_NAME}
        echo "✅ Container parado"
        ;;
    
    rm)
        echo "🗑️  Removing container..."
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
        docker rm ${CONTAINER_NAME} 2>/dev/null || true
        echo "✅ Container removido"
        ;;
    
    logs)
        echo "📋 Logs..."
        docker logs -f ${CONTAINER_NAME}
        ;;
    
    shell)
        echo "🔧 Abrindo shell..."
        docker exec -it ${CONTAINER_NAME} /bin/bash
        ;;
    
    health)
        echo "🏥 Health check..."
        docker exec ${CONTAINER_NAME} curl -s http://localhost/health | python3 -m json.tool
        ;;
    
    ps)
        echo "📊 Status..."
        docker ps -f name=${CONTAINER_NAME}
        echo ""
        docker stats ${CONTAINER_NAME} --no-stream
        ;;
    
    help|*)
        cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║              MEGA LOG V2.0 - Docker Control Script             ║
╚════════════════════════════════════════════════════════════════╝

Uso: ./run_docker.sh <comando>

Comandos:
  build       - Build da imagem Docker
  run         - Iniciar container (modo manual)
  compose     - Iniciar com docker-compose
  stop        - Parar container
  rm          - Remover container
  logs        - Ver logs em tempo real
  shell       - Abrir shell interativo
  health      - Verificar saúde da aplicação
  ps          - Ver status e recursos
  help        - Exibir esta mensagem

Exemplos:
  ./run_docker.sh build
  ./run_docker.sh run
  ./run_docker.sh logs
  ./run_docker.sh shell

Variáveis de ambiente:
  VOLUME_HOT   - Caminho para HOT storage (default: ./data/hot)
  VOLUME_COLD  - Caminho para COLD storage (default: ./data/cold)
  VOLUME_LOGS  - Caminho para logs (default: ./data/logs)

Exemplo customizado:
  VOLUME_HOT=/mnt/hot VOLUME_COLD=/mnt/cold ./run_docker.sh run

═════════════════════════════════════════════════════════════════

Acesso: http://localhost/login
User:   superadmin
Pass:   admin123

EOF
        ;;
esac
