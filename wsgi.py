#!/usr/bin/env python3
# wsgi.py
# Wrapper WSGI para Gunicorn

import sys
import os

# Adiciona o diretório da app ao path
sys.path.insert(0, os.path.dirname(__file__))

from run import create_app

# Cria instância da aplicação
app = create_app()

if __name__ == "__main__":
    app.run()
