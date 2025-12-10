# app/routes.py
# Rotas web do MEGA LOG V2.0

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from datetime import datetime, timedelta
from app import config
from app.models import User, AuditLog, LogSearch, LogStatistics, ensure_admin_user
from app.database import get_current_log_db_connection, get_processor_stats, get_log_db_path, get_db_connection
import psutil
import os
import requests
from functools import lru_cache

main_bp = Blueprint('main', __name__)

# ==================== MAXMIND GEOIP ====================
# Carrega MaxMind GeoIP2 ASN database (se disponível)
_asn_reader = None
_maxmind_available = False

try:
    import geoip2.database
    import geoip2.errors

    GEOIP_DB_PATH = '/opt/megalog/geoip/GeoLite2-ASN.mmdb'
    if os.path.exists(GEOIP_DB_PATH):
        _asn_reader = geoip2.database.Reader(GEOIP_DB_PATH)
        _maxmind_available = True
        print(f"✅ MaxMind GeoLite2-ASN carregado de {GEOIP_DB_PATH}")
    else:
        print(f"⚠️ MaxMind database não encontrado em {GEOIP_DB_PATH}")
        print(f"   Usando fallback para API ipapi.co")
except ImportError:
    print("⚠️ Biblioteca geoip2 não instalada. Usando fallback para API ipapi.co")
except Exception as e:
    print(f"⚠️ Erro ao carregar MaxMind database: {e}")
    print(f"   Usando fallback para API ipapi.co")

# Cache para lookups de ASN (evita chamadas repetidas)
@lru_cache(maxsize=10000)  # Aumentado para 10k já que é lookup local
def get_ip_asn_info(ip_address):
    """
    Busca informação de ASN para um IP
    Prioridade: 1) MaxMind local, 2) API ipapi.co (fallback)
    Retorna dict com 'asn' e 'org' ou None em caso de erro
    """
    try:
        # Verifica se é IP privado (RFC1918, loopback, etc)
        octets = [int(x) for x in ip_address.split('.')]
        is_private = (
            octets[0] == 10 or  # 10.0.0.0/8
            (octets[0] == 172 and 16 <= octets[1] <= 31) or  # 172.16.0.0/12
            (octets[0] == 192 and octets[1] == 168) or  # 192.168.0.0/16
            octets[0] == 127 or  # 127.0.0.0/8 (loopback)
            octets[0] == 0  # 0.0.0.0/8
        )

        if is_private:
            return {
                'asn': 'Privado',
                'org': 'Rede Privada (RFC1918)',
                'country': 'Local',
                'source': 'local'
            }

        # OPÇÃO 1: Usa MaxMind GeoLite2-ASN (local, rápido, ilimitado)
        if _maxmind_available and _asn_reader:
            try:
                response = _asn_reader.asn(ip_address)
                asn_number = response.autonomous_system_number
                asn_org = response.autonomous_system_organization or 'N/A'

                return {
                    'asn': f'AS{asn_number}' if asn_number else 'N/A',
                    'org': asn_org,
                    'country': 'N/A',  # ASN DB não tem país
                    'source': 'maxmind'
                }
            except geoip2.errors.AddressNotFoundError:
                # IP não encontrado no database (normal para alguns IPs)
                return {
                    'asn': 'N/A',
                    'org': 'IP não catalogado',
                    'country': 'N/A',
                    'source': 'maxmind'
                }
            except Exception as e:
                print(f"[WARNING] Erro MaxMind para {ip_address}: {e}")
                # Continua para fallback API

        # OPÇÃO 2: Fallback para API ipapi.co (online, limitado)
        response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=2)
        if response.status_code == 200:
            data = response.json()
            # Verifica se retornou erro de rate limit
            if data.get('error'):
                return {
                    'asn': 'Limite API',
                    'org': 'Rate limit atingido - instale MaxMind',
                    'country': 'N/A',
                    'source': 'api-error'
                }
            return {
                'asn': data.get('asn', 'N/A'),
                'org': data.get('org', 'N/A'),
                'country': data.get('country_name', 'N/A'),
                'source': 'api'
            }
        elif response.status_code == 429:
            return {
                'asn': 'Limite API',
                'org': 'Rate limit atingido (1000 req/dia)',
                'country': 'N/A',
                'source': 'api-error'
            }
    except Exception as e:
        print(f"[WARNING] Erro ao buscar ASN para {ip_address}: {e}")

    return None

