# app/database.py
# Engine de banco de dados com normalização e cache

import sqlite3
import os
import re
import ipaddress
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
from app import config

# ==================== REGEX DE PARSING ====================
# Suporta logs Mikrotik com NAT
LOG_REGEX_WITH_NAT = re.compile(
    r'.*?(?P<syslog_ts>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*?'
    r'in:(?P<interface_in>\S+)\s+'
    r'out:(?P<interface_out>\S+),\s+.*?'
    r'proto\s+(?P<proto>\S+),\s+'
    r'(?P<src_ip_priv>[\d\.]+):(?P<src_port_priv>\d+)->'
    r'(?P<dst_ip>[\d\.]+):(?P<dst_port>\d+),\s+.*?'
    r'NAT\s+\((?P<nat_ip_priv>[\d\.]+):(?P<nat_port_priv>\d+)->'
    r'(?P<nat_ip_pub>[\d\.]+):(?P<nat_port_pub>\d+)\)->'
)

# Suporta logs sem NAT (fallback)
LOG_REGEX_NO_NAT = re.compile(
    r'.*?(?P<syslog_ts>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*?'
    r'in:(?P<interface_in>\S+)\s+'
    r'out:(?P<interface_out>\S+),\s+.*?'
    r'proto\s+(?P<proto>\S+),\s+'
    r'(?P<src_ip_priv>[\d\.]+):(?P<src_port_priv>\d+)->'
    r'(?P<dst_ip>[\d\.]+):(?P<dst_port>\d+)'
)

# ==================== CACHE GLOBAL ====================
# Cache em memória para dicionários (compressão)
D_CACHE = {
    "d_interfaces": {},  # {"ether1": 1, "ether2": 2, ...}
    "d_protocols": {},   # {"tcp": 1, "udp": 2, ...}
    "d_states": {}       # {"new": 1, "established": 2, ...}
}

# ==================== CONEXÕES ====================

def get_db_connection(db_path: str, timeout: float = None) -> Optional[sqlite3.Connection]:
    """Cria conexão otimizada com SQLite"""
    if timeout is None:
        timeout = config.DB_TIMEOUT
    
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        conn.execute(f"PRAGMA journal_mode = {config.DB_JOURNAL_MODE};")
        conn.execute(f"PRAGMA synchronous = {config.DB_SYNCHRONOUS};")
        conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
        conn.row_factory = sqlite3.Row  # Permite acesso por nome de coluna
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar ao DB {db_path}: {e}")
        return None

def get_users_db_connection() -> Optional[sqlite3.Connection]:
    """Conexão com banco de usuários"""
    return get_db_connection(config.USERS_DB_PATH)

def get_log_db_path(date_obj: date = None) -> str:
    """Retorna caminho do DB de logs para uma data específica"""
    if date_obj is None:
        date_obj = date.today()
    
    db_name = date_obj.strftime(config.LOG_DB_FILENAME_FORMAT)
    return os.path.join(config.COLD_STORAGE_DIR, db_name)

def get_current_log_db_connection() -> Optional[sqlite3.Connection]:
    """Conexão com banco de logs do dia atual"""
    db_path = get_log_db_path()
    conn = get_db_connection(db_path)
    if conn:
        create_log_schema(conn)
        load_caches(conn)
    return conn

# ==================== SCHEMAS ====================

