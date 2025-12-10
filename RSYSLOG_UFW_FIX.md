# ✅ Correção: UFW Logs agora com tag [FIREWALL]

## Problema Resolvido

Os logs de firewall UFW/iptables estavam sendo capturados com a tag `[KERNEL]` ao invés de `[FIREWALL]`.

**Antes:**
```
Dec  9 21:35:08 system [KERNEL]  [UFW BLOCK] IN=ens192 OUT= ...
```

**Depois:**
```
Dec  9 21:38:46 system [FIREWALL]  [UFW BLOCK] IN=ens192 OUT= ...
```

## Solução Aplicada

### 1. Reordenação das Regras de Captura

Movemos as regras de **Firewall/UFW antes de Kernel** para garantir que mensagens contendo `[UFW]` sejam capturadas primeiro:

```rsyslog
###############################################################################
# REGRAS DE ROTEAMENTO - Firewall/UFW (Prioridade MUITO ALTA - Antes de Kernel)
###############################################################################

# Capturar UFW BLOCK/ALLOW (padrão [UFW])
if $msg contains "[UFW BLOCK]" or $msg contains "[UFW ALLOW]" or $msg contains "[UFW DROP]" then {
    /dados1/system-log/hot/hot_logs.raw;firewall_format
    & stop
}

# Capturar padrão de firewall kernel (IN=, OUT=, MAC=, SRC=, DST=)
if ($msg contains "IN=" and $msg contains "OUT=") or ($msg contains "SRC=" and $msg contains "DST=") 
   or ($msg contains "MAC=" and $msg contains "LEN=") then {
    /dados1/system-log/hot/hot_logs.raw;firewall_format
    & stop
}

# Capturar logs com palavras-chave firewall
if $msg contains "FIREWALL" or $msg contains "iptables" or $msg contains "REJECT" 
   or $msg contains "ACCEPT" then {
    /dados1/system-log/hot/hot_logs.raw;firewall_format
    & stop
}
```

### 2. Uso de `contains` em vez de `regex`

Alteramos de operadores regex para `contains` (mais compatível com rsyslog 8.2504.0):

- ❌ `:msg, regex, "..."`
- ✅ `if $msg contains "..."`

### 3. Sintaxe `startswith` para Nomes de Hosts

Para capturar dispositivos por hostname:

```rsyslog
# Capturar logs de outros Mikrotik/equipamentos de rede por nome
if ($hostname startswith "mikrotik") or ($hostname startswith "routeros") or ($hostname startswith "rb") then {
    /dados1/system-log/hot/hot_logs.raw;mikrotik_format
    & stop
}
```

## Padrões Capturados

### UFW Logs IPv4 e IPv6
```
[UFW BLOCK]  IN=eth0 OUT= MAC=... SRC=192.168.1.100 DST=192.168.1.1 ...
[UFW ALLOW]  IN=eth0 OUT=eth1 MAC=... SRC=203.0.113.50 DST=10.0.0.1 ...
[UFW DROP]   ...
```

### Padrão de Firewall Kernel (iptables)
Qualquer mensagem com:
- `IN=` E `OUT=` (interfaces)
- `SRC=` E `DST=` (IPs)
- `MAC=` E `LEN=` (pacotes)

## Templates Utilizados

| Tag | Template | Formato |
|-----|----------|---------|
| `[FIREWALL]` | `firewall_format` | `2024-12-09T21:38 system [FIREWALL] [UFW BLOCK] IN=...` |
| `[KERNEL]` | `kernel_format` | `2024-12-09T21:38 system [KERNEL] message` |
| `[MIKROTIK]` | `mikrotik_format` | `2024-12-09T21:38 10.100.100.1 [MIKROTIK] message` |
| `[AUTH]` | `auth_format` | `2024-12-09T21:38 system [AUTH] sshd[1234]: ...` |
| `[NETWORK]` | `network_format` | `2024-12-09T21:38 192.168.1.50 [NETWORK] message` |

## Prioridade de Processamento (Atualizado)

1. ✅ **Prioridade MÁXIMA** - Dispositivos de rede (Mikrotik, Firewall, Switches)
2. ✅ **Prioridade MUITO ALTA** - Firewall/UFW (ANTES de Kernel) 
3. ✅ **Prioridade ALTA** - Sistema local (Kernel, SSH, Nginx, etc)
4. ✅ **Prioridade MÉDIA** - Severidade (erros, críticos)
5. ✅ **Prioridade BAIXA** - Catch-all (avisos)

## Validação

```bash
# Validar configuração
sudo rsyslogd -N 1
# Output: "End of config validation run. Bye." ✅

# Status do serviço
sudo systemctl status rsyslog
# Output: "Active: active (running)" ✅

# Verificar captura em tempo real
sudo tail -f /dados1/system-log/hot/hot_logs.raw | grep FIREWALL
```

## Teste Manual

Para testar a captura de UFW:

```bash
# Simular log UFW BLOCK
sudo logger -t "kernel" -p kern.warning "[UFW BLOCK] IN=eth0 OUT= SRC=192.168.1.100 DST=192.168.1.1"

# Simular log UFW ALLOW
sudo logger -t "kernel" -p kern.info "[UFW ALLOW] IN=eth0 OUT=eth1 PROTO=TCP SPT=22 DPT=22"

# Simular padrão iptables
sudo logger -t "kernel" -p kern.notice "IN=eth0 OUT= SRC=10.0.0.5 DST=10.0.0.1 MAC=..."

# Verificar resultado
tail -1 /dados1/system-log/hot/hot_logs.raw
# Deve conter [FIREWALL]
```

## Próximos Passos

✅ **UFW**: Agora captura logs com tag `[FIREWALL]`
✅ **Mikrotik**: Captura com tag `[MIKROTIK]` (IP 177.67.176.144)
✅ **Sistema**: Kernel, SSH, Nginx com tags apropriadas

### Adicionar Mais Padrões

Para adicionar novos padrões de firewall:

```rsyslog
# Adicionar ao final da seção Firewall/UFW
if $msg contains "seu_padrão_aqui" then {
    /dados1/system-log/hot/hot_logs.raw;firewall_format
    & stop
}
```

---

**Status:** ✅ IMPLEMENTADO E TESTADO  
**Data:** 9 de Dezembro de 2025  
**Versão rsyslog:** 8.2504.0  
**Arquivo:** `/etc/rsyslog.d/50-megalog.conf`
