# MEGA LOG V2.0 - Configuração Rsyslog

## 📍 Localização
```
/etc/rsyslog.d/50-megalog.conf
```

## ✅ Status Atual
- **Versão rsyslog:** 8.2504.0 (Debian 13)
- **Status:** ✅ ATIVO E FUNCIONANDO
- **Validação:** ✅ Sem erros

## 📝 Configuração Atual

### Templates (Formatos de Log)

#### 1. megalog_format (Principal)
```
Format: TIMESTAMP HOSTNAME TAG MESSAGE
Exemplo: 2024-12-09T21:24 system kernel Linux version 6.12.0
```

#### 2. kernel_format
```
Format: TIMESTAMP HOSTNAME [KERNEL] MESSAGE
Uso: Logs do kernel do sistema
```

#### 3. firewall_format
```
Format: TIMESTAMP HOSTNAME [FIREWALL] MESSAGE
Uso: Logs UFW, iptables, DROP, REJECT
```

#### 4. auth_format
```
Format: TIMESTAMP HOSTNAME [AUTH] TAG MESSAGE
Uso: SSH, sudo, autenticação
```

## 🎯 Regras de Captura

### Prioridade Alta (Captura específica)

| Origem | Regra | Destino | Template |
|--------|-------|---------|----------|
| **Kernel** | programname = "kernel" | hot_logs.raw | kernel_format |
| **Firewall** | msg contém UFW/DROP/ACCEPT | hot_logs.raw | firewall_format |
| **SSH** | programname = "sshd" | hot_logs.raw | auth_format |
| **Sudo** | programname = "sudo" | hot_logs.raw | auth_format |
| **Nginx** | programname = "nginx" | hot_logs.raw | megalog_format |
| **MEGA LOG** | programname contém gunicorn/python/megalog | hot_logs.raw | megalog_format |

### Por Severidade

| Nível | Severidade | Capturado |
|-------|-----------|----------|
| **Erro** | .err | ✅ Sim |
| **Crítico** | .crit | ✅ Sim |
| **Alerta** | .alert | ✅ Sim |
| **Emergência** | .emerg | ✅ Sim |
| **Aviso** | .warn | ✅ Sim |
| **Informação** | .info | ❌ Não (comentado) |

## 💾 Destino de Logs

```
Arquivo: /dados1/system-log/hot/hot_logs.raw
Permissões: 0644 (rw-r--r--)
Proprietário: root:root
```

## ⚙️ Configurações de Performance

| Parâmetro | Valor | Propósito |
|-----------|-------|----------|
| ActionQueueType | LinkedList | Buffer em memória |
| ActionQueueMaxDiskSpace | 1G | Limite de espaço em disco |
| ActionQueueSize | 100000 | Tamanho máximo do buffer |
| FileCreateMode | 0644 | Permissões do arquivo |

## 🔍 Verificação de Status

### Ver se rsyslog está rodando
```bash
sudo systemctl status rsyslog
```

### Validar configuração
```bash
sudo rsyslogd -N 1
```

### Ver erros/warnings
```bash
sudo journalctl -u rsyslog -f
```

### Testar envio de logs
```bash
logger "TEST MESSAGE FROM MEGA LOG"
cat /dados1/system-log/hot/hot_logs.raw | tail -5
```

## 📊 Exemplo de Log Capturado

```
2024-12-09T21:24 system sshd[1234] Invalid user admin from 192.168.1.100 port 54321
2024-12-09T21:25 system sudo: root : TTY=pts/0 ; PWD=/root ; USER=root ; COMMAND=/bin/systemctl restart rsyslog
2024-12-09T21:26 system nginx: 192.168.1.50 - - [09/Dec/2024:21:26:00 -0300] "GET /health HTTP/1.1" 200 45
2024-12-09T21:27 system [FIREWALL] [UFW BLOCK] IN=eth0 OUT= MAC=... SRC=203.0.113.50 DST=192.168.1.1
2024-12-09T21:28 system [KERNEL] audit: type=1400 audit(1733858880.123:456): apparmor="DENIED"
```

## 🔄 Fluxo de Log

```
Sistema (kernel, sshd, nginx, etc)
    ↓
rsyslog lê via /dev/log (ou /run/systemd/journal/syslog)
    ↓
Aplica regras (programname, msg, severity)
    ↓
Seleciona template apropriado
    ↓
Escreve em /dados1/system-log/hot/hot_logs.raw
    ↓
Processor (pygtail) lê cada 10 segundos
    ↓
Normaliza e insere em SQLite em /dados2/system-log/cold/
```

