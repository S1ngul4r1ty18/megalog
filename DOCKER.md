# MEGA LOG V2.0 - Docker Deployment Guide

## 🐳 Container Docker

### Pré-requisitos

- Docker >= 20.10
- Docker Compose >= 2.0 (opcional)

### Opção 1: Docker Compose (Recomendado)

#### 1. Build
```bash
docker-compose build
```

#### 2. Iniciar
```bash
docker-compose up -d
```

#### 3. Verificar
```bash
docker-compose ps
docker-compose logs -f megalog
```

#### 4. Parar
```bash
docker-compose down
```

---

### Opção 2: Docker Manual

#### 1. Build
```bash
docker build -t megalog:v2.0 -f Dockerfile .
```

#### 2. Criar volumes (dados persistentes)
```bash
docker volume create megalog-hot
docker volume create megalog-cold
docker volume create megalog-logs
```

#### 3. Iniciar container
```bash
docker run -d \
  --name megalog \
  -p 80:80 \
  -p 443:443 \
  -v megalog-hot:/dados1/system-log/hot \
  -v megalog-cold:/dados2/system-log/cold \
  -v megalog-logs:/var/log/megalog \
  -e FLASK_ENV=production \
  -e PYTHONUNBUFFERED=1 \
  --restart unless-stopped \
  megalog:v2.0
```

#### 4. Verificar
```bash
docker ps | grep megalog
docker logs -f megalog
curl http://localhost/health
```

---

## 📁 Volumes & Persistência

### Dados HOT (Buffer de entrada)
```
-v /seu/caminho/hot:/dados1/system-log/hot
```

### Dados COLD (Banco de dados)
```
-v /seu/caminho/cold:/dados2/system-log/cold
```

### Logs da aplicação
```
-v /seu/caminho/logs:/var/log/megalog
```

---

## 🔐 Variáveis de Ambiente

```bash
# Arquivo .env
FLASK_ENV=production
FLASK_SECRET_KEY=sua_chave_segura_aqui
PYTHONUNBUFFERED=1
```

---

## 🌐 Acesso

- **URL**: http://localhost/login
- **Usuário**: superadmin
- **Senha**: admin123
- **Health**: http://localhost/health

---

## 📊 Containerização com Docker Compose

### Estrutura Completa (com Processador separado)

```yaml
# docker-compose.yml fornecido já inclui:
# - Serviço Web (Gunicorn + Nginx)
# - Serviço Processor (24/7)
# - Volumes persistentes
# - Health checks
# - Network isolada
```

### Iniciar apenas Web
```bash
docker-compose up -d megalog
```

### Iniciar com Processor
```bash
docker-compose up -d
```

### Ver logs
```bash
docker-compose logs -f
docker-compose logs -f megalog
docker-compose logs -f processor
```

---

## 🔧 Operações Comuns

### Acessar shell do container
```bash
docker exec -it megalog /bin/bash
```

### Reiniciar
```bash
docker restart megalog
```

### Remover
```bash
docker-compose down -v  # Remove também volumes
docker rm megalog
```

### Ver recursos
```bash
docker stats megalog
```

---

## 🚀 Deploy em Produção

### 1. Build otimizado
```bash
docker build -t megalog:v2.0 \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -f Dockerfile .
```

### 2. Push para registry
```bash
docker tag megalog:v2.0 seu-registry/megalog:v2.0
docker push seu-registry/megalog:v2.0
```

### 3. Docker Swarm
```bash
docker stack deploy -c docker-compose.yml megalog
```

### 4. Kubernetes (Helm)
```bash
# Ver helm-chart/ para templates K8s
helm install megalog ./helm-chart/
```

---

## 📈 Performance Tuning

### Limitar recursos
```bash
docker run -d \
  --memory="2g" \
  --cpus="2" \
  megalog:v2.0
```

### Log rotation
```bash
docker run -d \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  megalog:v2.0
```

---

## 🔍 Troubleshooting

### Container não inicia
```bash
docker logs megalog
docker inspect megalog
```

### Sem acesso a /dados1 e /dados2
```bash
# Verificar volumes
docker volume ls | grep megalog

# Remount se necessário
docker run -v /seu/path/hot:/dados1/system-log/hot ...
```

### Porta já em uso
```bash
docker run -p 8080:80 megalog:v2.0  # Use porta diferente
```

---

## 📊 Monitoramento

### Prometheus (opcional)
```bash
# Adicionar a docker-compose.yml:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

### Observabilidade
```bash
# Logs estruturados
docker logs --timestamps megalog

# Métricas
docker stats megalog
```

---

## ✨ Recursos Finais

- **Imagem base**: Debian 13 slim (~150MB)
- **Tamanho final**: ~600-800MB (com dependências)
- **Startup**: ~5-10 segundos
- **Memory footprint**: ~200-400MB em repouso
- **Escalabilidade**: Pronto para Docker Swarm/Kubernetes

---

## 🎯 Próximas Etapas

1. [ ] Customizar Dockerfile se necessário
2. [ ] Build da imagem
3. [ ] Push para seu registry
4. [ ] Deploy em produção
5. [ ] Monitorar performance
