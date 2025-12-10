# MEGA LOG V2.0 - Helm Chart Guide

## 📋 Índice
1. [Instalação do Helm](#instalação-do-helm)
2. [Deploy com Helm](#deploy-com-helm)
3. [Customizações](#customizações)
4. [Operações](#operações)
5. [Troubleshooting](#troubleshooting)

## Instalação do Helm

### 1. Instalar Helm 3
```bash
# Linux/Mac
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verificar
helm version

# Adicionar repo oficial
helm repo add stable https://charts.helm.sh/stable
helm repo update
```

### 2. Estrutura do Chart

```
helm/megalog/
├── Chart.yaml              # Metadados do chart
├── values.yaml             # Valores padrão
├── templates/
│   ├── deployment.yaml     # Deployments
│   ├── service.yaml        # Service
│   ├── configmap.yaml      # ConfigMap
│   ├── pvc.yaml           # PersistentVolumeClaim
│   ├── serviceaccount.yaml # RBAC
│   ├── hpa.yaml           # HorizontalPodAutoscaler
│   ├── pdb.yaml           # PodDisruptionBudget
│   └── _helpers.tpl       # Templates helpers
```

## Deploy com Helm

### 1. Deploy padrão (teste)

```bash
# Validar chart
helm lint helm/megalog

# Preview do YAML gerado
helm template megalog helm/megalog -n megalog

# Deploy
helm install megalog helm/megalog -n megalog --create-namespace

# Verificar
helm list -n megalog
kubectl get pods -n megalog
kubectl get svc -n megalog
```

### 2. Deploy com valores customizados

```bash
# Via arquivo values
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  -f helm/megalog/values.yaml

# Via CLI (sobrescreve values.yaml)
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  --set replicaCount=3 \
  --set image.tag=v2.1 \
  --set service.type=ClusterIP \
  --set persistence.cold.size=1Ti
```

### 3. Deploy com arquivo de valores customizado

```bash
# Criar valores customizados
cat > custom-values.yaml << 'EOF'
replicaCount: 4
image:
  tag: v2.0
  pullPolicy: Always

service:
  type: LoadBalancer
  
persistence:
  enabled: true
  storageClass: fast-ssd
  cold:
    size: 1Ti
  hot:
    size: 100Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 60

ingress:
  enabled: true
  hosts:
    - host: megalog.example.com
      paths:
        - path: /
          pathType: Prefix
EOF

# Deploy
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  -f custom-values.yaml
```

### 4. Deploy em múltiplos ambientes

```bash
# Valores para desenvolvimento
cat > helm/megalog/values-dev.yaml << 'EOF'
replicaCount: 1
image:
  tag: v2.0-dev
  pullPolicy: Always

autoscaling:
  enabled: false

resources:
  web:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 100m
      memory: 128Mi
EOF

# Valores para produção
cat > helm/megalog/values-prod.yaml << 'EOF'
replicaCount: 3
image:
  tag: v2.0
  pullPolicy: IfNotPresent

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 30

resources:
  web:
    limits:
      cpu: 4000m
      memory: 4Gi
    requests:
      cpu: 2000m
      memory: 2Gi

persistence:
  storageClass: fast-ssd
  cold:
    size: 1Ti
EOF

# Deploy em dev
helm install megalog helm/megalog -n dev --create-namespace -f helm/megalog/values-dev.yaml

# Deploy em prod
helm install megalog helm/megalog -n prod --create-namespace -f helm/megalog/values-prod.yaml
```

## Customizações

### 1. Alterar imagens

```bash
# Apontando para private registry
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  --set image.repository=seu-registry.com/megalog \
  --set processorImage.repository=seu-registry.com/megalog-processor
```

### 2. Image Pull Secrets

```yaml
# custom-values.yaml
imagePullSecrets:
  - name: docker-registry

# Criar secret primeiro
kubectl create secret docker-registry docker-registry \
  --docker-server=seu-registry.com \
  --docker-username=usuario \
  --docker-password=senha \
  -n megalog
```

### 3. Storage customizado

```bash
# Usar volume local
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  --set persistence.enabled=true \
  --set persistence.storageClass=local \
  --set persistence.hot.size=100Gi \
  --set persistence.cold.size=500Gi

# Usar NFS
kubectl apply -f - << 'EOF'
apiVersion: v1
kind: PersistentVolume
metadata:
  name: megalog-nfs-pv
spec:
  capacity:
    storage: 1Ti
  accessModes:
    - ReadWriteMany
  nfs:
    server: nfs-server.local
    path: "/exports/megalog"
EOF

helm install megalog helm/megalog \
  -n megalog --create-namespace \
  --set persistence.storageClass=nfs \
  --set persistence.cold.size=1Ti
```

### 4. Ingress com HTTPS

```bash
# Instalar cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Deploy com Ingress habilitado
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=megalog.example.com \
  --set ingress.tls[0].secretName=megalog-tls \
  --set ingress.tls[0].hosts[0]=megalog.example.com
```

### 5. Limites de recursos customizados

```bash
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  --set resources.web.limits.cpu=8000m \
  --set resources.web.limits.memory=8Gi \
  --set resources.web.requests.cpu=4000m \
  --set resources.web.requests.memory=4Gi \
  --set resources.processor.limits.cpu=2000m \
  --set resources.processor.limits.memory=1Gi
```

### 6. Monitoramento com Prometheus

```bash
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  --set monitoring.prometheus.enabled=true \
  --set monitoring.prometheus.interval=15s
```

## Operações

### 1. Upgrade

```bash
# Atualizar imagem
helm upgrade megalog helm/megalog \
  -n megalog \
  --set image.tag=v2.1

# Com novos valores
helm upgrade megalog helm/megalog \
  -n megalog \
  -f new-values.yaml

# Com histórico
helm history megalog -n megalog
```

### 2. Rollback

```bash
# Para versão anterior
helm rollback megalog 1 -n megalog

# Com delay (esperar pods ficarem ready)
helm rollback megalog 1 -n megalog --wait
```

### 3. Verificar valores

```bash
# Valores efetivos em deployment
helm get values megalog -n megalog

# Template renderizado
helm get manifest megalog -n megalog

# Diferenças
helm diff upgrade megalog helm/megalog -n megalog -f new-values.yaml
```

### 4. Uninstall

```bash
# Manter PVCs
helm uninstall megalog -n megalog

# Deletar tudo (CUIDADO!)
kubectl delete pvc -n megalog --all
```

### 5. Validação antes de deploy

```bash
# Lint
helm lint helm/megalog

# Template validation
helm template megalog helm/megalog | kubeval

# Dry-run
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  --dry-run=client

# Com custom values
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  -f custom-values.yaml \
  --dry-run=server
```

## Troubleshooting

### 1. Pods não iniciam

```bash
# Ver logs do chart
helm get manifest megalog -n megalog | kubectl describe -f -

# Ver eventos
kubectl describe pod megalog-web-xxxxx -n megalog

# Verificar valores
helm get values megalog -n megalog
```

### 2. Storage não funciona

```bash
# Verificar PVCs
kubectl get pvc -n megalog
kubectl describe pvc megalog-hot-pvc -n megalog

# Verificar PVs
kubectl get pv
kubectl describe pv megalog-hot-pv

# Limpiar PVC failed
kubectl delete pvc megalog-hot-pvc -n megalog
helm upgrade megalog helm/megalog -n megalog --reuse-values
```

### 3. Imagem não encontrada

```bash
# Verificar imagePullSecrets
kubectl get secret -n megalog

# Verificar registry
kubectl describe pod megalog-web-xxxxx -n megalog | grep -i pull

# Fixar
helm upgrade megalog helm/megalog \
  -n megalog \
  --set image.pullPolicy=IfNotPresent
```

### 4. Health check falha

```bash
# Testar endpoint
kubectl exec -it pod/megalog-web-xxxxx -n megalog -- curl http://localhost/health

# Aumentar delays
helm upgrade megalog helm/megalog \
  -n megalog \
  --set livenessProbe.initialDelaySeconds=60 \
  --set readinessProbe.initialDelaySeconds=30
```

## Padrões Avançados

### 1. GitOps com Helm (ArgoCD)

```yaml
# argo-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: megalog
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/seu-usuario/megalog
    targetRevision: HEAD
    path: helm/megalog
    helm:
      releaseName: megalog
      values: |
        replicaCount: 3
        image:
          tag: v2.0
  destination:
    server: https://kubernetes.default.svc
    namespace: megalog
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

### 2. Secrets com Sealed Secrets

```bash
# Instalar sealed-secrets
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.23.0/controller.yaml

# Criar secret
kubectl create secret generic db-creds \
  --from-literal=username=admin \
  --from-literal=password=secret \
  --dry-run=client -o yaml | kubeseal -o yaml > sealed-secret.yaml

# Usar em helm values
helm install megalog helm/megalog \
  -n megalog --create-namespace \
  --values-file sealed-secret.yaml
```

### 3. Multi-tenancy

```bash
# Deploy com namespace por tenant
for tenant in client-a client-b client-c; do
  helm install megalog-$tenant helm/megalog \
    -n $tenant --create-namespace \
    --set persistence.hot.size=10Gi \
    --set persistence.cold.size=50Gi
done
```

## Comandos Rápidos

```bash
# Status
helm status megalog -n megalog

# Release info
helm get all megalog -n megalog

# Valores customizados
helm get values megalog -n megalog > current-values.yaml

# Teste completo
helm lint helm/megalog && \
helm template megalog helm/megalog | kubeval && \
helm install megalog helm/megalog --dry-run=server

# Listar todos os releases
helm list --all-namespaces

# Limpar releases failed
helm list --failed -n megalog | awk '{print $1}' | xargs -I {} helm delete {} -n megalog

# Ver diferenças entre upgrades
helm diff upgrade megalog helm/megalog -n megalog -f new-values.yaml
```

## 🎯 Próximos Passos

- [ ] Integração com ArgoCD para GitOps
- [ ] Sealed Secrets para valores sensíveis
- [ ] Helm hooks para migrations
- [ ] Custom metrics para HPA avançado
- [ ] Backup automático com Velero

## 📞 Recursos

- Documentação Helm: https://helm.sh/docs/
- Helm Best Practices: https://helm.sh/docs/chart_best_practices/
- Chart Museum: https://chartmuseum.com/
- Artifact Hub: https://artifacthub.io/
