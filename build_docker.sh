#!/bin/bash
# build_docker.sh - Script para build da imagem Docker

set -e

PROJECT_NAME="megalog"
VERSION="2.0"
REGISTRY="${REGISTRY:-docker.io}"  # Customizar se usar registry privado
IMAGE_NAME="${REGISTRY}/${PROJECT_NAME}:v${VERSION}"
IMAGE_PROCESSOR="${REGISTRY}/${PROJECT_NAME}-processor:v${VERSION}"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          Building Docker Image for MEGA LOG V2.0              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não instalado. Instale em: https://docs.docker.com/install/"
    exit 1
fi

echo "📦 Build Principal (Web + Nginx)..."
docker build -t ${IMAGE_NAME} \
    --file Dockerfile \
    --label "version=${VERSION}" \
    --label "maintainer=MEGA LOG Team" \
    .

if [ $? -eq 0 ]; then
    echo "✅ Build principal concluído: ${IMAGE_NAME}"
else
    echo "❌ Build principal falhou"
    exit 1
fi

echo ""
echo "📦 Build Processador..."
docker build -t ${IMAGE_PROCESSOR} \
    --file Dockerfile.processor \
    --label "version=${VERSION}" \
    --label "component=processor" \
    .

if [ $? -eq 0 ]; then
    echo "✅ Build processador concluído: ${IMAGE_PROCESSOR}"
else
    echo "❌ Build processador falhou"
    exit 1
fi

echo ""
echo "🏷️  Criando tags..."
docker tag ${IMAGE_NAME} ${PROJECT_NAME}:latest
docker tag ${IMAGE_PROCESSOR} ${PROJECT_NAME}-processor:latest

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ Build Concluído!                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Imagens criadas:"
echo "  - ${IMAGE_NAME}"
echo "  - ${IMAGE_PROCESSOR}"
echo ""
echo "Para iniciar com Docker Compose:"
echo "  docker-compose up -d"
echo ""
echo "Para iniciar manual:"
echo "  docker run -d -p 80:80 ${PROJECT_NAME}:v${VERSION}"
echo ""
