#!/bin/bash
# setup_megalog.sh
# Script de instalação e configuração completa do MEGA LOG V2.0

set -e  # Aborta em caso de erro

echo "============================================================"
echo "  MEGA LOG V2.0 - Script de Instalação Completa"
echo "============================================================"
echo ""

# ==================== VARIÁVEIS ====================
HOT_DIR="/dados1/system-log/hot"
COLD_DIR="/dados2/system-log/cold"
APP_DIR="/opt/megalog"
LOG_DIR="/var/log/megalog"
SYSTEMD_DIR="/etc/systemd/system"

# ==================== VERIFICAÇÕES ====================
echo "🔍 Verificando requisitos..."

# Root check
if [[ $EUID -ne 0 ]]; then
   echo "❌ Este script deve ser executado como root (sudo)"
   exit 1
fi

# Python check
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado"
    exit 1
fi

echo "✅ Verificações OK"
echo ""

# ==================== CRIAÇÃO DE DIRETÓRIOS ====================
echo "📁 Criando estrutura de diretórios..."

mkdir -p "$HOT_DIR"
mkdir -p "$COLD_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"

# Cria arquivo de buffer se não existir
touch "$HOT_DIR/hot_logs.raw"

echo "✅ Diretórios criados"
echo ""

# ==================== INSTALAÇÃO DE DEPENDÊNCIAS ====================
echo "📦 Instalando dependências Python..."

pip3 install --break-system-packages -q flask werkzeug pandas numpy psutil pygtail gunicorn

echo "✅ Dependências instaladas"
echo ""

# ==================== COPIA ARQUIVOS ====================
echo "📋 Copiando arquivos da aplicação..."

# Assume que os arquivos estão no diretório atual
if [ -d "app" ]; then
    cp -r app "$APP_DIR/"
    echo "  ✅ Módulo app copiado"
fi

if [ -f "run.py" ]; then
    cp run.py "$APP_DIR/"
    echo "  ✅ run.py copiado"
fi

if [ -f "log_receiver.py" ]; then
    cp log_receiver.py "$APP_DIR/"
    chmod +x "$APP_DIR/log_receiver.py"
    echo "  ✅ log_receiver.py copiado"
fi

if [ -f "processor_service.py" ]; then
    cp processor_service.py "$APP_DIR/"
    chmod +x "$APP_DIR/processor_service.py"
    echo "  ✅ processor_service.py copiado"
fi

if [ -f "log_generator.py" ]; then
    cp log_generator.py "$APP_DIR/"
    chmod +x "$APP_DIR/log_generator.py"
    echo "  ✅ log_generator.py copiado"
fi

if [ -f "gunicorn_config.py" ]; then
    cp gunicorn_config.py "$APP_DIR/"
    echo "  ✅ gunicorn_config.py copiado"
fi

echo "✅ Arquivos copiados"
echo ""

# ==================== SYSTEMD SERVICES ====================
echo "⚙️  Criando serviços systemd..."

# Serviço: Receptor de Logs
cat > "$SYSTEMD_DIR/megalog-receiver.service" << EOF
[Unit]
Description=MEGA LOG - Receptor de Logs (Syslog UDP)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/log_receiver.py
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/receiver.log
StandardError=append:$LOG_DIR/receiver-error.log

[Install]
WantedBy=multi-user.target
EOF
echo "  ✅ megalog-receiver.service criado"

# Serviço: Processador de Logs
cat > "$SYSTEMD_DIR/megalog-processor.service" << EOF
[Unit]
Description=MEGA LOG - Processador de Logs (Stream)
After=network.target megalog-receiver.service
Wants=megalog-receiver.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/processor_service.py
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/processor.log
StandardError=append:$LOG_DIR/processor-error.log

[Install]
WantedBy=multi-user.target
EOF
echo "  ✅ megalog-processor.service criado"

# Serviço: Interface Web
cat > "$SYSTEMD_DIR/megalog-web.service" << EOF
[Unit]
Description=MEGA LOG - Interface Web (Gunicorn)
After=network.target

[Service]
Type=notify
User=root
WorkingDirectory=$APP_DIR
Environment="PYTHONPATH=$APP_DIR"
ExecStart=/usr/local/bin/gunicorn -c $APP_DIR/gunicorn_config.py run:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/web.log
StandardError=append:$LOG_DIR/web-error.log

[Install]
WantedBy=multi-user.target
EOF
echo "  ✅ megalog-web.service criado"

echo "✅ Serviços systemd criados"
echo ""

