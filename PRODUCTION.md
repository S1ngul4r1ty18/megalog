# MEGA LOG V2.0 - Guia de Produção

## 🎯 Visão Geral

Sistema forense de logs CGNAT em tempo real com:
- **Web Interface**: Dashboard + Busca Forense Avançada
- **Stream Processor**: Processamento 24/7 de logs em lote
- **SQLite Otimizado**: Um banco por dia, normalizado, comprimido
- **Gunicorn + Nginx**: Stack production-ready

## ✅ Status Atual

```
✅ Web Service (Gunicorn)      - RODANDO
✅ Processor Service 24/7      - RODANDO
✅ Nginx Reverse Proxy         - RODANDO
✅ Firewall UFW                - ATIVO
```

## 📂 Estrutura de Produção

```
/opt/megalog/                    # Código da aplicação
├── app/
│   ├── __init__.py
│   ├── config.py              # Configurações centralizadas
│   ├── database.py            # Engine SQLite
│   ├── models.py              # Modelos User, AuditLog, LogSearch
│   ├── routes.py              # Rotas Flask
│   └── users.db               # Banco de usuários (único)
├── venv/                       # Ambiente virtual Python 3.13
├── templates/                  # Templates Jinja2 + Tailwind
├── run.py                      # App factory Flask
├── wsgi.py                     # Entry point Gunicorn
├── processor_service.py        # Processador de logs 24/7
├── gunicorn_config.py         # Config Gunicorn (prod)
├── requirements.txt            # Dependências Python
└── setup_production.sh         # Script de setup

/dados1/system-log/hot/        # Storage HOT (SSD)
└── hot_logs.raw               # Buffer de entrada (tail -f)

/dados2/system-log/cold/       # Storage COLD (HD)
├── 2025-12-09.db              # Logs processados (1 por dia)
├── 2025-12-10.db
└── .processor.offset           # Offset do Pygtail

/var/log/megalog/              # Logs do sistema
├── error.log                  # Erros Gunicorn
├── access.log                 # Access Gunicorn
├── nginx_error.log            # Erros Nginx
└── nginx_access.log           # Access Nginx

/etc/systemd/system/
├── megalog-web.service        # Serviço web Gunicorn
└── megalog-processor.service  # Processador 24/7

/etc/nginx/sites-available/megalog  # Config Nginx
```

## 🚀 Serviços Systemd

### Web Service
```bash
sudo systemctl start megalog-web.service
sudo systemctl status megalog-web.service
sudo systemctl restart megalog-web.service
sudo journalctl -u megalog-web.service -f
```

### Processor Service
```bash
sudo systemctl start megalog-processor.service
sudo systemctl status megalog-processor.service
sudo journalctl -u megalog-processor.service -f
```

### Nginx
```bash
sudo systemctl start nginx
sudo nginx -t  # Validar config
```

## 🔑 Autenticação Padrão

```
Usuário: superadmin
Senha:   admin123
```

⚠️ **ALTERE IMEDIATAMENTE EM PRODUÇÃO!**

### Alterar Senha Admin
1. Faça login com `superadmin / admin123`
2. Vá em "Alterar Senha" no menu
3. Defina uma senha segura

### Criar Novos Usuários
1. Vá em "Administração → Gerenciar Usuários"
2. Preencha os campos e clique "Cadastrar"

## 🌐 Acessando a Aplicação

```
http://seu_ip_ou_dominio/login
```

Porta: 80 (HTTP via Nginx)  
Backend: 127.0.0.1:5000 (Gunicorn)

## 📝 Logs

### Logs da Aplicação
```bash
# Web
tail -f /var/log/megalog/error.log

# Processor
sudo journalctl -u megalog-processor.service -f

# Nginx
tail -f /var/log/megalog/nginx_access.log
tail -f /var/log/megalog/nginx_error.log
```

## 🔧 Configurações Importantes

### Environment Variables
```bash
# Definir secret key produção (IMPORTANTE!)
export FLASK_SECRET_KEY="sua_chave_aleatoria_muito_segura_aqui"

# Executar processor
FLASK_SECRET_KEY="..." python3 processor_service.py
```

