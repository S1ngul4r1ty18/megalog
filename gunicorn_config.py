# gunicorn_config.py
# Configuração do Gunicorn para produção

import multiprocessing
import os

# Bind
bind = "127.0.0.1:5000"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000

# Timeouts
timeout = 120
keepalive = 5

# Daemon
daemon = False
pidfile = None

# Logging
accesslog = "/var/log/megalog/access.log"
errorlog = "/var/log/megalog/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "megalog_web"

# Server mechanics
preload_app = True
reload = False

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

def on_starting(server):
    """Callback ao iniciar"""
    print("🚀 Gunicorn iniciando...")

def when_ready(server):
    """Callback quando pronto"""
    print("✅ Gunicorn pronto para aceitar conexões")

def on_exit(server):
    """Callback ao sair"""
    print("🛑 Gunicorn encerrado")