# ==================== DECORATORS ====================

def login_required(f):
    """Requer login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para continuar.', 'danger')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Requer privilégios de admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para continuar.', 'danger')
            return redirect(url_for('main.login'))
        
        user = User.get_by_id(session['user_id'])
        if not user or not user.is_admin:
            flash('Acesso negado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Retorna usuário logado"""
    if 'user_id' in session:
        return User.get_by_id(session['user_id'])
    return None

# ==================== AUTH ROUTES ====================

@main_bp.route('/')
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.authenticate(username, password)
        
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            session.permanent = True
            
            # Log de auditoria
            AuditLog.log_action(user.id, user.username, 'LOGIN', 
                              ip_address=request.remote_addr)
            
            flash(f'Bem-vindo, {user.username}!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Credenciais inválidas.', 'danger')
    
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    """Logout"""
    user = get_current_user()
    if user:
        AuditLog.log_action(user.id, user.username, 'LOGOUT',
                          ip_address=request.remote_addr)
    
    session.clear()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('main.login'))

# ==================== DASHBOARD ====================

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal"""
    user = get_current_user()
    
    # Estatísticas estáticas (carregadas uma vez)
    today_stats = LogStatistics.get_daily_summary()
    available_dates = LogStatistics.get_available_dates()[:7]  # Últimos 7 dias
    
    return render_template('dashboard.html',
                         user=user,
                         today_stats=today_stats,
                         available_dates=available_dates)

@main_bp.route('/api/system-status')
@login_required
def api_system_status():
    """API de status do sistema em tempo real"""
    try:
        # CPU por núcleo
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)

        # RAM
        ram = psutil.virtual_memory().percent

        # Disco HOT
        try:
            disk_hot = psutil.disk_usage(config.HOT_STORAGE_DIR)
            disk_hot_data = {
                'percent': round(disk_hot.percent, 1),
                'used_gb': round(disk_hot.used / (1024**3), 2),
                'total_gb': round(disk_hot.total / (1024**3), 2)
            }
        except Exception:
            disk_hot_data = {'percent': 0, 'used_gb': 0, 'total_gb': 0}

        # Disco COLD
        try:
            disk_cold = psutil.disk_usage(config.COLD_STORAGE_DIR)
            disk_cold_data = {
                'percent': round(disk_cold.percent, 1),
                'used_gb': round(disk_cold.used / (1024**3), 2),
                'total_gb': round(disk_cold.total / (1024**3), 2)
            }
        except Exception:
            disk_cold_data = {'percent': 0, 'used_gb': 0, 'total_gb': 0}

        # Buffer HOT size
        buffer_size_mb = 0
        if os.path.exists(config.HOT_LOG_BUFFER_FILE):
            buffer_size_mb = os.path.getsize(config.HOT_LOG_BUFFER_FILE) / (1024**2)

        # Stats do processador e logs de hoje
        conn = get_current_log_db_connection()
        processor_stats = {}
        today_stats = {'total_logs': 0, 'db_size_mb': 0}

        if conn:
            processor_stats = get_processor_stats(conn)

            # Estatísticas de logs de hoje
            from app.models import LogStatistics
            daily_summary = LogStatistics.get_daily_summary()
            today_stats = {
                'total_logs': daily_summary.get('total_logs', 0),
                'db_size_mb': daily_summary.get('db_size_mb', 0)
            }

            conn.close()

        return jsonify({
            'cpu_per_core': cpu_per_core,
            'ram': round(ram, 1),
            'disk_hot': disk_hot_data,
            'disk_cold': disk_cold_data,
            'buffer_size_mb': round(buffer_size_mb, 2),
            'processor_stats': processor_stats,
            'today_stats': today_stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== FORENSIC SEARCH ====================

@main_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search_forensics():
    """Busca forense avançada com paginação"""
    user = get_current_user()
    results = None
    total_count = 0
    page = int(request.args.get('page', 1))
    per_page = 100  # Registros por página

    # Parâmetros padrão
    search_params = {
        'date_inicio': datetime.now().strftime('%Y-%m-%d'),
        'hora_inicio': '00:00:00',
        'date_fim': datetime.now().strftime('%Y-%m-%d'),
        'hora_fim': '23:59:59',
        'ip_privado': '',
        'port_privada': '',
        'ip_publico': '',
        'port_publica': '',
        'ip_destino': '',
        'port_destino': ''
    }

    if request.method == 'POST' or request.args.get('search_submitted'):
        # Se POST, usa form. Se GET com paginação, usa query string
        if request.method == 'POST':
            search_params.update(request.form.to_dict())
        else:
            # Filtra apenas os parâmetros de busca válidos do query string
            for key in search_params.keys():
                if request.args.get(key):
                    search_params[key] = request.args.get(key)
        
        try:
            # Parse de datas
            start_dt = datetime.strptime(
                f"{search_params['date_inicio']} {search_params['hora_inicio']}",
                '%Y-%m-%d %H:%M:%S'
            )
            end_dt = datetime.strptime(
                f"{search_params['date_fim']} {search_params['hora_fim']}",
                '%Y-%m-%d %H:%M:%S'
            )
            
            if start_dt > end_dt:
                flash('Data/hora de início não pode ser maior que a de fim.', 'danger')
                return render_template('search_forensics.html', 
                                     results=results, 
                                     params=search_params,
                                     total_count=0,
                                     page=page,
                                     total_pages=0)
            
            # Executa busca (sem limite, pegamos tudo)
            all_results, total_count = LogSearch.search(
                start_dt=start_dt,
                end_dt=end_dt,
                ip_privado=search_params['ip_privado'].strip() or None,
                port_privada=search_params['port_privada'].strip() or None,
                ip_publico=search_params['ip_publico'].strip() or None,
                port_publica=search_params['port_publica'].strip() or None,
                ip_destino=search_params['ip_destino'].strip() or None,
                port_destino=search_params['port_destino'].strip() or None,
                limit=10000,  # Limite alto para pegar todos
                user_id=user.id,
                username=user.username,
                ip_address=request.remote_addr
            )
            
            # Calcula paginação
            total_pages = (total_count + per_page - 1) // per_page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            results = all_results[start_idx:end_idx]
            
            if total_count > 0:
                flash(f'{total_count} registros encontrados. Página {page} de {total_pages}.', 'success')
            else:
                flash('Nenhum registro encontrado para os critérios informados.', 'info')
                
        except ValueError as e:
            flash(f'Erro no formato de data/hora: {e}', 'danger')
        except Exception as e:
            flash(f'Erro ao executar busca: {e}', 'danger')
    
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0
    
    return render_template('search_forensics.html',
                         results=results,
                         params=search_params,
                         total_count=total_count,
                         page=page,
                         total_pages=total_pages,
                         per_page=per_page)

@main_bp.route('/export-results', methods=['POST'])
@login_required
def export_results():
    """Exporta resultados em CSV"""
    import csv
    from io import StringIO
    from flask import make_response
    
    # Recebe dados do form (JSON)
    import json
    results = json.loads(request.form.get('results', '[]'))
    
    if not results:
        flash('Nenhum resultado para exportar.', 'warning')
        return redirect(url_for('main.search_forensics'))
    
    # Cria CSV
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)
    
    # Log de auditoria
    user = get_current_user()
    AuditLog.log_action(user.id, user.username, 'EXPORTACAO',
                       f'{len(results)} registros exportados',
                       request.remote_addr)
    
    # Retorna CSV
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=logs_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response.headers['Content-Type'] = 'text/csv'
    
    return response

# ==================== DAILY LOGS ====================

@main_bp.route('/logs-daily')
@login_required
def logs_daily():
    """Visualização de logs diários"""
    available_dates = LogStatistics.get_available_dates()

    selected_date_str = request.args.get('date')
    logs_summary = None

    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            logs_summary = LogStatistics.get_daily_summary(selected_date)
        except ValueError:
            flash('Data inválida.', 'danger')

    return render_template('logs_daily.html',
                         available_dates=available_dates,
                         selected_date=selected_date_str,
                         logs_summary=logs_summary)

@main_bp.route('/api/daily-charts/<date_str>')
@login_required
def api_daily_charts(date_str):
    """API para dados de gráficos diários"""
    try:
        print(f"[DEBUG] Charts API chamada para data: {date_str}")
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        db_path = get_log_db_path(selected_date)
        print(f"[DEBUG] Caminho do banco: {db_path}")

        if not os.path.exists(db_path):
            print(f"[ERROR] Banco não encontrado: {db_path}")
            return jsonify({'error': 'Banco de dados não encontrado'}), 404

        conn = get_db_connection(db_path)
        if not conn:
            print(f"[ERROR] Erro ao conectar ao banco")
            return jsonify({'error': 'Erro ao conectar ao banco'}), 500

        # Gráfico de Protocolos
        cursor = conn.execute("""
            SELECT d.name as protocol, COUNT(*) as count
            FROM logs l
            JOIN d_protocols d ON l.protocol_id = d.id
            GROUP BY l.protocol_id
            ORDER BY count DESC
            LIMIT 10
        """)
        protocols = [{'name': row['protocol'], 'count': row['count']} for row in cursor.fetchall()]

        # Gráfico de Interfaces (origem)
        cursor = conn.execute("""
            SELECT d.name as interface, COUNT(*) as count
            FROM logs l
            JOIN d_interfaces d ON l.interface_in_id = d.id
            GROUP BY l.interface_in_id
            ORDER BY count DESC
            LIMIT 10
        """)
        interfaces = [{'name': row['interface'], 'count': row['count']} for row in cursor.fetchall()]

        # Timeline (logs por hora)
        cursor = conn.execute("""
            SELECT
                strftime('%H:00', datetime(timestamp, 'unixepoch', 'localtime')) as hour,
                COUNT(*) as count
            FROM logs
            GROUP BY hour
            ORDER BY hour
        """)
        timeline = [{'hour': row['hour'], 'count': row['count']} for row in cursor.fetchall()]

        # Top IPs Públicos (NAT)
        cursor = conn.execute("""
            SELECT
                CASE
                    WHEN nat_ip_pub IS NOT NULL THEN
                        printf('%d.%d.%d.%d',
                            (nat_ip_pub >> 24) & 255,
                            (nat_ip_pub >> 16) & 255,
                            (nat_ip_pub >> 8) & 255,
                            nat_ip_pub & 255)
                    ELSE 'N/A'
                END as ip,
                COUNT(*) as count
            FROM logs
            WHERE nat_ip_pub IS NOT NULL
            GROUP BY nat_ip_pub
            ORDER BY count DESC
            LIMIT 10
        """)
        top_ips = [{'ip': row['ip'], 'count': row['count']} for row in cursor.fetchall()]

        # Top IPs de Destino (mais acessados) com informação de ASN
        # Filtra apenas IPs públicos (não RFC1918)
        cursor = conn.execute("""
            SELECT
                CASE
                    WHEN dst_ip IS NOT NULL THEN
                        printf('%d.%d.%d.%d',
                            (dst_ip >> 24) & 255,
                            (dst_ip >> 16) & 255,
                            (dst_ip >> 8) & 255,
                            dst_ip & 255)
                    ELSE 'N/A'
                END as ip,
                COUNT(*) as count
            FROM logs
            WHERE dst_ip IS NOT NULL
                -- Filtra IPs privados RFC1918
                AND NOT ((dst_ip >> 24) & 255 = 10)  -- 10.0.0.0/8
                AND NOT (((dst_ip >> 24) & 255 = 172) AND (((dst_ip >> 16) & 255) BETWEEN 16 AND 31))  -- 172.16.0.0/12
                AND NOT (((dst_ip >> 24) & 255 = 192) AND (((dst_ip >> 16) & 255) = 168))  -- 192.168.0.0/16
                AND NOT ((dst_ip >> 24) & 255 = 127)  -- 127.0.0.0/8 (loopback)
                AND NOT ((dst_ip >> 24) & 255 = 0)  -- 0.0.0.0/8
            GROUP BY dst_ip
            ORDER BY count DESC
            LIMIT 10
        """)

        # Enriquece com informação de ASN (limitado aos top 10 para não sobrecarregar API)
        top_dst_ips = []
        for row in cursor.fetchall():
            ip = row['ip']
            asn_info = get_ip_asn_info(ip)
            top_dst_ips.append({
                'ip': ip,
                'count': row['count'],
                'asn': asn_info['asn'] if asn_info else 'N/A',
                'org': asn_info['org'] if asn_info else 'N/A',
                'country': asn_info['country'] if asn_info else 'N/A'
            })

        conn.close()

        print(f"[DEBUG] Dados gerados - Protocolos: {len(protocols)}, Interfaces: {len(interfaces)}, Timeline: {len(timeline)}, Top IPs NAT: {len(top_ips)}, Top IPs Destino: {len(top_dst_ips)}")

        return jsonify({
            'protocols': protocols,
            'interfaces': interfaces,
            'timeline': timeline,
            'top_ips': top_ips,
            'top_dst_ips': top_dst_ips
        })

    except Exception as e:
        print(f"[ERROR] Exceção na API de gráficos: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== ADMIN ROUTES ====================

@main_bp.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def admin_users():
    """Gerenciamento de usuários"""
    user = get_current_user()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            is_admin = request.form.get('is_admin') == 'on'
            
            if not username or not password:
                flash('Username e senha são obrigatórios.', 'danger')
            elif User.create(username, password, is_admin):
                AuditLog.log_action(user.id, user.username, 'USER_CREATE',
                                  f'Criado usuário: {username}',
                                  request.remote_addr)
                flash(f'Usuário "{username}" criado com sucesso!', 'success')
            else:
                flash(f'Erro ao criar usuário "{username}". Talvez já exista.', 'danger')
        
        elif action == 'delete':
            user_id = request.form.get('user_id')
            target_user = User.get_by_id(user_id)
            
            if target_user and target_user.username == config.ADMIN_USERNAME:
                flash('Não é possível deletar o super admin.', 'danger')
            elif target_user and User.delete(user_id):
                AuditLog.log_action(user.id, user.username, 'USER_DELETE',
                                  f'Deletado usuário: {target_user.username}',
                                  request.remote_addr)
                flash(f'Usuário "{target_user.username}" deletado.', 'success')
            else:
                flash('Erro ao deletar usuário.', 'danger')
        
        elif action == 'reset_password':
            user_id = request.form.get('user_id')
            new_password = request.form.get('new_password', '').strip()
            target_user = User.get_by_id(user_id)
            
            if not new_password:
                flash('Nova senha não pode ser vazia.', 'danger')
            elif target_user and User.update_password(user_id, new_password):
                AuditLog.log_action(user.id, user.username, 'PASSWORD_RESET',
                                  f'Senha resetada para: {target_user.username}',
                                  request.remote_addr)
                flash(f'Senha de "{target_user.username}" atualizada.', 'success')
            else:
                flash('Erro ao atualizar senha.', 'danger')
        
        return redirect(url_for('main.admin_users'))
    
    users = User.get_all()
    return render_template('admin_users.html', users=users)

@main_bp.route('/admin/audit-log')
@admin_required
def admin_audit_log():
    """Log de auditoria"""
    logs = AuditLog.get_recent(limit=200)
    return render_template('audit_log.html', logs=logs)

# ==================== PROFILE ====================

@main_bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Alterar própria senha"""
    user = get_current_user()
    
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '').strip()
        
        # Valida senha antiga
        if not User.authenticate(user.username, old_password):
            flash('Senha antiga incorreta.', 'danger')
        elif not new_password:
            flash('Nova senha não pode ser vazia.', 'danger')
        elif User.update_password(user.id, new_password):
            AuditLog.log_action(user.id, user.username, 'PASSWORD_CHANGE',
                              'Usuário alterou própria senha',
                              request.remote_addr)
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Erro ao alterar senha.', 'danger')
    
    return render_template('change_password.html', user=user)

# ==================== HEALTHCHECK ====================

@main_bp.route('/health')
def health():
    """Endpoint de healthcheck"""
    try:
        # Verifica DB de usuários
        conn_users = User.get_by_id(1)
        
        # Verifica DB de logs
        conn_logs = get_current_log_db_connection()
        if conn_logs:
            conn_logs.close()
        
        # Verifica buffer
        buffer_exists = os.path.exists(config.HOT_LOG_BUFFER_FILE)
        
        return jsonify({
            'status': 'healthy',
            'version': config.SYSTEM_VERSION,
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'users_db': True,
                'logs_db': conn_logs is not None,
                'buffer': buffer_exists
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# ==================== CONTEXT PROCESSOR ====================

@main_bp.app_context_processor
def inject_globals():
    """Injeta variáveis globais nos templates"""
    return {
        'system_name': config.SYSTEM_NAME,
        'system_version': config.SYSTEM_VERSION,
        'current_user': get_current_user()
    }
