# 🚀 MEGA LOG V2.0 - PRODUÇÃO EM DEBIAN 13 - CHECKLIST

## ✅ Instalação Concluída (9 de Dezembro de 2025)

### 1️⃣ INFRAESTRUTURA
- ✅ Debian 13 limpo
- ✅ Python 3.13 com venv
- ✅ Dependências do sistema instaladas
- ✅ Estrutura de diretórios criada

### 2️⃣ APLICAÇÃO
- ✅ Flask + Gunicorn em `/opt/megalog`
- ✅ Processador 24/7 funcionando
- ✅ Banco de dados SQLite otimizado
- ✅ Autenticação com senhas hasheadas

### 3️⃣ SERVIÇOS SYSTEMD
- ✅ `megalog-web.service` - Web (Gunicorn)
- ✅ `megalog-processor.service` - Processor (24/7)
- ✅ `nginx` - Reverse proxy

### 4️⃣ ARMAZENAMENTO
- ✅ `/dados1/system-log/hot/` - Buffer HOT (SSD)
- ✅ `/dados2/system-log/cold/` - Dados COLD (HD)
- ✅ `/var/log/megalog/` - Logs do sistema

### 5️⃣ SEGURANÇA
- ✅ Firewall UFW ativo
- ✅ Portas: SSH(22), HTTP(80), HTTPS(443)
- ✅ Auditoria de consultas ativada
- ✅ Usuário megalog com permissões restritas

---

## 🎯 STATUS ATUAL

```
WEB SERVICE:          ✅ active (running)
PROCESSOR:            ✅ active (running)
NGINX:                ✅ active (running)
FIREWALL:             ✅ active
```

---

## 🔐 CREDENCIAIS PADRÃO

| Campo | Valor |
|-------|-------|
| Usuário | `superadmin` |
| Senha | `admin123` |
| ⚠️ Status | **MUDE IMEDIATAMENTE EM PRODUÇÃO** |

---

## 🌐 ACESSO

**URL Principal**: `http://seu_servidor/login`

**Endereços Internos**:
- Web Backend: `http://127.0.0.1:5000`
- Nginx: `http://127.0.0.1:80`

---

## 📊 ARQUIVOS IMPORTANTES

| Arquivo | Descrição |
|---------|-----------|
| `/opt/megalog/app/config.py` | Configurações centralizadas |
| `/opt/megalog/gunicorn_config.py` | Config Gunicorn (workers, timeouts) |
| `/etc/nginx/sites-available/megalog` | Config Nginx proxy reverso |
| `/var/log/megalog/` | Logs da aplicação |
| `/opt/megalog/PRODUCTION.md` | Documentação completa |

---

## 🛠️ COMANDOS RÁPIDOS

### Verificar Status
```bash
sudo systemctl status megalog-web.service megalog-processor.service nginx
```

### Ver Logs
```bash
tail -f /var/log/megalog/error.log
sudo journalctl -u megalog-processor.service -f
tail -f /var/log/megalog/nginx_access.log
```

### Restart Serviços
```bash
sudo systemctl restart megalog-web.service
sudo systemctl restart megalog-processor.service
sudo systemctl reload nginx
```

### Teste de Saúde
```bash
curl http://127.0.0.1/health
```

---

## 📋 PRÓXIMOS PASSOS RECOMENDADOS

### Imediato (CRÍTICO)
1. [ ] ⚠️ **ALTERE A SENHA DO ADMIN**
   - Acesso: Menu → Alterar Senha
   - Nova senha: `definir_algo_seguro`

2. [ ] Verifique se logs estão entrando
   - Monitore: `/var/log/megalog/error.log`
   - Teste: `curl http://localhost/health`

### Segurança
3. [ ] Configure SSL/TLS com Let's Encrypt
   ```bash
   sudo certbot --nginx -d seu_dominio.com
   ```

4. [ ] Defina `FLASK_SECRET_KEY` em produção
   ```bash
   export FLASK_SECRET_KEY="sua_chave_aleatoria_muito_segura"
   ```