### Config.py - /opt/megalog/app/config.py
```python
# Storage
HOT_STORAGE_DIR = "/dados1/system-log/hot"   # SSD (buffer)
COLD_STORAGE_DIR = "/dados2/system-log/cold" # HD (permanente)

# Performance
BATCH_SIZE = 500                  # Logs por lote
BATCH_TIMEOUT_SEC = 10            # Timeout do lote
DB_JOURNAL_MODE = "WAL"          # Write-Ahead Logging
DB_SYNCHRONOUS = "NORMAL"        # Menos sync = mais rápido

# Retenção
LOG_RETENTION_DAYS = 365         # Deletar logs antigos

# Segurança
ENABLE_AUDIT_LOG = True          # Auditar consultas
```

## 📊 Monitoramento

### Health Check
```bash
curl http://localhost/health | python3 -m json.tool
```

Response esperado:
```json
{
  "status": "healthy",
  "version": "V2.0-STREAM",
  "checks": {
    "users_db": true,
    "logs_db": true,
    "buffer": true
  }
}
```

### Recursos do Sistema
```bash
# CPU, RAM, Disco
free -h
df -h /dados1 /dados2
ps aux | grep -E "gunicorn|processor"

# Conexões Nginx
netstat -an | grep :80 | wc -l
```

## 🔐 Segurança

### Firewall
```bash
sudo ufw status
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
```

### Logs de Auditoria
Todas as consultas forenses são registradas em:
- **DB**: `/opt/megalog/app/users.db` → tabela `audit_log`
- **Interface**: Menu "Administração → Log de Auditoria"

### SSL/TLS (HTTPS)
Para adicionar certificado Let's Encrypt:
```bash
sudo certbot --nginx -d seu_dominio.com
sudo systemctl reload nginx
```

## 🐛 Troubleshooting

### Web Service não inicia
```bash
sudo journalctl -xeu megalog-web.service --no-pager
tail -50 /var/log/megalog/error.log
```

### Processor saindo
```bash
sudo journalctl -u megalog-processor.service -n 100
```

### Nginx retorna 502 Bad Gateway
```bash
# Verificar se Gunicorn está rodando
curl http://127.0.0.1:5000/health

# Restar tudo
sudo systemctl restart megalog-web.service nginx
```

### Disco cheio
```bash
# Ver tamanho DBs
du -sh /dados2/system-log/cold/

# Implementar retenção (config.py)
LOG_RETENTION_DAYS = 90  # Deletar logs > 90 dias
```

## 📈 Performance Tuning

### Aumentar Workers Gunicorn
`/opt/megalog/gunicorn_config.py`:
```python
workers = multiprocessing.cpu_count() * 2 + 1  # Aumentar se necessário
```

### Aumentar Buffer SQLite
```python
conn.execute("PRAGMA cache_size = -64000;")  # 64MB, aumentar se necessário
```

### Otimizar Batch Size
```python
BATCH_SIZE = 1000  # Aumentar para mais linhas/lote
```

## 🔄 Backup e Recuperação

### Backup Manual
```bash
# Banco de usuários
sudo cp /opt/megalog/app/users.db /backup/users.db.$(date +%Y%m%d)

# Dados de logs
sudo tar -czf /backup/logs_$(date +%Y%m%d).tar.gz /dados2/system-log/cold/
```

### Restaurar Banco de Usuários
```bash
sudo cp /backup/users.db.20251209 /opt/megalog/app/users.db
sudo chown megalog:megalog /opt/megalog/app/users.db
sudo systemctl restart megalog-web.service
```

## 📞 Suporte

**Logs Location**: `/var/log/megalog/`  
**Config**: `/opt/megalog/app/config.py`  
**Systemd Status**: `sudo systemctl status megalog-*`

---

**Versão**: V2.0-STREAM  
**Data Setup**: 9 de Dezembro de 2025  
**Python**: 3.13  
**Stack**: Flask + Gunicorn + Nginx + SQLite
