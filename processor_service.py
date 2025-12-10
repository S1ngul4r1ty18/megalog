#!/usr/bin/env python3
# processor_service.py
# Serviço de processamento em stream (24/7)

import time
import os
import sys
import signal
from datetime import datetime, date

try:
    from pygtail import Pygtail
except ImportError:
    print("❌ Erro: pygtail não instalado. Execute: pip install pygtail")
    sys.exit(1)

from app import config, database

# ==================== CONTROLE DE EXECUÇÃO ====================
running = True

def signal_handler(signum, frame):
    """Handler para shutdown gracioso"""
    global running
    print(f"\n⚠️ Sinal {signum} recebido. Encerrando processador...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ==================== PROCESSADOR ====================

class LogProcessor:
    def __init__(self):
        self.conn = None
        self.current_db_date = None
        self.log_batch = []
        self.last_batch_time = time.time()
        self.stats = {
            'lines_processed': 0,
            'lines_inserted': 0,
            'lines_filtered': 0,
            'lines_failed': 0,
            'last_log_time': None,
            'db_rotations': 0
        }
        
        # Cria arquivo de buffer se não existir
        if not os.path.exists(config.HOT_LOG_BUFFER_FILE):
            print(f"⚠️ Buffer não encontrado. Criando: {config.HOT_LOG_BUFFER_FILE}")
            os.makedirs(os.path.dirname(config.HOT_LOG_BUFFER_FILE), exist_ok=True)
            open(config.HOT_LOG_BUFFER_FILE, 'a').close()
        
        # Inicializa Pygtail (tail -f com memória)
        self.log_tail = Pygtail(
            config.HOT_LOG_BUFFER_FILE,
            offset_file=config.PROCESSOR_OFFSET_FILE,
            paranoid=True  # Detecta rotação de arquivo
        )
        
        print("✅ Processador inicializado")
    
    def connect_to_db(self, target_date: date = None):
        """Conecta ao banco de logs (cria se necessário)"""
        if target_date is None:
            target_date = date.today()
        
        # Fecha conexão anterior se existir
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        
        # Abre nova conexão
        db_path = database.get_log_db_path(target_date)
        self.conn = database.get_db_connection(db_path)
        
        if self.conn:
            database.create_log_schema(self.conn)
            database.load_caches(self.conn)
            self.current_db_date = target_date
            print(f"📂 Conectado ao DB: {os.path.basename(db_path)}")
            return True
        else:
            print(f"❌ Falha ao conectar ao DB de {target_date}")
            return False
    
    def check_db_rotation(self):
        """Verifica se precisa trocar de banco (mudança de dia)"""
        today = date.today()
        
        if self.current_db_date != today:
            print(f"📅 Mudança de dia detectada: {self.current_db_date} → {today}")
            
            # Salva lote pendente no DB antigo
            if self.log_batch:
                print(f"💾 Salvando {len(self.log_batch)} logs pendentes do dia anterior...")
                inserted = database.insert_log_batch(self.conn, self.log_batch)
                self.stats['lines_inserted'] += inserted
                self.log_batch = []
            
            # Atualiza stats do dia anterior
            self._update_db_stats()
            
            # Conecta ao novo DB
            if self.connect_to_db(today):
                self.stats['db_rotations'] += 1
                self.stats['lines_processed'] = 0
                self.stats['lines_inserted'] = 0
                return True
            else:
                print("❌ Falha crítica na rotação de DB!")
                return False
        
        return True
    
    def is_noise(self, line: str) -> bool:
        """Verifica se a linha é ruído (deve ser filtrada)"""
        for noise_filter in config.NOISE_FILTERS:
            if noise_filter in line:
                return True
        return False
    
    def process_line(self, line: str) -> bool:
        """Processa uma linha de log"""
        self.stats['lines_processed'] += 1
        
        # Filtro de ruído
        if self.is_noise(line):
            self.stats['lines_filtered'] += 1
            return False
        
        # Parse da linha
        parsed = database.parse_log_line(line)
        if not parsed:
            self.stats['lines_failed'] += 1
            return False
        
        # Prepara dados para inserção
        prepared = database.prepare_log_for_db(self.conn, parsed)
        if not prepared:
            self.stats['lines_failed'] += 1
            return False
        
        # Adiciona ao lote
        self.log_batch.append(prepared)
        self.stats['last_log_time'] = datetime.now()
        
        return True
    
    def should_flush_batch(self) -> bool:
        """Verifica se deve salvar o lote"""
        # Por tamanho
        if len(self.log_batch) >= config.BATCH_SIZE:
            return True
        
        # Por timeout
        if self.log_batch and (time.time() - self.last_batch_time > config.BATCH_TIMEOUT_SEC):
            return True
        
        return False
    
    def flush_batch(self):
        """Salva lote no banco"""
        if not self.log_batch:
            return
        
        batch_size = len(self.log_batch)
        inserted = database.insert_log_batch(self.conn, self.log_batch)
        
        if inserted > 0:
            self.stats['lines_inserted'] += inserted
            self.log_batch = []
            self.last_batch_time = time.time()
            
            # Atualiza stats a cada 1000 inserções
            if self.stats['lines_inserted'] % 1000 == 0:
                self._update_db_stats()
    
    def _update_db_stats(self):
        """Atualiza estatísticas no banco"""
        if not self.conn:
            return
        
        try:
            database.update_processor_stats(self.conn, 'lines_processed', self.stats['lines_processed'])
            database.update_processor_stats(self.conn, 'lines_inserted', self.stats['lines_inserted'])
            database.update_processor_stats(self.conn, 'lines_filtered', self.stats['lines_filtered'])
            database.update_processor_stats(self.conn, 'lines_failed', self.stats['lines_failed'])
            
            if self.stats['last_log_time']:
                database.update_processor_stats(self.conn, 'last_log_seen', 
                                              self.stats['last_log_time'].isoformat())
        except Exception as e:
            print(f"⚠️ Erro ao atualizar stats: {e}")
    
    def print_stats(self):
        """Imprime estatísticas"""
        print(f"\n📊 Estatísticas do Processador:")
        print(f"   Processadas: {self.stats['lines_processed']:,}")
        print(f"   Inseridas:   {self.stats['lines_inserted']:,}")
        print(f"   Filtradas:   {self.stats['lines_filtered']:,}")
        print(f"   Falhas:      {self.stats['lines_failed']:,}")
        print(f"   Rotações DB: {self.stats['db_rotations']}")
        print(f"   Buffer:      {len(self.log_batch)} logs")
        if self.stats['last_log_time']:
            print(f"   Último log:  {self.stats['last_log_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    def run(self):
        """Loop principal do processador"""
        global running
        
        print("🚀 Iniciando processador de logs...")
        print(f"   Buffer:     {config.HOT_LOG_BUFFER_FILE}")
        print(f"   Batch Size: {config.BATCH_SIZE}")
        print(f"   Timeout:    {config.BATCH_TIMEOUT_SEC}s")
        
        # Conecta ao DB inicial
        if not self.connect_to_db():
            print("❌ Falha ao conectar ao banco de dados. Abortando.")
            return
        
        last_stats_time = time.time()
        stats_interval = 300  # 5 minutos
        
        while running:
            try:
                # Verifica rotação de DB (mudança de dia)
                if not self.check_db_rotation():
                    print("⚠️ Falha na rotação de DB. Aguardando...")
                    time.sleep(10)
                    continue
                
                # Lê novas linhas do buffer
                new_lines = list(self.log_tail)
                
                if new_lines:
                    # Processa cada linha
                    for line in new_lines:
                        self.process_line(line)
                    
                    # Verifica se deve salvar lote
                    if self.should_flush_batch():
                        self.flush_batch()
                else:
                    # Sem novas linhas, verifica timeout do lote
                    if self.should_flush_batch():
                        self.flush_batch()
                    
                    # Dorme um pouco
                    time.sleep(1)
                
                # Imprime stats periodicamente
                if time.time() - last_stats_time > stats_interval:
                    self.print_stats()
                    last_stats_time = time.time()
                
            except KeyboardInterrupt:
                print("\n⚠️ Interrupção do usuário")
                break
            except Exception as e:
                print(f"❌ Erro no loop principal: {e}")
                print("   Tentando reconectar em 10s...")
                time.sleep(10)
                
                # Tenta reconectar
                try:
                    if self.connect_to_db():
                        print("✅ Reconectado com sucesso")
                    else:
                        print("❌ Falha ao reconectar")
                except Exception as reconnect_error:
                    print(f"❌ Erro ao reconectar: {reconnect_error}")
        
        # Shutdown gracioso
        print("\n🛑 Encerrando processador...")
        
        # Salva lote pendente
        if self.log_batch:
            print(f"💾 Salvando {len(self.log_batch)} logs pendentes...")
            self.flush_batch()
        
        # Atualiza stats finais
        self._update_db_stats()
        self.print_stats()
        
        # Fecha conexão
        if self.conn:
            self.conn.close()
        
        print("✅ Processador encerrado")

# ==================== MAIN ====================

def main():
    """Ponto de entrada"""
    print("=" * 60)
    print(f"  {config.SYSTEM_NAME} - Processador de Logs")
    print(f"  Versão: {config.SYSTEM_VERSION}")
    print("=" * 60)
    
    # Valida configuração (mas não falha)
    errors = config.validate_config()
    if errors:
        print("\n⚠️ AVISOS DE CONFIGURAÇÃO:")
        for error in errors:
            print(f"   - {error}")
        print()
    
    # Inicializa bancos
    database.initialize_databases()
    
    # Inicia processador
    processor = LogProcessor()
    
    try:
        processor.run()
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
