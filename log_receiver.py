#!/usr/bin/env python3
# log_receiver.py
# Receptor de logs via UDP (Syslog) - Escuta logs do Mikrotik

import socket
import sys
import signal
import time
import os
from datetime import datetime
from app import config

# ==================== CONFIGURAÇÃO ====================
SYSLOG_HOST = "0.0.0.0"  # Escuta em todas as interfaces
SYSLOG_PORT = 514        # Porta padrão do syslog
BUFFER_SIZE = 65535      # Tamanho máximo do buffer UDP

# ==================== CONTROLE ====================
running = True

def signal_handler(signum, frame):
    """Handler para shutdown gracioso"""
    global running
    print(f"\n⚠️ Sinal {signum} recebido. Encerrando receptor...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ==================== RECEPTOR ====================

class SyslogReceiver:
    def __init__(self, host=SYSLOG_HOST, port=SYSLOG_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.output_file = config.HOT_LOG_BUFFER_FILE
        self.stats = {
            'received': 0,
            'written': 0,
            'errors': 0,
            'started_at': None,
            'last_log': None
        }
        
    def start(self):
        """Inicia o receptor"""
        global running
        
        # Garante que diretório existe
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        
        # Cria socket UDP
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(1.0)  # Timeout de 1 segundo
            
            print(f"✅ Socket UDP criado e vinculado a {self.host}:{self.port}")
        except Exception as e:
            print(f"❌ Erro ao criar socket: {e}")
            print(f"   Dica: Porta {self.port} pode requerer privilégios root")
            return False
        
        self.stats['started_at'] = datetime.now()
        
        print(f"🎧 Receptor de logs iniciado")
        print(f"   Escutando: {self.host}:{self.port}")
        print(f"   Saída: {self.output_file}")
        print(f"   Pressione Ctrl+C para parar\n")
        
        last_stats_time = time.time()
        
        # Loop principal
        with open(self.output_file, 'a', buffering=1) as f:  # Line buffered
            while running:
                try:
                    # Recebe dados
                    data, addr = self.socket.recvfrom(BUFFER_SIZE)
                    
                    if data:
                        self.stats['received'] += 1
                        
                        # Decodifica
                        try:
                            log_line = data.decode('utf-8', errors='ignore').strip()
                            
                            # Ignora linhas vazias
                            if not log_line:
                                continue
                            
                            # Adiciona timestamp de recebimento
                            timestamp = datetime.now().isoformat()
                            self.stats['last_log'] = timestamp
                            
                            # Escreve no arquivo
                            f.write(f"{log_line}\n")
                            self.stats['written'] += 1
                            
                            # Debug: mostra alguns logs
                            if self.stats['received'] <= 5 or self.stats['received'] % 1000 == 0:
                                print(f"[{timestamp}] De {addr[0]}: {log_line[:100]}...")
                            
                        except Exception as e:
                            self.stats['errors'] += 1
                            if self.stats['errors'] <= 5:
                                print(f"⚠️ Erro ao processar log: {e}")
                    
                    # Imprime estatísticas a cada 60 segundos
                    if time.time() - last_stats_time >= 60:
                        self.print_stats()
                        last_stats_time = time.time()
                    
                except socket.timeout:
                    # Timeout normal, continua
                    continue
                except Exception as e:
                    self.stats['errors'] += 1
                    print(f"❌ Erro no loop: {e}")
                    time.sleep(1)
        
        print("\n🛑 Encerrando receptor...")
        self.print_stats()
        
        if self.socket:
            self.socket.close()
        
        print("✅ Receptor encerrado")
        return True
    
    def print_stats(self):
        """Imprime estatísticas"""
        uptime = None
        if self.stats['started_at']:
            uptime = datetime.now() - self.stats['started_at']
        
        print(f"\n📊 Estatísticas do Receptor:")
        print(f"   Logs recebidos: {self.stats['received']:,}")
        print(f"   Logs gravados:  {self.stats['written']:,}")
        print(f"   Erros:          {self.stats['errors']:,}")
        
        if uptime:
            print(f"   Uptime:         {uptime}")
            
        if self.stats['last_log']:
            print(f"   Último log:     {self.stats['last_log']}")
        
        # Tamanho do arquivo
        if os.path.exists(self.output_file):
            size_mb = os.path.getsize(self.output_file) / (1024**2)
            print(f"   Arquivo:        {size_mb:.2f} MB")
        
        print()

# ==================== MAIN ====================

def main():
    """Ponto de entrada"""
    print("=" * 60)
    print(f"  {config.SYSTEM_NAME} - Receptor de Logs")
    print(f"  Versão: {config.SYSTEM_VERSION}")
    print("=" * 60)
    print()
    
    # Verifica porta
    if SYSLOG_PORT < 1024 and os.geteuid() != 0:
        print(f"⚠️ AVISO: Porta {SYSLOG_PORT} requer privilégios root")
        print(f"   Execute com: sudo python3 {sys.argv[0]}")
        print(f"   Ou mude SYSLOG_PORT no código para >= 1024")
        print()
    
    # Inicia receptor
    receiver = SyslogReceiver()
    
    try:
        receiver.start()
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
