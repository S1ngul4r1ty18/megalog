#!/bin/bash
# check_megalog.sh
# Script de verificação e troubleshooting do MEGA LOG

echo "============================================================"
echo "  MEGA LOG V2.0 - Verificação de Sistema"
echo "============================================================"
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_ok() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# ==================== VERIFICAÇÕES ====================

echo "1. Verificando diretórios..."
echo ""

if [ -d "/dados1/system-log/hot" ]; then
    check_ok "Diretório HOT existe"
    ls -lh /dados1/system-log/hot/hot_logs.raw 2>/dev/null || check_warn "Arquivo hot_logs.raw não encontrado"
else
    check_fail "Diretório HOT não existe"
fi

if [ -d "/dados2/system-log/cold" ]; then
    check_ok "Diretório COLD existe"
    DB_COUNT=$(ls -1 /dados2/system-log/cold/*.db 2>/dev/null | wc -l)
    echo "   📂 Bancos de dados encontrados: $DB_COUNT"
else
    check_fail "Diretório COLD não existe"
fi

echo ""
echo "2. Verificando serviços systemd..."
echo ""

for service in megalog-receiver megalog-processor megalog-web; do
    if systemctl is-active --quiet $service; then
        check_ok "$service está rodando"
    else
        check_fail "$service NÃO está rodando"
        echo "   Tente: sudo systemctl start $service"
    fi
done

echo ""
echo "3. Verificando portas..."
echo ""

if netstat -tuln 2>/dev/null | grep -q ":514 "; then
    check_ok "Porta 514/UDP está aberta (Syslog)"
else
    check_warn "Porta 514/UDP não está escutando"
    echo "   Verifique: sudo systemctl status megalog-receiver"
fi

if netstat -tuln 2>/dev/null | grep -q ":5000 "; then
    check_ok "Porta 5000/TCP está aberta (Web)"
else
    check_warn "Porta 5000/TCP não está escutando"
    echo "   Verifique: sudo systemctl status megalog-web"
fi

echo ""
echo "4. Verificando logs do sistema..."
echo ""

if [ -f "/var/log/megalog/receiver.log" ]; then
    LAST_RECEIVER=$(tail -n 1 /var/log/megalog/receiver.log)
    echo "   📝 Último log do receptor:"
    echo "   $LAST_RECEIVER"
fi

if [ -f "/var/log/megalog/processor.log" ]; then
    LAST_PROCESSOR=$(tail -n 1 /var/log/megalog/processor.log)
    echo "   📝 Último log do processador:"
    echo "   $LAST_PROCESSOR"
fi

echo ""
echo "5. Estatísticas de logs..."
echo ""

if [ -f "/dados1/system-log/hot/hot_logs.raw" ]; then
    SIZE=$(du -h /dados1/system-log/hot/hot_logs.raw | cut -f1)
    LINES=$(wc -l < /dados1/system-log/hot/hot_logs.raw 2>/dev/null || echo 0)
    echo "   📊 Buffer HOT: $SIZE ($LINES linhas)"
fi

if [ -d "/dados2/system-log/cold" ]; then
    TOTAL_SIZE=$(du -sh /dados2/system-log/cold 2>/dev/null | cut -f1)
    echo "   📊 Armazenamento COLD: $TOTAL_SIZE"
fi

echo ""
echo "6. Testando conectividade..."
echo ""

# Testa se consegue enviar para a porta 514
if echo "test" | nc -u -w1 127.0.0.1 514 2>/dev/null; then
    check_ok "Porta 514/UDP está aceitando conexões"
else
    check_warn "Não foi possível testar porta 514/UDP"
    echo "   (nc pode não estar instalado)"
fi

echo ""
echo "7. Últimos erros nos logs..."
echo ""

if [ -f "/var/log/megalog/receiver-error.log" ]; then
    ERROR_COUNT=$(wc -l < /var/log/megalog/receiver-error.log 2>/dev/null || echo 0)
    if [ "$ERROR_COUNT" -gt 0 ]; then
        check_warn "Receptor tem $ERROR_COUNT linhas de erro"
        echo "   Últimas 3 linhas:"
        tail -n 3 /var/log/megalog/receiver-error.log | sed 's/^/   /'
    else
        check_ok "Receptor sem erros"
    fi
fi

if [ -f "/var/log/megalog/processor-error.log" ]; then
    ERROR_COUNT=$(wc -l < /var/log/megalog/processor-error.log 2>/dev/null || echo 0)
    if [ "$ERROR_COUNT" -gt 0 ]; then
        check_warn "Processador tem $ERROR_COUNT linhas de erro"
        echo "   Últimas 3 linhas:"
        tail -n 3 /var/log/megalog/processor-error.log | sed 's/^/   /'
    else
        check_ok "Processador sem erros"
    fi
fi

echo ""
echo "============================================================"
echo "  Comandos úteis:"
echo "============================================================"
echo ""
echo "Ver logs em tempo real:"
echo "  sudo journalctl -u megalog-receiver -f"
echo "  sudo journalctl -u megalog-processor -f"
echo "  tail -f /var/log/megalog/*.log"
echo ""
echo "Reiniciar serviços:"
echo "  sudo systemctl restart megalog-receiver"
echo "  sudo systemctl restart megalog-processor"
echo "  sudo systemctl restart megalog-web"
echo ""
echo "Testar geração de logs:"
echo "  cd /opt/megalog"
echo "  python3 log_generator.py --duration 30"
echo ""
echo "Ver tamanho dos bancos:"
echo "  du -sh /dados2/system-log/cold/*.db"
echo ""
echo "Contar logs em um banco:"
echo "  sqlite3 /dados2/system-log/cold/2024-12-10.db \"SELECT COUNT(*) FROM logs;\""
echo ""
echo "============================================================"
