# app/config.py
# Configurações centralizadas do MEGA LOG V2.0

import os
from datetime import timedelta
from werkzeug.security import generate_password_hash

# ==================== PATHS ====================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Armazenamento HOT (SSD) - Buffer de entrada
HOT_STORAGE_DIR = "/dados1/system-log/hot"
HOT_LOG_BUFFER_FILE = os.path.join(HOT_STORAGE_DIR, "hot_logs.raw")

# Armazenamento COLD (HD) - Logs processados
COLD_STORAGE_DIR = "/dados2/system-log/cold"

# Banco de dados de usuários (único, permanente)
USERS_DB_PATH = os.path.join(BASE_DIR, "users.db")

# Formato de nome do banco de logs (por dia)
LOG_DB_FILENAME_FORMAT = "%Y-%m-%d.db"  # Ex: 2025-12-02.db

# Arquivo de offset do Pygtail (controle de leitura)
PROCESSOR_OFFSET_FILE = os.path.join(COLD_STORAGE_DIR, ".processor.offset")

# ==================== INICIALIZAÇÃO ====================
# Garantir que diretórios existam (executado na inicialização)
os.makedirs(HOT_STORAGE_DIR, exist_ok=True)
os.makedirs(COLD_STORAGE_DIR, exist_ok=True)

# ==================== FLASK ====================
# IMPORTANTE: Trocar em produção!
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or \
    "6806f13715f7999ba9726f66e15c5498324b269c6422ee1f29241dfe55e481ddcd9e2e7676e307cba1a58c5a214249b713836f080d88e43ff1a0e85c7254850e"

DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

# ==================== WHITE LABEL ====================
SYSTEM_NAME = "MEGA LOG V2"
SYSTEM_VERSION = "V2.0-STREAM"

# ==================== ADMIN ====================
ADMIN_USERNAME = "superadmin"
# Senha padrão: "admin123" - TROQUE ANTES DE COLOCAR EM PRODUÇÃO!
ADMIN_PASSWORD_HASH = generate_password_hash("admin123", method='pbkdf2:sha256:600000')

# ==================== PROCESSADOR ====================
# Quantas linhas processar antes de salvar no DB
BATCH_SIZE = 500

# Tempo máximo antes de salvar lote incompleto (segundos)
BATCH_TIMEOUT_SEC = 10

# Filtros de ruído (logs que NÃO serão salvos)
NOISE_FILTERS = [
    '->10.10.10.10:53',  # DNS interno
    '->8.8.8.8:53',      # Google DNS (opcional)
]

# ==================== PERFORMANCE ====================
# Timeout de conexão SQLite
DB_TIMEOUT = 30.0

# Modo de journal SQLite (WAL = melhor concorrência)
DB_JOURNAL_MODE = "WAL"

# Sincronização (NORMAL = mais rápido, FULL = mais seguro)
DB_SYNCHRONOUS = "NORMAL"

# ==================== RETENÇÃO ====================
# Dias para manter logs (0 = infinito)
LOG_RETENTION_DAYS = 365

# ==================== AUDITORIA ====================
# Habilitar log de consultas forenses
ENABLE_AUDIT_LOG = True

# ==================== ALERTAS ====================
# Email para alertas (deixe vazio para desabilitar)
ALERT_EMAIL = ""

# Webhook para alertas (Slack, Discord, etc)
ALERT_WEBHOOK_URL = ""

# ==================== VALIDAÇÃO ====================
def validate_config():
    """Valida configurações críticas na inicialização"""
    errors = []
    
    if not os.path.exists(HOT_STORAGE_DIR):
        errors.append(f"Diretório HOT não existe: {HOT_STORAGE_DIR}")
    
    if not os.path.exists(COLD_STORAGE_DIR):
        errors.append(f"Diretório COLD não existe: {COLD_STORAGE_DIR}")
    
    if not os.access(HOT_STORAGE_DIR, os.W_OK):
        errors.append(f"Sem permissão de escrita em: {HOT_STORAGE_DIR}")
    
    if not os.access(COLD_STORAGE_DIR, os.W_OK):
        errors.append(f"Sem permissão de escrita em: {COLD_STORAGE_DIR}")
    
    if DEBUG and "prod" in os.environ.get('ENVIRONMENT', '').lower():
        errors.append("DEBUG=True em ambiente de produção!")
    
    if FLASK_SECRET_KEY.startswith("6806f137") and not DEBUG:
        errors.append("FLASK_SECRET_KEY padrão em produção! Defina variável de ambiente.")
    
    return errors

if __name__ == "__main__":
    # Teste de configuração
    errors = validate_config()
    if errors:
        print("❌ ERROS DE CONFIGURAÇÃO:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Configuração válida!")
        print(f"  - HOT Storage: {HOT_STORAGE_DIR}")
        print(f"  - COLD Storage: {COLD_STORAGE_DIR}")
        print(f"  - Users DB: {USERS_DB_PATH}")
        print(f"  - Batch Size: {BATCH_SIZE}")
        print(f"  - Debug Mode: {DEBUG}")