## ⚠️ Warnings Esperados

Durante o restart do rsyslog, você pode ver:
```
warning: ~ action is deprecated, consider using the 'stop' statement
```

Isso é normal em rsyslog 8.25+. A sintaxe `~` é legada mas ainda funciona.

## 🔧 Modificar Configuração

### Adicionar nova regra
Edite `/etc/rsyslog.d/50-megalog.conf`:
```
:programname, isequal, "seu-aplicativo" ~
/dados1/system-log/hot/hot_logs.raw;megalog_format
```

### Alterar formato de log
Modifique os templates:
```
template(name="megalog_format" type="string" 
    string="%timegenerated:1:19% %HOSTNAME% %syslogtag%%msg%\n")
```

### Validar mudanças
```bash
sudo rsyslogd -N 1
```

### Aplicar mudanças
```bash
sudo systemctl restart rsyslog
```

## 📚 Propriedades Disponíveis

| Propriedade | Descrição | Exemplo |
|-----------|-----------|---------|
| `%timegenerated%` | Timestamp | 2024-12-09T21:24:05 |
| `%HOSTNAME%` | Nome do host | system |
| `%syslogtag%` | Tag do programa | sshd[1234] |
| `%msg%` | Mensagem | Invalid user admin |
| `%programname%` | Nome do programa | sshd |
| `%pri%` | Priority (facility+severity) | 34 |

## 🔐 Permissões

```bash
# Verificar permissões do arquivo de log
ls -la /dados1/system-log/hot/hot_logs.raw

# Se forem incorretas, corrigir:
sudo chown root:root /dados1/system-log/hot/hot_logs.raw
sudo chmod 0644 /dados1/system-log/hot/hot_logs.raw
```

## 📈 Monitoramento

### Ver quantidade de logs por hora
```bash
grep -c "^" /dados1/system-log/hot/hot_logs.raw
```

### Ver logs de um programa específico
```bash
grep "sshd" /dados1/system-log/hot/hot_logs.raw
```

### Ver logs de um nível de severidade
```bash
grep "err\|crit\|alert\|emerg" /dados1/system-log/hot/hot_logs.raw
```

## 🐛 Troubleshooting

### Rsyslog não inicia
```bash
sudo rsyslogd -N 1        # Ver erro exato
sudo systemctl restart rsyslog
```

### Arquivo hot_logs.raw não é criado
```bash
# Verificar se o diretório existe
ls -la /dados1/system-log/hot/

# Se não, criar:
sudo mkdir -p /dados1/system-log/hot
sudo chmod 755 /dados1/system-log/hot

# Reiniciar rsyslog
sudo systemctl restart rsyslog
```

### Nenhum log sendo capturado
```bash
# Testar manualmente
logger "TEST MESSAGE"

# Ver logs rsyslog
sudo journalctl -u rsyslog -n 50

# Verificar arquivo de log
tail -20 /dados1/system-log/hot/hot_logs.raw
```

### Permissão negada no arquivo
```bash
# Corrigir proprietário
sudo chown root:root /dados1/system-log/hot/hot_logs.raw

# Corrigir permissões
sudo chmod 644 /dados1/system-log/hot/hot_logs.raw

# Reiniciar rsyslog
sudo systemctl restart rsyslog
```

## 📝 Log Completo da Configuração

Ver arquivo em `/etc/rsyslog.d/50-megalog.conf`

## ✅ Checklist Final

- [x] Rsyslog 8.2504.0 instalado
- [x] Configuração sem erros de sintaxe
- [x] Rsyslog está ativo e rodando
- [x] Diretórios /dados1/system-log/hot criados
- [x] Templates configurados
- [x] Regras de captura ativas
- [x] Buffer de performance configurado
- [x] Permissões corretas definidas

## 📞 Próximos Passos

1. Verificar se logs estão sendo capturados:
   ```bash
   tail -f /dados1/system-log/hot/hot_logs.raw
   ```

2. Testar processor MEGA LOG:
   ```bash
   docker logs megalog-processor
   ```

3. Verificar no dashboard:
   ```
   http://localhost/search
   ```

4. Se necessário, ajustar regras em:
   ```
   /etc/rsyslog.d/50-megalog.conf
   ```

---

**Data de criação:** Dezembro 2024  
**Versão rsyslog:** 8.2504.0  
**Debian:** 13  
**Status:** ✅ Operacional
