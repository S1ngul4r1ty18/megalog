# app/routes.py
# Rotas web do MEGA LOG V2.0

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from datetime import datetime, timedelta
from app import config
from app.models import User, AuditLog, LogSearch, LogStatistics, ensure_admin_user
from app.database import get_current_log_db_connection, get_processor_stats, get_log_db_path
import psutil
import os

main_bp = Blueprint('main', __name__)

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
        
        # Stats do processador
        conn = get_current_log_db_connection()
        processor_stats = {}
        if conn:
            processor_stats = get_processor_stats(conn)
            conn.close()
        
        return jsonify({
            'cpu_per_core': cpu_per_core,
            'ram': round(ram, 1),
            'disk_hot': disk_hot_data,
            'disk_cold': disk_cold_data,
            'buffer_size_mb': round(buffer_size_mb, 2),
            'processor_stats': processor_stats
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
            search_params.update(request.args.to_dict())
        
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
