#!/bin/bash
# QUICK START GUIDE - MEGA LOG V2.0 Container

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     MEGA LOG V2.0 - Container Deployment Quick Start          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Detectar sistema operacional
OS_TYPE=$(uname -s)
DOCKER_VERSION=$(docker --version 2>/dev/null | awk '{print $3}' | cut -d',' -f1)
COMPOSE_VERSION=$(docker-compose --version 2>/dev/null | awk '{print $3}' | cut -d',' -f1)

echo "📋 System Information"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "OS:              $OS_TYPE"
echo "Docker:          ${DOCKER_VERSION:-❌ NOT INSTALLED}"
echo "Docker Compose:  ${COMPOSE_VERSION:-❌ NOT INSTALLED}"
echo ""

# Verificar dependências
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker não está instalado!"
    echo ""
    echo "Instale com:"
    if [[ "$OS_TYPE" == "Linux" ]]; then
        echo "  sudo apt-get update && sudo apt-get install -y docker.io docker-compose"
        echo "  sudo usermod -aG docker \$USER"
    elif [[ "$OS_TYPE" == "Darwin" ]]; then
        echo "  brew install docker docker-compose"
    fi
    echo ""
    exit 1
fi

echo "✅ Docker instalado"
echo ""

# Menu de opções
echo "🎯 Choose an option:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1) 🔨 Build Docker images"
echo "  2) 🐳 Run with Docker Compose (RECOMMENDED)"
echo "  3) 🏃 Run single container"
echo "  4) 📊 View Kubernetes manifesto"
echo "  5) 📦 Install Helm chart"
echo "  6) 📖 View documentation"
echo "  7) 🧹 Cleanup (stop and remove)"
echo "  0) ❌ Exit"
echo ""

read -p "Enter your choice (0-7): " choice

case $choice in
    1)
        echo ""
        echo "🔨 Building Docker images..."
        cd /opt/megalog
        bash build_docker.sh
        ;;
    
    2)
        echo ""
        echo "🐳 Starting with Docker Compose..."
        cd /opt/megalog
        
        # Criar diretórios
        mkdir -p data/{hot,cold,logs}
        
        echo "Creating volumes..."
        docker-compose up -d
        
        echo ""
        echo "✅ Containers started!"
        echo ""
        echo "📊 Status:"
        docker-compose ps
        
        echo ""
        echo "🌐 Access Points:"
        echo "   Login:  http://localhost/login"
        echo "   Health: http://localhost/health"
        echo ""
        echo "👤 Default Credentials:"
        echo "   User: superadmin"
        echo "   Pass: admin123"
        echo ""
        echo "📋 Useful commands:"
        echo "   docker-compose logs -f          # View logs"
        echo "   docker-compose ps               # Status"
        echo "   docker-compose down             # Stop all"
        ;;
    
    3)
        echo ""
        echo "🏃 Starting single container..."
        cd /opt/megalog
        ./run_docker.sh run
        ;;
    
    4)
        echo ""
        echo "📋 Kubernetes manifest:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "File: /opt/megalog/kubernetes-deployment.yaml"
        echo ""
        echo "Deploy with:"
        echo "  kubectl apply -f kubernetes-deployment.yaml"
        echo ""
        echo "Check status:"
        echo "  kubectl get pods"
        echo "  kubectl get svc"
        echo ""
        echo "View logs:"
        echo "  kubectl logs -f deployment/megalog-web"
        echo ""
        echo "Read full guide:"
        echo "  cat /opt/megalog/KUBERNETES.md"
        ;;
    
    5)
        echo ""
        echo "📦 Installing Helm chart..."
        echo ""
        
        # Verificar Helm
        if ! command -v helm &> /dev/null; then
            echo "⚠️  Helm não está instalado!"
            echo ""
            echo "Instale com:"
            echo "  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
            echo ""
            exit 1
        fi
        
        echo "Creating namespace..."
        kubectl create namespace megalog --dry-run=client -o yaml | kubectl apply -f -
        
        echo "Installing chart..."
        helm install megalog /opt/megalog/helm/megalog \
            -n megalog \
            --set replicaCount=2 \
            --set persistence.enabled=true
        
        echo ""
        echo "✅ Helm chart installed!"
        echo ""
        echo "Status:"
        helm list -n megalog
        
        echo ""
        echo "Useful commands:"
        echo "  helm status megalog -n megalog"
        echo "  helm upgrade megalog /opt/megalog/helm/megalog -n megalog"
        echo "  helm rollback megalog -n megalog"
        ;;
    
    6)
        echo ""
        echo "📖 Documentation Files:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "  📄 CONTAINERIZATION_SUMMARY.md  - This summary"
        echo "  🐳 DOCKER.md                    - Docker guide"
        echo "  ☸️  KUBERNETES.md               - Kubernetes guide"
        echo "  📦 HELM.md                      - Helm chart guide"
        echo "  📋 README_DEPLOYMENT.txt        - Deployment summary"
        echo "  ✅ DEPLOYMENT.md                - Detailed checklist"
        echo ""
        echo "Open with:"
        echo "  cat /opt/megalog/CONTAINERIZATION_SUMMARY.md"
        echo "  cat /opt/megalog/DOCKER.md"
        echo "  cat /opt/megalog/KUBERNETES.md"
        echo "  cat /opt/megalog/HELM.md"
        ;;
    
    7)
        echo ""
        echo "🧹 Cleaning up..."
        cd /opt/megalog
        docker-compose down
        docker volume prune -f
        echo "✅ Cleanup complete!"
        ;;
    
    0)
        echo "👋 Goodbye!"
        exit 0
        ;;
    
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📞 Need help? Read the docs or run:"
echo ""
echo "  ./quick-start.sh        # This script"
echo "  ./run_docker.sh help    # Docker helper"
echo "  bash build_docker.sh    # Build script"
echo ""
