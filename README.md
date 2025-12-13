# MEGA LOG V2.0 - Sistema Forense de Logs CGNAT

Sistema completo de coleta, processamento e análise forense de logs CGNAT do Mikrotik.

## 🎯 Características

- ✅ **Recepção em Tempo Real** - Receptor UDP syslog (porta 514)
- ✅ **Processamento em Stream** - Pygtail para leitura incremental sem perder logs
- ✅ **Armazenamento HOT/COLD** - Otimizado para alta performance
- ✅ **Normalização de Dados** - Compressão ~3x com dicionários
- ✅ **Busca Forense Avançada** - Busca por IP/Porta pública (ordens judiciais)
- ✅ **Interface Web Moderna** - Dashboard em tempo real
- ✅ **Auditoria Completa** - Log de todas as consultas forenses
- ✅ **Multi-usuário** - Sistema de autenticação com admin

## 📋 Requisitos

- **Sistema Operacional**: Debian 12/13, Ubuntu 20.04+ ou similar
- **Python**: 3.8+
- **RAM**: Mínimo 4GB (recomendado 8GB+)
- **Disco HOT (SSD)**: Mínimo 50GB para buffer
- **Disco COLD (HD)**: Conforme necessidade (1TB+ recomendado)
- **Rede**: Porta 514/UDP aberta para receber logs

## 🚀 Instalação Rápida

### Passo 1: Preparar o ambiente

```bash
# Como root ou com sudo
sudo su

# Atualizar sistema
apt update && apt upgrade -y

# Instalar dependências do sistema
apt install -y python3 python3-pip sqlite3 nginx

# Opcional: ferramentas de rede
apt install -y net-tools netcat-openbsd
```

### Passo 2: Baixar o projeto

```bash
cd /tmp
# Copie todos os arquivos do projeto para /tmp/megalog/
```

### Passo 3: Executar instalação

```bash
cd /tmp/megalog
chmod +x setup_megalog.sh
./setup_megalog.sh
```

O script irá:
1. Criar diretórios necessários
2. Instalar dependências Python
3. Copiar arquivos para `/opt/megalog`
4. Criar serviços systemd
5. Configurar Nginx (se instalado)
6. Inicializar banco de dados
7. Iniciar todos os serviços

### Passo 4: Verificar instalação

```bash
# Rodar script de verificação
chmod +x /opt/megalog/check_megalog.sh
/opt/megalog/check_megalog.sh
```

## 🔧 Configuração do Mikrotik

### Configurar envio de logs para o servidor

```routeros
# Substitua SEU_IP_SERVIDOR pelo IP do servidor MEGA LOG

# 1. Criar ação de logging remoto
/system logging action
add name=megalog-remote remote=SEU_IP_SERVIDOR remote-port=514 target=remote

# 2. Adicionar regra de firewall logging
/system logging
add action=megalog-remote topics=firewall,info

# 3. Verificar se está funcionando
/log print where topics~"firewall"
```

### Verificar conectividade

```routeros
# Testar conectividade com o servidor
/tool traceroute SEU_IP_SERVIDOR
/ping SEU_IP_SERVIDOR count=10

# Ver logs que estão sendo enviados
/log print follow where topics~"firewall"
```

## 🧪 Testando o Sistema

### Teste 1: Gerar logs de teste

```bash
cd /opt/megalog
python3 log_generator.py --duration 60 --rate 100
```

Isso irá gerar 100 logs/segundo por 60 segundos (total: 6000 logs).

### Teste 2: Verificar recepção

```bash
# Ver logs sendo recebidos
tail -f /var/log/megalog/receiver.log

# Ver buffer HOT crescendo
watch -n 1 'du -h /dados1/system-log/hot/hot_logs.raw'
```

### Teste 3: Verificar processamento

```bash
# Ver logs sendo processados
tail -f /var/log/megalog/processor.log

# Contar registros no banco de hoje
TODAY=$(date +%Y-%m-%d)
sqlite3 /dados2/system-log/cold/${TODAY}.db "SELECT COUNT(*) FROM logs;"
```

### Teste 4: Acessar interface web

```
http://seu-servidor/
```

**Login padrão:**
- Usuário: `superadmin`
- Senha: `admin123`

⚠️ **MUDE A SENHA IMEDIATAMENTE!**

## 📊 Monitoramento

### Ver status dos serviços

```bash
systemctl status megalog-receiver
systemctl status megalog-processor
systemctl status megalog-web
```

### Ver logs em tempo real

```bash
# Receptor
journalctl -u megalog-receiver -f

# Processador
journalctl -u megalog-processor -f

# Web
journalctl -u megalog-web -f
```

### Estatísticas

```bash
# Tamanho do buffer HOT
du -h /dados1/system-log/hot/hot_logs.raw

# Tamanho total do COLD
du -sh /dados2/system-log/cold/

# Listar bancos de dados
ls -lh /dados2/system-log/cold/*.db

# Contar logs em um banco específico
sqlite3 /dados2/system-log/cold/2024-12-10.db "SELECT COUNT(*) FROM logs;"
```

## 🔍 Busca Forense

### Via Interface Web

1. Acesse: `http://seu-servidor/search`
2. Informe o período (data/hora início e fim)
3. Informe o **IP Público (NAT)** e **Porta Pública** da ordem judicial
4. Clique em "Buscar"
5. Exporte os resultados em CSV

