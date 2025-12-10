# Configuração Rsyslog Melhorada - Mikrotik e Dispositivos de Rede

## ✅ Configuração Atualizada

O arquivo `/etc/rsyslog.d/50-megalog.conf` foi melhorado para capturar:

### 🖥️ Dispositivos de Rede

#### Mikrotik (Roteadores)
```
Método 1 - IP específico:
if $fromhost-ip == '10.100.100.1' then {
    /dados1/system-log/hot/hot_logs.raw;mikrotik_format
    & stop
}

Método 2 - Por nome (hostname):
:hostname, regex, "^mikrotik|^routeros|^rb[0-9]" {
    /dados1/system-log/hot/hot_logs.raw;mikrotik_format
    & stop
}
```

#### Firewalls
```
:hostname, regex, "^firewall|^fw-|^pfsense|^fortigate" {
    /dados1/system-log/hot/hot_logs.raw;network_format
    & stop
}
```

#### Switches/Access Points
```
:hostname, regex, "^switch|^ap-|^access-point|^cisco" {
    /dados1/system-log/hot/hot_logs.raw;network_format
    & stop
}
```

### 💻 Sistema Local

- Kernel
- Firewall (UFW, iptables)
- SSH (sshd)
- Sudo
- Systemd
- Nginx
- MEGA LOG (Gunicorn, Python, Processor)
- Web apps (Apache, Tomcat, Node.js)
- Erros e Avisos

## 📝 Templates Disponíveis

| Template | Uso | Exemplo |
|----------|-----|---------|
| `megalog_format` | Logs gerais do sistema | `2024-12-09T21:31 system nginx...` |
| `kernel_format` | Logs do kernel | `2024-12-09T21:31 system [KERNEL] ...` |
| `firewall_format` | Logs de firewall | `2024-12-09T21:31 system [FIREWALL] ...` |
| `auth_format` | SSH, Sudo, Auth | `2024-12-09T21:31 system [AUTH] sshd...` |
| `mikrotik_format` | Mikrotik | `2024-12-09T21:31 10.100.100.1 [MIKROTIK]...` |
| `network_format` | Outros equipamentos | `2024-12-09T21:31 192.168.1.50 [NETWORK]...` |

## 🔧 Como Customizar

### Adicionar novo equipamento Mikrotik

```bash
# Editar
sudo nano /etc/rsyslog.d/50-megalog.conf

# Encontre a seção "Capturar logs do Mikrotik" e adicione:
if $fromhost-ip == 'SEU_IP_AQUI' then {
    /dados1/system-log/hot/hot_logs.raw;mikrotik_format
    & stop
}

# Ou por nome:
:hostname, regex, "seu-hostname-aqui" {
    /dados1/system-log/hot/hot_logs.raw;mikrotik_format
    & stop
}

# Validar
sudo rsyslogd -N 1

# Aplicar
sudo systemctl restart rsyslog
```

### Modificar formato do log

```bash
# Editar template
template(name="mikrotik_format" type="string" 
    string="NOVO_FORMATO_AQUI\n")

# Propriedades disponíveis:
# %timegenerated:1:19%   - Data/hora
# %fromhost-ip%          - IP de origem
# %HOSTNAME%             - Hostname
# %syslogtag%            - Tag do programa
# %msg%                  - Mensagem
```

## 🧪 Testar Configuração

### 1. Validar sintaxe
```bash
sudo rsyslogd -N 1
```

### 2. Ver logs em tempo real
```bash
tail -f /dados1/system-log/hot/hot_logs.raw
```

### 3. Enviar teste (Mikrotik simulado)
```bash
# Simular log com IP específico
sudo logger -t "test[123]" -p local0.info "Teste do Mikrotik"

# Ou com netcat (se tiver acesso ao Mikrotik)
echo "<34>mikrotik: test message" | nc -u localhost 514
```

### 4. Verificar erros
```bash
sudo journalctl -u rsyslog -f
```

## 📊 Exemplo de Logs Capturados

```
Dec  9 21:31 10.100.100.1 [MIKROTIK] RouterOS: address-list changed
Dec  9 21:31 10.100.100.1 [MIKROTIK] firewall: blocked 192.168.1.100
Dec  9 21:31 192.168.1.50 [NETWORK] Switch: Interface eth0 up
Dec  9 21:31 system [FIREWALL] [UFW BLOCK] IN=eth0 OUT= SRC=203.0.113.50
Dec  9 21:31 system [KERNEL] audit: type=1400
Dec  9 21:31 system sshd[1234]: Invalid user admin
```

## ⚙️ Prioridade de Processamento

As regras são aplicadas em ordem:

1. **Prioridade MÁXIMA** - Dispositivos de rede (Mikrotik, Firewall, etc)
2. **Prioridade Alta** - Sistema local (Kernel, SSH, Nginx, etc)
3. **Prioridade Média** - Severidade (erros, críticos)
4. **Prioridade Baixa** - Catch-all (avisos e acima)

## 🔐 Segurança

- Porta UDP 514 (syslog) está aberta
- Porta TCP 514 (syslog) está aberta
- Arquivo `/dados1/system-log/hot/hot_logs.raw` com permissões `0644`
- Proprietário: `root:root`

Para restringir por IP:
```
input(type="imudp" port="514" address="10.100.100.0/24" ruleSet="MEGA_LOG")
```

## 📋 Checklist

- [x] Configuração validada
- [x] Rsyslog ativo e rodando
- [x] Templates configurados para Mikrotik
- [x] Regras de captura por IP
- [x] Regras de captura por hostname
- [x] Prioridade correta de processamento
- [x] Permissões e performance configuradas

## 📚 Próximos Passos

1. Configurar seu Mikrotik/dispositivos para enviar logs:
   ```
   Mikrotik: /system logging action set 0 remote=SEU_IP_AQUI
   ```

2. Monitorar logs:
   ```bash
   tail -f /dados1/system-log/hot/hot_logs.raw | grep MIKROTIK
   ```

3. Verificar no MEGA LOG dashboard:
   ```
   http://localhost/search?filter=MIKROTIK
   ```

4. Se logs não chegarem, verificar:
   - Conectividade IP entre Mikrotik e servidor
   - Firewall permitindo porta 514
   - Configuração de syslog no Mikrotik

---

**Data:** Dezembro 2024  
**Versão rsyslog:** 8.2504.0  
**Status:** ✅ Operacional