# ==================== NGINX (OPCIONAL) ====================
echo "🌐 Configurando Nginx (se instalado)..."

if command -v nginx &> /dev/null; then
    cat > "/etc/nginx/sites-available/megalog" << EOF
server {
    listen 80;
    server_name _;  # Mude para seu domínio

    access_log $LOG_DIR/nginx-access.log;
    error_log $LOG_DIR/nginx-error.log;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }

    # Arquivos estáticos (se houver)
    location /static {
        alias $APP_DIR/static;
        expires 30d;
    }
}
EOF

    # Ativa site
    ln -sf /etc/nginx/sites-available/megalog /etc/nginx/sites-enabled/
    
    # Testa configuração
    nginx -t && systemctl reload nginx
    
    echo "  ✅ Nginx configurado"
else
    echo "  ℹ️  Nginx não instalado (opcional)"
fi

echo ""

# ==================== PERMISSÕES ====================
echo "🔒 Ajustando permissões..."

chown -R root:root "$APP_DIR"
chmod -R 755 "$APP_DIR"
chmod 644 "$APP_DIR/app"/*.py 2>/dev/null || true
chmod +x "$APP_DIR"/*.py 2>/dev/null || true

chown -R root:root "$HOT_DIR"
chown -R root:root "$COLD_DIR"
chmod 755 "$HOT_DIR"
chmod 755 "$COLD_DIR"
chmod 644 "$HOT_DIR/hot_logs.raw"

chown -R root:root "$LOG_DIR"
chmod 755 "$LOG_DIR"

echo "✅ Permissões ajustadas"
echo ""

# ==================== FIREWALL ====================
echo "🔥 Configurando firewall..."

# UFW
if command -v ufw &> /dev/null; then
    ufw allow 514/udp comment "MEGA LOG - Syslog" 2>/dev/null || true
    ufw allow 80/tcp comment "MEGA LOG - Web" 2>/dev/null || true
    echo "  ✅ UFW configurado"
fi

# Firewalld
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=514/udp 2>/dev/null || true
    firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
    echo "  ✅ Firewalld configurado"
fi

echo ""

# ==================== INICIALIZAÇÃO ====================
echo "🚀 Inicializando banco de dados..."

cd "$APP_DIR"
python3 -c "from app.database import initialize_databases; from app.models import ensure_admin_user; initialize_databases(); ensure_admin_user()"

echo "✅ Banco de dados inicializado"
echo ""

# ==================== SYSTEMD ====================
echo "📊 Habilitando e iniciando serviços..."

systemctl daemon-reload

# Habilita serviços
systemctl enable megalog-receiver.service
systemctl enable megalog-processor.service
systemctl enable megalog-web.service

# Inicia serviços
systemctl start megalog-receiver.service
sleep 2
systemctl start megalog-processor.service
sleep 2
systemctl start megalog-web.service

echo "✅ Serviços iniciados"
echo ""

# ==================== STATUS ====================
echo "📈 Status dos serviços:"
echo ""

systemctl status megalog-receiver.service --no-pager | head -n 5
echo "---"
systemctl status megalog-processor.service --no-pager | head -n 5
echo "---"
systemctl status megalog-web.service --no-pager | head -n 5

echo ""
echo "============================================================"
echo "  ✅ INSTALAÇÃO CONCLUÍDA!"
echo "============================================================"
echo ""
echo "📋 Próximos passos:"
echo ""
echo "1. Acesse a interface web:"
echo "   http://seu-servidor"
echo ""
echo "2. Login padrão:"
echo "   Usuário: superadmin"
echo "   Senha: admin123"
echo "   ⚠️  MUDE A SENHA IMEDIATAMENTE!"
echo ""
echo "3. Configure seu Mikrotik para enviar logs:"
echo "   /system logging action"
echo "   add name=cgnat-remote remote=SEU_IP_SERVIDOR remote-port=514 target=remote"
echo "   /system logging"
echo "   add action=cgnat-remote topics=firewall,info"
echo ""
echo "4. Teste o recebimento de logs:"
echo "   cd $APP_DIR"
echo "   python3 log_generator.py --duration 30"
echo ""
echo "5. Monitore os serviços:"
echo "   sudo systemctl status megalog-receiver"
echo "   sudo systemctl status megalog-processor"
echo "   sudo systemctl status megalog-web"
echo "   sudo journalctl -u megalog-receiver -f"
echo ""
echo "6. Logs do sistema:"
echo "   $LOG_DIR/"
echo ""
echo "============================================================"
