#!/usr/bin/env python3
# run.py
# Servidor web do MEGA LOG V2.0

from flask import Flask
from app import config
from app.routes import main_bp
from app.database import initialize_databases
from app.models import ensure_admin_user

def create_app():
    """Factory do Flask"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Configurações
    app.config['SECRET_KEY'] = config.FLASK_SECRET_KEY
    app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME
    app.config['DEBUG'] = config.DEBUG
    
    # Valida configuração
    errors = config.validate_config()
    if errors:
        print("\n⚠️ AVISOS DE CONFIGURAÇÃO:")
        for error in errors:
            print(f"   - {error}")
        print()
    
    # Inicializa bancos de dados
    print("🔧 Inicializando bancos de dados...")
    initialize_databases()
    
    # Garante que admin existe
    ensure_admin_user()
    
    # Registra blueprint
    app.register_blueprint(main_bp)
    
    print(f"✅ {config.SYSTEM_NAME} {config.SYSTEM_VERSION} inicializado")
    
    return app

# Criar instância global para Gunicorn (importação lazy)
_app_instance = None

def get_app():
    global _app_instance
    if _app_instance is None:
        _app_instance = create_app()
    return _app_instance

app = None  # Será carregado quando chamado por gunicorn

if __name__ == '__main__':
    app = create_app()
    
    print("=" * 60)
    print(f"  🚀 {config.SYSTEM_NAME} - Web Interface")
    print(f"  Versão: {config.SYSTEM_VERSION}")
    print("=" * 60)
    print()
    print("⚠️  MODO DE DESENVOLVIMENTO")
    print("   Para produção, use: gunicorn -c gunicorn_config.py run:app")
    print()
    
    # Servidor de desenvolvimento
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=config.DEBUG,
        threaded=True
    )
