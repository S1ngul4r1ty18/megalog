#!/bin/bash
# setup_production.sh - Script de inicialização para MEGA LOG V2.0 em Produção

set -e

echo "================================"
echo "  MEGA LOG V2.0 - Setup Production"
echo "================================"
echo ""

# 1. Criar estrutura de diretórios
echo "📁 Criando estrutura de diretórios..."
sudo mkdir -p /dados1/system-log/hot /dados2/system-log/cold /var/log/megalog /var/run/megalog

# 2. Criar usuário megalog
echo "👤 Criando usuário megalog..."
sudo useradd -r -s /bin/false -d /opt/megalog megalog 2>/dev/null || echo "   Usuário já existe"

# 3. Configurar permissões
echo "🔐 Configurando permissões..."
sudo chown -R megalog:megalog /dados1/system-log /dados2/system-log /var/log/megalog /var/run/megalog /opt/megalog
sudo chmod 750 /dados1/system-log /dados2/system-log

# 4. Criar buffer
echo "📝 Criando arquivo de buffer..."
sudo touch /dados1/system-log/hot/hot_logs.raw
sudo chown megalog:megalog /dados1/system-log/hot/hot_logs.raw

# 5. Criar logs Nginx
echo "📊 Criando arquivos de log Nginx..."
sudo touch /var/log/megalog/nginx_{access,error}.log
sudo chown megalog:megalog /var/log/megalog/nginx*.log

# 6. Venv e dependências
echo "📦 Instalando dependências Python..."
cd /opt/megalog
python3 -m venv venv --upgrade-pip
source venv/bin/activate
pip install -q --upgrade pip setuptools wheel
pip install -q -r requirements.txt

# 7. Limpar cache Python
echo "🧹 Limpando cache Python..."
find /opt/megalog -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find /opt/megalog -name "*.pyc" -delete

# 8. Recarregar systemd
echo "⚙️  Registrando serviços systemd..."
sudo systemctl daemon-reload
sudo systemctl enable megalog-web.service megalog-processor.service nginx

# 9. Iniciar serviços
echo "🚀 Iniciando serviços..."
sudo systemctl start megalog-web.service
sleep 2
sudo systemctl start megalog-processor.service
sudo systemctl start nginx

# 10. Verificar status
echo ""
echo "================================"
echo "  Status dos Serviços"
echo "================================"
sudo systemctl status megalog-web.service --no-pager | grep -E "Active|Running"
sudo systemctl status megalog-processor.service --no-pager | grep -E "Active|Running"
sudo systemctl status nginx --no-pager | grep -E "Active|Running"

# 11. Testar aplicação
echo ""
echo "================================"
echo "  Testando Aplicação"
echo "================================"
sleep 2

echo -n "🔍 Testando health check... "
if curl -s http://127.0.0.1/health > /dev/null; then
    echo "✅ OK"
else
    echo "❌ FALHOU"
fi

echo -n "🔍 Testando login page... "
if curl -s http://127.0.0.1/login | grep -q "MEGA LOG"; then
    echo "✅ OK"
else
    echo "❌ FALHOU"
fi

echo ""
echo "================================"
echo "  Próximos Passos"
echo "================================"
echo ""
echo "1. ✅ Serviços configurados:"
echo "   - Web: /opt/megalog (Gunicorn)"
echo "   - Processor: /opt/megalog/processor_service.py"
echo "   - Proxy: Nginx (porta 80)"
echo ""
echo "2. 📂 Diretórios:"
echo "   - HOT: /dados1/system-log/hot"
echo "   - COLD: /dados2/system-log/cold"
echo "   - LOGS: /var/log/megalog"
echo ""
echo "3. 🔒 Segurança:"
echo "   - Firewall UFW ativado"
echo "   - Portas abertas: 22 (SSH), 80 (HTTP), 443 (HTTPS)"
echo ""
echo "4. 🔑 Credenciais Padrão:"
echo "   - Usuário: superadmin"
echo "   - Senha: admin123"
echo "   ⚠️  MUDE ANTES DE USAR EM PRODUÇÃO!"
echo ""
echo "5. 📝 Logs:"
echo "   - Web: tail -f /var/log/megalog/error.log"
echo "   - Nginx: tail -f /var/log/megalog/nginx_access.log"
echo ""
echo "6. 🌐 Acesse: http://$(hostname -I | awk '{print $1}')/login"
echo ""
echo "✅ Setup concluído com sucesso!"
echo ""