### Via SQL Direto (Avançado)

```bash
sqlite3 /dados2/system-log/cold/2024-12-10.db << EOF
SELECT 
    datetime(timestamp, 'unixepoch', 'localtime') as data_hora,
    nat_ip_pub,
    nat_port_pub,
    src_ip_priv,
    src_port_priv,
    dst_ip,
    dst_port
FROM logs
WHERE nat_ip_pub = '<IP_PUBLICO_INT>' 
  AND nat_port_pub = <PORTA>
ORDER BY timestamp DESC
LIMIT 100;
EOF
```

## 🛠️ Troubleshooting

### Logs não estão chegando

```bash
# 1. Verificar se porta 514 está aberta
netstat -tuln | grep 514

# 2. Verificar firewall
ufw status
firewall-cmd --list-ports

# 3. Testar recepção local
echo "test log" | nc -u 127.0.0.1 514

# 4. Ver logs do receptor
tail -f /var/log/megalog/receiver.log
tail -f /var/log/megalog/receiver-error.log
```

### Logs não estão sendo processados

```bash
# 1. Verificar se buffer HOT está crescendo
ls -lh /dados1/system-log/hot/hot_logs.raw

# 2. Ver logs do processador
tail -f /var/log/megalog/processor.log
tail -f /var/log/megalog/processor-error.log

# 3. Verificar banco de dados do dia
TODAY=$(date +%Y-%m-%d)
ls -lh /dados2/system-log/cold/${TODAY}.db
```

### Interface web não responde

```bash
# 1. Verificar se serviço está rodando
systemctl status megalog-web

# 2. Ver logs
tail -f /var/log/megalog/web.log
tail -f /var/log/megalog/web-error.log

# 3. Reiniciar serviço
systemctl restart megalog-web
```

### Erros de permissão

```bash
# Reajustar permissões
chown -R root:root /opt/megalog
chown -R root:root /dados1/system-log
chown -R root:root /dados2/system-log
chmod -R 755 /opt/megalog
```

## 📁 Estrutura de Arquivos

```
/opt/megalog/                 # Aplicação
├── app/                      # Módulo principal
│   ├── __init__.py
│   ├── config.py            # Configurações
│   ├── database.py          # Engine de BD
│   ├── models.py            # Modelos de dados
│   └── routes.py            # Rotas web
├── templates/               # Templates HTML
├── run.py                   # Servidor web
├── log_receiver.py          # Receptor de logs
├── processor_service.py     # Processador
├── log_generator.py         # Gerador de teste
└── gunicorn_config.py       # Config Gunicorn

/dados1/system-log/hot/      # Buffer HOT (SSD)
└── hot_logs.raw            # Logs brutos

/dados2/system-log/cold/     # Storage COLD (HD)
├── 2024-12-01.db           # Banco do dia 01/12
├── 2024-12-02.db           # Banco do dia 02/12
└── ...

/var/log/megalog/            # Logs do sistema
├── receiver.log
├── receiver-error.log
├── processor.log
├── processor-error.log
├── web.log
└── web-error.log
```

## 🔒 Segurança

### Alterar senha padrão

1. Acesse: `http://seu-servidor/profile/change-password`
2. Senha antiga: `admin123`
3. Digite e confirme nova senha

### Criar usuários adicionais

1. Acesse: `http://seu-servidor/admin/users` (requer admin)
2. Preencha username e senha
3. Marque "Admin" se necessário
4. Clique em "Cadastrar"

### Configurar HTTPS (Nginx)

```bash
# Instalar Certbot
apt install -y certbot python3-certbot-nginx

# Obter certificado (substitua seu-dominio.com)
certbot --nginx -d seu-dominio.com

# Renovação automática já está configurada
```

## 📈 Performance

### Recomendações

- **SSD para /dados1** - Essencial para buffer HOT
- **HD para /dados2** - Armazenamento de longo prazo
- **RAM**: 1GB por 10.000 logs/segundo
- **CPU**: 2+ cores recomendado

### Ajustes de performance

Edite `/opt/megalog/app/config.py`:

```python
# Tamanho do lote de inserção
BATCH_SIZE = 1000  # Aumente para mais performance

# Timeout do lote
BATCH_TIMEOUT_SEC = 10  # Reduza para latência menor
```

## 📝 Logs de Auditoria

Todas as consultas forenses são registradas automaticamente:

```bash
# Via interface web
http://seu-servidor/admin/audit-log

# Via SQL
sqlite3 /opt/megalog/users.db "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 50;"
```

## 🔄 Backup e Restore

### Backup

```bash
# Backup dos bancos de dados COLD
tar -czf backup-megalog-$(date +%Y%m%d).tar.gz /dados2/system-log/cold/

# Backup do banco de usuários
cp /opt/megalog/users.db /backup/users-$(date +%Y%m%d).db
```

### Restore

```bash
# Restore dos bancos COLD
tar -xzf backup-megalog-20241210.tar.gz -C /

# Restore do banco de usuários
cp /backup/users-20241210.db /opt/megalog/users.db
systemctl restart megalog-web
```

## 📞 Suporte

Para problemas:
1. Execute `/opt/megalog/check_megalog.sh`
2. Verifique logs em `/var/log/megalog/`
3. Verifique `journalctl -u megalog-*`

## 📄 Licença

GNU General Public License v2.0

---

**MEGA LOG V2.0** - Sistema Forense de Logs CGNAT
