# MEGA LOG V2.0 - Kubernetes Deployment Guide

## 📋 Índice
1. [Pré-requisitos](#pré-requisitos)
2. [Deploy Básico](#deploy-básico)
3. [Configurações Avançadas](#configurações-avançadas)
4. [Monitoramento](#monitoramento)
5. [Troubleshooting](#troubleshooting)
6. [Escalabilidade](#escalabilidade)

## Pré-requisitos

### Sistema
- Kubernetes 1.24+
- Docker registry com as imagens `megalog:v2.0` e `megalog-processor:v2.0`
- 10GB de espaço em disco (mínimo)
- 4GB RAM (mínimo)

### Ferramentas
```bash
# Instalar kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# Instalar helm (opcional, para charts)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Deploy Básico

### 1. Push das imagens para registry

```bash
# Login no Docker Hub ou registry privado
docker login

# Tag das imagens
docker tag megalog:v2.0 seu-usuario/megalog:v2.0
docker tag megalog-processor:v2.0 seu-usuario/megalog-processor:v2.0

# Push
docker push seu-usuario/megalog:v2.0
docker push seu-usuario/megalog-processor:v2.0
```

### 2. Ajustar referências no YAML

```bash
# Editar kubernetes-deployment.yaml e alterar:
# - megalog:v2.0 → seu-usuario/megalog:v2.0
# - megalog-processor:v2.0 → seu-usuario/megalog-processor:v2.0

sed -i 's|megalog:v2.0|seu-usuario/megalog:v2.0|g' kubernetes-deployment.yaml
sed -i 's|megalog-processor:v2.0|seu-usuario/megalog-processor:v2.0|g' kubernetes-deployment.yaml
```

### 3. Deploy inicial

```bash
# Aplicar manifesto
kubectl apply -f kubernetes-deployment.yaml

# Verificar status
kubectl get pods -o wide
kubectl describe pod megalog-web-xxxxx

# Aguardar rollout
kubectl rollout status deployment/megalog-web
kubectl rollout status deployment/megalog-processor
```

### 4. Verificar acesso

```bash
# Port-forward local
kubectl port-forward svc/megalog 8080:80

# Acessar
# http://localhost:8080/login
# User: superadmin
# Pass: admin123
```

## Configurações Avançadas

### 1. Namespace Dedicado

```bash
# Criar namespace
kubectl create namespace megalog
kubectl label namespace megalog monitoring=true

# Alterar manifesto
sed -i 's|namespace: default|namespace: megalog|g' kubernetes-deployment.yaml

# Deploy no namespace
kubectl apply -f kubernetes-deployment.yaml -n megalog
```

### 2. Image Pull Secrets (Private Registry)

```bash
# Criar secret
kubectl create secret docker-registry megalog-registry \
  --docker-server=seu-registry.com \
  --docker-username=usuario \
  --docker-password=senha

# Adicionar ao manifesto (antes de spec.containers):
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: megalog-web
spec:
  template:
    spec:
      imagePullSecrets:
      - name: megalog-registry
      containers:
      - ...
```

### 3. Persistent Storage com NFS

```bash
# ConfigMap com NFS
apiVersion: v1
kind: PersistentVolume
metadata:
  name: megalog-nfs-pv
spec:
  capacity:
    storage: 500Gi
  accessModes:
    - ReadWriteMany
  nfs:
    server: nfs-server.example.com
    path: "/exports/megalog"
  persistentVolumeReclaimPolicy: Retain
```

### 4. Ingress com HTTPS

```bash
# Instalar cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Ingress manifest
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: megalog
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - megalog.example.com
    secretName: megalog-tls
  rules:
  - host: megalog.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: megalog
            port:
              number: 80

# ClusterIssuer para Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

### 5. Resource Quotas

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: megalog-quota
  namespace: megalog
spec:
  hard:
    requests.cpu: "10"
    requests.memory: "20Gi"
    limits.cpu: "20"
    limits.memory: "40Gi"
    pods: "20"
  scopeSelector:
    matchExpressions:
    - operator: In
      scopeName: PriorityClass
      values: ["high", "medium"]
```

## Monitoramento

### 1. Prometheus + Grafana

```bash
# Adicionar helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Instalar
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# Adicionar Service Monitor ao manifesto
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: megalog
spec:
  selector:
    matchLabels:
      app: megalog
  endpoints:
  - port: http
    interval: 30s
    path: /metrics
```

### 2. Logs com ELK

```bash
# Instalar Fluent Bit
helm repo add fluent https://fluent.github.io/helm-charts
helm install fluent-bit fluent/fluent-bit -n logging --create-namespace

# Configuração no helm values
config:
  service: |
    [SERVICE]
        Flush        10
        Daemon       Off
        Log_Level    info
  
  inputs: |
    [INPUT]
        Name              tail
        Path              /var/log/megalog/access.log
        Tag               megalog.*
        Read_from_Head    On
        DB                /var/log/fluent-bit-state.db
```

### 3. Alertas

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: megalog-alerts
spec:
  groups:
  - name: megalog
    interval: 30s
    rules:
    - alert: MegalogDown
      expr: up{job="megalog"} == 0
      for: 5m
      annotations:
        summary: "Megalog está down"
        description: "Megalog não responde há 5 minutos"
    
    - alert: HighMemory
      expr: container_memory_usage_bytes{pod=~"megalog-.*"} > 1.5e9
      for: 2m
      annotations:
        summary: "Alto uso de memória"
        description: "Megalog usando {{ $value | humanize }}B"
    
    - alert: HighCPU
      expr: rate(container_cpu_usage_seconds_total{pod=~"megalog-.*"}[5m]) > 0.8
      for: 3m
      annotations:
        summary: "Alto uso de CPU"
```

## Troubleshooting

### Pods em Pending
```bash
# Verificar eventos
kubectl describe node
kubectl describe pvc megalog-hot-pvc

# Soluções:
# 1. Aumentar espaço em disco
# 2. Ajustar requests/limits
# 3. Criar PVs manualmente
```

### Falha no Health Check
```bash
# Verificar logs
kubectl logs -f deployment/megalog-web

# Testar endpoint
kubectl exec -it pod/megalog-web-xxxxx -- curl http://localhost/health

# Aumentar initialDelaySeconds em livenessProbe
```

### Database Lock
```bash
# WAL mode ativo?
kubectl exec -it pod/megalog-web-xxxxx -- \
  sqlite3 /dados2/system-log/cold/2024-01-12.db "PRAGMA journal_mode;"

# Limpar checkpoints
kubectl exec -it pod/megalog-web-xxxxx -- \
  sqlite3 /dados2/system-log/cold/2024-01-12.db "PRAGMA wal_checkpoint(RESTART);"
```

### Processor não conecta ao HOT
```bash
# Verificar permissões
kubectl exec -it pod/megalog-processor-xxxxx -- ls -la /dados1/system-log/hot/

# Verificar pygtail offset
kubectl exec -it pod/megalog-processor-xxxxx -- cat /dados1/.pygtail_offset

# Resetar offset
kubectl exec -it pod/megalog-processor-xxxxx -- rm /dados1/.pygtail_offset
```

## Escalabilidade

### 1. Horizontal Pod Autoscaling

O manifesto incluí HPA automático:
```bash
# Verificar HPA
kubectl get hpa

# Forçar scaling manualmente
kubectl scale deployment megalog-web --replicas=5

# Remover HPA
kubectl delete hpa megalog-web-hpa
```

### 2. Custom Metrics

```bash
# Escalar baseado em métricas customizadas
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: megalog-custom-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: megalog-web
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

### 3. Pod Disruption Budgets

PDB já incluído no manifesto. Para eventos:
```bash
# Ver PDBs
kubectl get pdb

# Drain node mantendo mínimo
kubectl drain node-1 --ignore-daemonsets --disable-eviction=false
```

### 4. Limites de Recursos

Aumentar se necessário:
```bash
kubectl set resources deployment megalog-web \
  --limits=cpu=4000m,memory=4Gi \
  --requests=cpu=1000m,memory=1Gi
```

### 5. Multi-region

Para HA:
```yaml
# Usar Federation v2 ou:
# 1. Deploy em múltiplos clusters
# 2. Usar external-dns para round-robin
# 3. Sincronizar dados via shared storage (NFS/S3)

apiVersion: v1
kind: Service
metadata:
  name: megalog-federation
  annotations:
    external-dns.alpha.kubernetes.io/hostname: megalog.example.com
spec:
  type: ExternalName
  externalName: megalog.region1.svc.cluster.local
```

## Comandos Úteis

```bash
# Status completo
kubectl get all -n megalog

# Restart pods
kubectl rollout restart deployment/megalog-web
kubectl rollout restart deployment/megalog-processor

# Escalar
kubectl scale deployment megalog-web --replicas=5

# Logs
kubectl logs -f deployment/megalog-web --tail=50
kubectl logs -f deployment/megalog-processor

# Shell interativo
kubectl exec -it pod/megalog-web-xxxxx -- /bin/bash

# Port-forward
kubectl port-forward svc/megalog 8080:80
kubectl port-forward pod/megalog-web-xxxxx 5000:5000

# Copiar arquivos
kubectl cp megalog/megalog-web-xxxxx:/dados2/system-log/cold ./backup

# Deletar tudo
kubectl delete -f kubernetes-deployment.yaml
```

## 🎯 Roadmap

- [ ] Implementar servicemonitor para Prometheus
- [ ] Adicionar rate-limiting com nginx
- [ ] Backup automático com Velero
- [ ] Multi-tenancy com namespaces
- [ ] GitOps com ArgoCD
- [ ] Policy Engine (OPA/Gatekeeper)

## 📞 Suporte

Para issues:
1. Verificar logs: `kubectl logs -f pod/nome`
2. Descrever eventos: `kubectl describe pod/nome`
3. Verificar recursos: `kubectl top pods`
4. Validar YAML: `kubectl apply -f manifesto.yaml --dry-run=client`
