# app/__init__.py
# Inicialização do módulo

__version__ = "2.0.0"
__author__ = "MEGA LOG Team"

# Importa configurações
from app import config

print(f"📦 {config.SYSTEM_NAME} {config.SYSTEM_VERSION} carregado")
