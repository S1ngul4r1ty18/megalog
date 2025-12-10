# app/models.py
# Modelos de dados e queries complexas

import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from app import config, database

# ==================== USER MODEL ====================

class User:
    """Modelo de usuário"""
    
    def __init__(self, id: int, username: str, is_admin: bool = False):
        self.id = id
        self.username = username
        self.is_admin = is_admin
    
    @staticmethod
    def create(username: str, password: str, is_admin: bool = False) -> Optional['User']:
        """Cria novo usuário"""
        from werkzeug.security import generate_password_hash
        
        conn = database.get_users_db_connection()
        if not conn:
            return None
        
        try:
            password_hash = generate_password_hash(password, method='pbkdf2:sha256:600000')
            
            with conn:
                cursor = conn.execute("""
                INSERT INTO users (username, password_hash, is_admin)
                VALUES (?, ?, ?)
                """, (username, password_hash, int(is_admin)))
                
                user_id = cursor.lastrowid
            
            conn.close()
            print(f"✅ Usuário '{username}' criado (ID: {user_id})")
            return User(user_id, username, is_admin)
            
        except Exception as e:
            print(f"❌ Erro ao criar usuário: {e}")
            if conn:
                conn.close()
            return None
    
    @staticmethod
    def authenticate(username: str, password: str) -> Optional['User']:
        """Autentica usuário"""
        from werkzeug.security import check_password_hash
        
        conn = database.get_users_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.execute("""
            SELECT id, username, password_hash, is_admin
            FROM users
            WHERE username = ?
            """, (username,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and check_password_hash(row['password_hash'], password):
                return User(row['id'], row['username'], bool(row['is_admin']))
            
        except Exception as e:
            print(f"❌ Erro ao autenticar: {e}")
            if conn:
                conn.close()
        
        return None
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional['User']:
        """Busca usuário por ID"""
        conn = database.get_users_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.execute("""
            SELECT id, username, is_admin
            FROM users
            WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return User(row['id'], row['username'], bool(row['is_admin']))
        
        except Exception as e:
            print(f"❌ Erro ao buscar usuário: {e}")
            if conn:
                conn.close()
        
        return None
    
    @staticmethod
    def get_all() -> List['User']:
        """Lista todos os usuários"""
        conn = database.get_users_db_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.execute("""
            SELECT id, username, is_admin
            FROM users
            ORDER BY username
            """)
            
            users = [User(row['id'], row['username'], bool(row['is_admin'])) 
                    for row in cursor.fetchall()]
            conn.close()
            return users
            
        except Exception as e:
            print(f"❌ Erro ao listar usuários: {e}")
            if conn:
                conn.close()
            return []
    
    @staticmethod
    def delete(user_id: int) -> bool:
        """Deleta usuário"""
        conn = database.get_users_db_connection()
        if not conn:
            return False
        
        try:
            with conn:
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Erro ao deletar usuário: {e}")
            if conn:
                conn.close()
            return False
    
    @staticmethod
    def update_password(user_id: int, new_password: str) -> bool:
        """Atualiza senha do usuário"""
        from werkzeug.security import generate_password_hash
        
        conn = database.get_users_db_connection()
        if not conn:
            return False
        
        try:
            password_hash = generate_password_hash(new_password, method='pbkdf2:sha256:600000')
            
            with conn:
                conn.execute("""
                UPDATE users SET password_hash = ?
                WHERE id = ?
                """, (password_hash, user_id))
            
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Erro ao atualizar senha: {e}")
            if conn:
                conn.close()
            return False

# ==================== AUDIT LOG ====================

class AuditLog:
    """Log de auditoria de consultas"""
    
    @staticmethod
    def log_action(user_id: int, username: str, action: str, 
                   details: str = None, ip_address: str = None):
        """Registra ação de auditoria"""
        if not config.ENABLE_AUDIT_LOG:
            return
        
        conn = database.get_users_db_connection()
        if not conn:
            return
        
        try:
            with conn:
                conn.execute("""
                INSERT INTO audit_log (user_id, username, action, details, ip_address)
                VALUES (?, ?, ?, ?, ?)
                """, (user_id, username, action, details, ip_address))
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao registrar auditoria: {e}")
            if conn:
                conn.close()
    
    @staticmethod
    def get_recent(limit: int = 100) -> List[Dict]:
        """Busca logs de auditoria recentes"""
        conn = database.get_users_db_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.execute("""
            SELECT id, user_id, username, action, details, ip_address, timestamp
            FROM audit_log
            ORDER BY timestamp DESC
            LIMIT ?
            """, (limit,))
            
            logs = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return logs
        except Exception as e:
            print(f"❌ Erro ao buscar auditoria: {e}")
            if conn:
                conn.close()
            return []

# ==================== LOG SEARCH ====================

class LogSearch:
    """Engine de busca forense"""
    
    @staticmethod
    def get_db_files_in_range(start_date: date, end_date: date) -> List[str]:
        """Retorna lista de arquivos DB no intervalo de datas"""
        db_files = []
        current = start_date
        
        while current <= end_date:
            db_path = database.get_log_db_path(current)
            if os.path.exists(db_path):
                db_files.append(db_path)
            current += timedelta(days=1)
        
        return db_files
    
    @staticmethod
    def search(start_dt: datetime, end_dt: datetime,
               ip_privado: str = None, port_privada: str = None,
               ip_publico: str = None, port_publica: str = None,
               ip_destino: str = None, port_destino: str = None,
               limit: int = 1000, user_id: int = None, username: str = None,
               ip_address: str = None) -> Tuple[List[Dict], int]:
        """
        Executa busca forense nos logs
        
        Returns:
            (resultados, total_encontrado)
        """
        
        # Log de auditoria
        if user_id and username:
            filters_used = []
            if ip_privado: filters_used.append(f"IP Privado={ip_privado}")
            if port_privada: filters_used.append(f"Porta Privada={port_privada}")
            if ip_publico: filters_used.append(f"IP Público={ip_publico}")
            if port_publica: filters_used.append(f"Porta Pública={port_publica}")
            if ip_destino: filters_used.append(f"IP Destino={ip_destino}")
            if port_destino: filters_used.append(f"Porta Destino={port_destino}")
            
            details = f"Período: {start_dt.date()} a {end_dt.date()} | Filtros: {', '.join(filters_used) if filters_used else 'Nenhum'}"
            AuditLog.log_action(user_id, username, "BUSCA_FORENSE", details, ip_address)
        
        # Busca arquivos DB no intervalo
        db_files = LogSearch.get_db_files_in_range(start_dt.date(), end_dt.date())
        
        if not db_files:
            return [], 0
        
        # Converte timestamps
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        
        # Monta query base
        query = """
        SELECT 
            l.timestamp,
            ii.name as interface_in,
            io.name as interface_out,
            s.name as state,
            p.name as protocol,
            l.src_ip_priv,
            l.src_port_priv,
            l.dst_ip,
            l.dst_port,
            l.nat_ip_pub,
            l.nat_port_pub
        FROM logs l
        JOIN d_interfaces ii ON l.interface_in_id = ii.id
        JOIN d_interfaces io ON l.interface_out_id = io.id
        LEFT JOIN d_states s ON l.state_id = s.id
        JOIN d_protocols p ON l.protocol_id = p.id
        WHERE l.timestamp BETWEEN ? AND ?
        """
        
        params = [start_ts, end_ts]
        
        # Adiciona filtros dinamicamente
        if ip_privado:
            query += " AND l.src_ip_priv = ?"
            params.append(database.convert_ip_to_int(ip_privado))
        
        if port_privada:
            query += " AND l.src_port_priv = ?"
            params.append(int(port_privada))
        
        if ip_publico:
            query += " AND l.nat_ip_pub = ?"
            params.append(database.convert_ip_to_int(ip_publico))
        
        if port_publica:
            query += " AND l.nat_port_pub = ?"
            params.append(int(port_publica))
        
        if ip_destino:
            query += " AND l.dst_ip = ?"
            params.append(database.convert_ip_to_int(ip_destino))
        
        if port_destino:
            query += " AND l.dst_port = ?"
            params.append(int(port_destino))
        
        query += " ORDER BY l.timestamp DESC"
        
        # Executa busca em todos os DBs
        all_results = []
        
        for db_path in db_files:
            try:
                conn = database.get_db_connection(db_path)
                if not conn:
                    continue
                
                cursor = conn.execute(query, params)
                
                for row in cursor:
                    all_results.append({
                        'timestamp': datetime.fromtimestamp(row['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                        'interface_in': row['interface_in'],
                        'interface_out': row['interface_out'],
                        'state': row['state'] or 'N/A',
                        'protocol': row['protocol'],
                        'src_ip_priv': database.convert_int_to_ip(row['src_ip_priv']),
                        'src_port_priv': row['src_port_priv'],
                        'dst_ip': database.convert_int_to_ip(row['dst_ip']),
                        'dst_port': row['dst_port'],
                        'nat_ip_pub': database.convert_int_to_ip(row['nat_ip_pub']) if row['nat_ip_pub'] else 'N/A',
                        'nat_port_pub': row['nat_port_pub'] if row['nat_port_pub'] else 'N/A',
                    })
                
                conn.close()
                
            except Exception as e:
                print(f"⚠️ Erro ao consultar {os.path.basename(db_path)}: {e}")
        
        # Ordena por timestamp (DESC) já que juntamos vários DBs
        all_results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        total_count = len(all_results)
        
        # Aplica limite
        return all_results[:limit], total_count

# ==================== STATISTICS ====================

class LogStatistics:
    """Estatísticas dos logs"""
    
    @staticmethod
    def get_daily_summary(target_date: date = None) -> Dict:
        """Resumo diário de logs"""
        if target_date is None:
            target_date = date.today()
        
        db_path = database.get_log_db_path(target_date)
        
        if not os.path.exists(db_path):
            return {
                'date': target_date.isoformat(),
                'exists': False,
                'total_logs': 0,
                'db_size_mb': 0
            }
        
        conn = database.get_db_connection(db_path)
        if not conn:
            return {'date': target_date.isoformat(), 'exists': False}
        
        try:
            # Total de logs
            cursor = conn.execute("SELECT COUNT(*) as total FROM logs")
            total = cursor.fetchone()['total']
            
            # Stats do processador
            stats = database.get_processor_stats(conn)
            
            # Tamanho do DB
            db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
            
            conn.close()
            
            return {
                'date': target_date.isoformat(),
                'exists': True,
                'total_logs': total,
                'db_size_mb': round(db_size, 2),
                'processor_stats': stats
            }
            
        except Exception as e:
            print(f"❌ Erro ao obter stats: {e}")
            if conn:
                conn.close()
            return {'date': target_date.isoformat(), 'error': str(e)}
    
    @staticmethod
    def get_available_dates() -> List[date]:
        """Lista datas com DBs disponíveis"""
        dates = []
        
        for filename in os.listdir(config.COLD_STORAGE_DIR):
            if filename.endswith('.db'):
                try:
                    # Parse filename (YYYY-MM-DD.db)
                    date_str = filename.replace('.db', '')
                    dt = datetime.strptime(date_str, '%Y-%m-%d').date()
                    dates.append(dt)
                except ValueError:
                    continue
        
        dates.sort(reverse=True)
        return dates

# ==================== INICIALIZAÇÃO ====================

def ensure_admin_user():
    """Garante que o usuário admin existe"""
    conn = database.get_users_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (config.ADMIN_USERNAME,))
        if not cursor.fetchone():
            # Cria admin
            User.create(config.ADMIN_USERNAME, "admin123", is_admin=True)
            print(f"✅ Usuário admin criado: {config.ADMIN_USERNAME}")
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao verificar admin: {e}")
        if conn:
            conn.close()