5. [ ] Faça backup do banco de usuários
   ```bash
   sudo cp /opt/megalog/app/users.db /backup/users.db.$(date +%Y%m%d)
   ```

### Operacional
6. [ ] Configure entrada de logs (rsyslog → hot_logs.raw)
7. [ ] Configure rotação de logs no logrotate
8. [ ] Monitore recursos (CPU, RAM, disco)
9. [ ] Implemente retenção de dados antigos

### Monitoramento
10. [ ] Configure alertas para disco cheio
11. [ ] Implemente backup automático
12. [ ] Monitore performance do Gunicorn

---

## 💾 DIRETÓRIOS CRÍTICOS

```
/opt/megalog/              ← Código-fonte e virtualenv
  ├── venv/                 ← Python 3.13 + packages
  ├── app/
  │   └── users.db          ← ⚠️ BACKUP IMPORTANTE!
  ├── processor_service.py  ← Processador 24/7
  ├── wsgi.py              ← Entry point Gunicorn
  └── requirements.txt      ← Dependências

/dados1/system-log/hot/    ← Buffer de entrada (SSD)
  └── hot_logs.raw         ← Arquivo de buffer

/dados2/system-log/cold/   ← Banco de dados (HD)
  ├── 2025-12-09.db        ← Um por dia
  ├── 2025-12-10.db
  └── .processor.offset     ← Offset Pygtail

/var/log/megalog/          ← Logs da aplicação
  ├── error.log
  ├── access.log
  ├── nginx_error.log
  └── nginx_access.log

/etc/systemd/system/       ← Serviços
  ├── megalog-web.service
  └── megalog-processor.service
```

---

## 🔧 PERFORMANCE TUNING

Se necessário ajustar para maior carga:

**Aumentar workers Gunicorn** (`gunicorn_config.py`):
```python
workers = 16  # ou: cpu_count() * 2 + 1
```

**Aumentar batch size** (`app/config.py`):
```python
BATCH_SIZE = 1000  # de 500 para 1000
BATCH_TIMEOUT_SEC = 5  # de 10 para 5
```

**Aumentar buffer SQLite** (`database.py`):
```python
conn.execute("PRAGMA cache_size = -128000;")  # de -64000 para -128000
```

---

## 📱 INTERFACE WEB FEATURES

- ✅ Dashboard com gráficos em tempo real
- ✅ Busca forense avançada (IP, porta, data)
- ✅ Visualização de logs diários
- ✅ Exportação em CSV
- ✅ Gerenciamento de usuários
- ✅ Log de auditoria
- ✅ Alteração de senha
- ✅ Health check endpoint

---

## 🆘 TROUBLESHOOTING RÁPIDO

### Gunicorn não inicia
```bash
sudo journalctl -xeu megalog-web.service --no-pager | tail -50
```

### Processor saiu com erro
```bash
sudo journalctl -u megalog-processor.service -n 100
```

### Nginx retorna 502
```bash
curl http://127.0.0.1:5000/health  # Verificar se Gunicorn está ok
sudo systemctl restart megalog-web.service nginx
```

### Disco cheio
```bash
du -sh /dados2/system-log/cold/  # Ver tamanho
# Implementar retenção ou deletar DBs antigos manualmente
```

---

## 📞 INFORMAÇÕES DO SISTEMA

| Item | Valor |
|------|-------|
| **OS** | Debian 13 |
| **Python** | 3.13 |
| **Web Framework** | Flask 3.0.0 |
| **Application Server** | Gunicorn 23.0.0 |
| **Reverse Proxy** | Nginx 1.26.3 |
| **Database** | SQLite3 |
| **Data Processor** | Python + Pygtail |
| **Deploy Date** | 9 de Dezembro de 2025 |

---

## 📖 DOCUMENTAÇÃO COMPLETA

Para informações detalhadas, consulte:
```bash
cat /opt/megalog/PRODUCTION.md
```

---

**Status**: 🟢 OPERACIONAL EM PRODUÇÃO  
**Última Atualização**: 9 de Dezembro de 2025  
**Próxima Review**: Conforme necessidade
