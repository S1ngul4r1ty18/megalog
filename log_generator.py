#!/usr/bin/env python3
# log_generator.py
# Gera logs de teste simulando Mikrotik CGNAT

import socket
import time
import random
from datetime import datetime

# ==================== CONFIGURAÇÃO ====================
SYSLOG_SERVER = "127.0.0.1"  # Localhost para teste
SYSLOG_PORT = 514             # Porta padrão
LOGS_PER_SECOND = 10          # Quantidade de logs por segundo

# ==================== DADOS DE TESTE ====================

# IPs privados CGNAT (100.64.0.0/10)
PRIVATE_IPS = [
    "100.64.3.10", "100.64.3.15", "100.64.3.20", "100.64.3.25",
    "100.80.5.100", "100.80.5.105", "100.80.5.110", "100.80.5.115",
    "100.90.10.50", "100.90.10.55", "100.90.10.60", "100.90.10.65"
]

# IPs públicos de saída (simula seu pool público)
PUBLIC_IPS = [
    "177.67.176.147", "177.67.176.148", "177.67.176.149",
    "177.67.176.150", "177.67.176.151", "177.67.176.152"
]

# Destinos populares
DESTINATIONS = [
    ("8.8.8.8", 53),           # Google DNS
    ("1.1.1.1", 53),           # Cloudflare DNS
    ("142.250.185.78", 443),   # Google
    ("31.13.71.36", 443),      # Facebook
    ("157.240.15.35", 443),    # Instagram
    ("13.107.42.14", 443),     # Microsoft
    ("151.101.1.140", 443),    # Reddit
]

INTERFACES_IN = ["ether1-cgnat", "ether2-cgnat", "ether3-cgnat"]
INTERFACES_OUT = ["ether5-wan", "ether6-wan"]
PROTOCOLS = ["tcp", "udp", "icmp"]
STATES = ["new", "established", "related"]

# ==================== GERADOR ====================

class LogGenerator:
    def __init__(self, server=SYSLOG_SERVER, port=SYSLOG_PORT):
        self.server = server
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stats = {'sent': 0, 'errors': 0}
        
    def generate_log(self):
        """Gera um log no formato Mikrotik"""
        # Timestamp
        now = datetime.now()
        ts = now.strftime('%b %d %H:%M:%S')
        
        # IPs e portas
        src_ip_priv = random.choice(PRIVATE_IPS)
        src_port_priv = random.randint(30000, 65535)
        
        dst_ip, dst_port = random.choice(DESTINATIONS)
        
        nat_ip_pub = random.choice(PUBLIC_IPS)
        nat_port_pub = random.randint(30000, 65535)
        
        # Interface e protocolo
        if_in = random.choice(INTERFACES_IN)
        if_out = random.choice(INTERFACES_OUT)
        proto = random.choice(PROTOCOLS)
        state = random.choice(STATES)
        
        # Monta log
        log = (
            f"{ts} mikrotik-router firewall,info forward: "
            f"in:{if_in} out:{if_out}, "
            f"connection-state:{state} "
            f"proto {proto}, "
            f"{src_ip_priv}:{src_port_priv}->{dst_ip}:{dst_port}, "
            f"NAT ({src_ip_priv}:{src_port_priv}->{nat_ip_pub}:{nat_port_pub})->{dst_ip}:{dst_port}"
        )
        
        return log
    
    def send_log(self, log):
        """Envia log via UDP"""
        try:
            message = log.encode('utf-8')
            self.socket.sendto(message, (self.server, self.port))
            self.stats['sent'] += 1
            return True
        except Exception as e:
            self.stats['errors'] += 1
            print(f"❌ Erro ao enviar: {e}")
            return False
    
    def run(self, duration_seconds=60):
        """Executa geração de logs"""
        print(f"🚀 Iniciando gerador de logs")
        print(f"   Destino: {self.server}:{self.port}")
        print(f"   Taxa: {LOGS_PER_SECOND} logs/segundo")
        print(f"   Duração: {duration_seconds}s")
        print()
        
        start_time = time.time()
        interval = 1.0 / LOGS_PER_SECOND
        
        try:
            while time.time() - start_time < duration_seconds:
                log = self.generate_log()
                self.send_log(log)
                
                # Mostra alguns logs
                if self.stats['sent'] <= 3 or self.stats['sent'] % 100 == 0:
                    print(f"[{self.stats['sent']}] {log}")
                
                time.sleep(interval)
            
            print(f"\n✅ Geração concluída!")
            print(f"   Enviados: {self.stats['sent']:,}")
            print(f"   Erros: {self.stats['errors']:,}")
            
        except KeyboardInterrupt:
            print(f"\n⚠️ Interrompido pelo usuário")
            print(f"   Enviados: {self.stats['sent']:,}")
    
    def test_connection(self):
        """Testa conexão com servidor"""
        print(f"🔍 Testando conexão com {self.server}:{self.port}...")
        
        test_log = self.generate_log()
        
        if self.send_log(test_log):
            print(f"✅ Conexão OK!")
            print(f"   Log enviado: {test_log[:80]}...")
            return True
        else:
            print(f"❌ Falha na conexão")
            return False

# ==================== MAIN ====================

def main():
    """Ponto de entrada"""
    global LOGS_PER_SECOND
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerador de Logs de Teste - MEGA LOG")
    parser.add_argument('--server', default=SYSLOG_SERVER, help='IP do servidor syslog')
    parser.add_argument('--port', type=int, default=SYSLOG_PORT, help='Porta do servidor')
    parser.add_argument('--rate', type=int, default=LOGS_PER_SECOND, help='Logs por segundo')
    parser.add_argument('--duration', type=int, default=60, help='Duração em segundos')
    parser.add_argument('--test', action='store_true', help='Apenas testa conexão')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  MEGA LOG - Gerador de Logs de Teste")
    print("=" * 60)
    print()
    
    LOGS_PER_SECOND = args.rate
    
    generator = LogGenerator(args.server, args.port)
    
    if args.test:
        generator.test_connection()
    else:
        generator.run(args.duration)

if __name__ == "__main__":
    main()