def create_users_schema(conn: sqlite3.Connection):
    """Cria schema do banco de usuários"""
    try:
        with conn:
            # Tabela de usuários
            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Tabela de auditoria de consultas
            if config.ENABLE_AUDIT_LOG:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """)
                
                conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
                ON audit_log(timestamp DESC)
                """)
                
                conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user 
                ON audit_log(user_id)
                """)
        
        print("✅ Schema de usuários criado/verificado")
    except Exception as e:
        print(f"❌ Erro ao criar schema de usuários: {e}")

def create_log_schema(conn: sqlite3.Connection):
    """Cria schema do banco de logs (normalizado)"""
    try:
        with conn:
            # Tabelas de dicionário (normalização)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS d_interfaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """)
            
            conn.execute("""
            CREATE TABLE IF NOT EXISTS d_protocols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """)
            
            conn.execute("""
            CREATE TABLE IF NOT EXISTS d_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """)
            
            # Tabela principal de logs (otimizada)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                interface_in_id INTEGER NOT NULL,
                interface_out_id INTEGER NOT NULL,
                state_id INTEGER,
                protocol_id INTEGER NOT NULL,
                src_ip_priv INTEGER NOT NULL,
                src_port_priv INTEGER NOT NULL,
                dst_ip INTEGER NOT NULL,
                dst_port INTEGER NOT NULL,
                nat_ip_pub INTEGER,
                nat_port_pub INTEGER,
                FOREIGN KEY (interface_in_id) REFERENCES d_interfaces(id),
                FOREIGN KEY (interface_out_id) REFERENCES d_interfaces(id),
                FOREIGN KEY (state_id) REFERENCES d_states(id),
                FOREIGN KEY (protocol_id) REFERENCES d_protocols(id)
            )
            """)
            
            # Índices otimizados para busca forense
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp 
            ON logs(timestamp DESC)
            """)
            
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_src_ip 
            ON logs(src_ip_priv)
            """)
            
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_nat_ip 
            ON logs(nat_ip_pub)
            """)
            
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_dst_ip 
            ON logs(dst_ip)
            """)
            
            # Índice composto para buscas por IP+Porta (mais comum)
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_nat_combo 
            ON logs(nat_ip_pub, nat_port_pub, timestamp DESC)
            """)
            
            # Tabela de estatísticas do processador
            conn.execute("""
            CREATE TABLE IF NOT EXISTS processor_stats (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
    except Exception as e:
        print(f"❌ Erro ao criar schema de logs: {e}")

# ==================== CACHE ====================

def load_caches(conn: sqlite3.Connection):
    """Carrega dicionários na memória para inserções rápidas"""
    global D_CACHE
    
    for table in D_CACHE.keys():
        try:
            cursor = conn.execute(f"SELECT id, name FROM {table}")
            D_CACHE[table] = {row['name']: row['id'] for row in cursor.fetchall()}
        except Exception as e:
            print(f"⚠️ Aviso ao carregar cache {table}: {e}")
    
    total_items = sum(len(cache) for cache in D_CACHE.values())
    if total_items > 0:
        print(f"✅ Cache carregado: {total_items} itens")

def get_or_create_dict_id(conn: sqlite3.Connection, table: str, value: str) -> Optional[int]:
    """Pega ID do cache ou cria novo (normalização)"""
    value = value.strip()
    if not value:
        return None
    
    # Busca no cache primeiro (O(1))
    if value in D_CACHE[table]:
        return D_CACHE[table][value]
    
    # Não está no cache, insere no DB
    try:
        with conn:
            cursor = conn.execute(f"INSERT INTO {table} (name) VALUES (?)", (value,))
            new_id = cursor.lastrowid
            D_CACHE[table][value] = new_id
            return new_id
    except sqlite3.IntegrityError:
        # Race condition: outro processo inseriu enquanto estávamos tentando
        try:
            cursor = conn.execute(f"SELECT id FROM {table} WHERE name = ?", (value,))
            row = cursor.fetchone()
            if row:
                D_CACHE[table][value] = row['id']
                return row['id']
        except Exception as inner_e:
            print(f"⚠️ Erro ao recuperar ID em race condition: {inner_e}")
    except Exception as e:
        print(f"❌ Erro em get_or_create_dict_id({table}, {value}): {e}")
    
    return None

# ==================== PARSING ====================

def parse_log_line(line: str) -> Optional[Dict]:
    """Analisa linha de log e retorna dicionário com campos"""
    # Tenta regex com NAT primeiro
    match = LOG_REGEX_WITH_NAT.search(line)
    if match:
        data = match.groupdict()
        data['has_nat'] = True
        return data
    
    # Fallback: regex sem NAT
    match = LOG_REGEX_NO_NAT.search(line)
    if match:
        data = match.groupdict()
        data['has_nat'] = False
        data['nat_ip_pub'] = None
        data['nat_port_pub'] = None
        return data
    
    return None

def convert_ip_to_int(ip_str: str) -> Optional[int]:
    """Converte IP string para inteiro"""
    if not ip_str:
        return None
    try:
        return int(ipaddress.IPv4Address(ip_str))
    except (ipaddress.AddressValueError, ValueError):
        return None

def convert_int_to_ip(ip_int: int) -> Optional[str]:
    """Converte IP inteiro para string"""
    if not ip_int:
        return None
    try:
        return str(ipaddress.IPv4Address(ip_int))
    except (ipaddress.AddressValueError, ValueError):
        return None

def parse_timestamp(ts_str: str) -> Optional[int]:
    """Converte timestamp syslog para Unix timestamp"""
    try:
        current_year = datetime.now().year
        # Formato: "Dec  2 14:23:45"
        dt_str = f"{ts_str} {current_year}"
        dt = datetime.strptime(dt_str, '%b %d %H:%M:%S %Y')
        
        # Ajuste de ano (se log é de dezembro mas estamos em janeiro)
        now = datetime.now()
        if dt.month == 12 and now.month == 1:
            dt = dt.replace(year=current_year - 1)
        
        return int(dt.timestamp())
    except Exception:
        return None

def prepare_log_for_db(conn: sqlite3.Connection, parsed: Dict) -> Optional[Tuple]:
    """Converte log parseado em tupla para inserção"""
    try:
        # Timestamp
        ts = parse_timestamp(parsed['syslog_ts'])
        if ts is None:
            return None
        
        # Normaliza strings em IDs
        in_if_id = get_or_create_dict_id(conn, 'd_interfaces', parsed['interface_in'])
        out_if_id = get_or_create_dict_id(conn, 'd_interfaces', parsed['interface_out'])
        proto_id = get_or_create_dict_id(conn, 'd_protocols', parsed['proto'])
        state_id = get_or_create_dict_id(conn, 'd_states', parsed.get('state', 'unknown'))
        
        if not all([in_if_id, out_if_id, proto_id]):
            return None
        
        # Converte IPs para inteiros
        src_ip = convert_ip_to_int(parsed['src_ip_priv'])
        dst_ip = convert_ip_to_int(parsed['dst_ip'])
        nat_ip = convert_ip_to_int(parsed.get('nat_ip_pub'))
        
        if src_ip is None or dst_ip is None:
            return None
        
        return (
            ts,
            in_if_id,
            out_if_id,
            state_id,
            proto_id,
            src_ip,
            int(parsed['src_port_priv']),
            dst_ip,
            int(parsed['dst_port']),
            nat_ip,
            int(parsed.get('nat_port_pub', 0) or 0)
        )
    except Exception as e:
        # Silencioso para não poluir logs
        return None

# ==================== INSERÇÃO ====================

def insert_log_batch(conn: sqlite3.Connection, batch: List[Tuple]) -> int:
    """Insere lote de logs no DB"""
    if not batch:
        return 0
    
    try:
        with conn:
            conn.executemany("""
            INSERT INTO logs (
                timestamp, interface_in_id, interface_out_id, state_id, protocol_id,
                src_ip_priv, src_port_priv, dst_ip, dst_port, nat_ip_pub, nat_port_pub
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
        return len(batch)
    except Exception as e:
        print(f"❌ Erro ao inserir lote: {e}")
        return 0

def update_processor_stats(conn: sqlite3.Connection, key: str, value: str):
    """Atualiza estatística do processador"""
    try:
        with conn:
            conn.execute("""
            INSERT INTO processor_stats (key, value, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET 
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """, (key, str(value)))
    except Exception as e:
        print(f"❌ Erro ao atualizar stats: {e}")

def get_processor_stats(conn: sqlite3.Connection) -> Dict:
    """Obtém estatísticas do processador"""
    stats = {}
    try:
        cursor = conn.execute("SELECT key, value, updated_at FROM processor_stats")
        for row in cursor:
            stats[row['key']] = {
                'value': row['value'],
                'updated_at': row['updated_at']
            }
    except Exception:
        pass
    return stats

# ==================== INICIALIZAÇÃO ====================

def initialize_databases():
    """Inicializa todos os bancos de dados"""
    print("🔧 Inicializando bancos de dados...")
    
    # 1. Banco de usuários
    users_conn = get_users_db_connection()
    if users_conn:
        create_users_schema(users_conn)
        users_conn.close()
        print("✅ Banco de usuários OK")
    else:
        print("❌ Falha ao criar banco de usuários")
    
    # 2. Banco de logs do dia atual
    logs_conn = get_current_log_db_connection()
    if logs_conn:
        logs_conn.close()
        print("✅ Banco de logs OK")
    else:
        print("❌ Falha ao criar banco de logs")

if __name__ == "__main__":
    # Teste do módulo
    initialize_databases()
    
    # Teste de parsing
    test_log = """Dec  2 14:23:45 router firewall,info forward: in:ether1 out:ether2, proto tcp, 100.80.3.210:41760->8.8.8.8:443, NAT (100.80.3.210:41760->177.67.176.147:41760)->8.8.8.8:443"""
    
    parsed = parse_log_line(test_log)
    if parsed:
        print(f"✅ Log parseado com sucesso:")
        print(f"   IP Origem: {parsed['src_ip_priv']}:{parsed['src_port_priv']}")
        print(f"   IP NAT: {parsed.get('nat_ip_pub')}:{parsed.get('nat_port_pub')}")
        print(f"   IP Destino: {parsed['dst_ip']}:{parsed['dst_port']}")
    else:
        print("❌ Falha ao parsear log")
