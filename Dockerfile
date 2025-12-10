FROM debian:13-slim

# Metadados
LABEL maintainer="MEGA LOG Team"
LABEL description="MEGA LOG V2.0 - Sistema Forense de Logs CGNAT"
LABEL version="2.0-STREAM"

# Variáveis de ambiente
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOME=/opt/megalog

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.13 \
    python3.13-venv \
    python3-pip \
    nginx \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário megalog
RUN useradd -r -s /bin/false -d ${APP_HOME} megalog

# Criar diretórios
RUN mkdir -p ${APP_HOME} \
    /dados1/system-log/hot \
    /dados2/system-log/cold \
    /var/log/megalog \
    /var/run/megalog

# Copiar código-fonte
COPY --chown=megalog:megalog . ${APP_HOME}/

# Criar venv e instalar dependências
RUN cd ${APP_HOME} && \
    python3.13 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Configurar permissões
RUN chown -R megalog:megalog ${APP_HOME} \
    /dados1/system-log \
    /dados2/system-log \
    /var/log/megalog \
    /var/run/megalog && \
    chmod 750 /dados1/system-log /dados2/system-log

# Criar arquivo de buffer
RUN touch /dados1/system-log/hot/hot_logs.raw && \
    chown megalog:megalog /dados1/system-log/hot/hot_logs.raw

# Copiar config Nginx
COPY docker/nginx.conf /etc/nginx/sites-available/megalog
RUN ln -sf /etc/nginx/sites-available/megalog /etc/nginx/sites-enabled/megalog && \
    rm -f /etc/nginx/sites-enabled/default && \
    mkdir -p /var/cache/nginx && \
    chown -R www-data:www-data /var/cache/nginx

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Expose ports
EXPOSE 80 443

# Copiar entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["start"]
