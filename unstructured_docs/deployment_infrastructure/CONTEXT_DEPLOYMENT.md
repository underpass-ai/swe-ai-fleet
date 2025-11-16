# Context Service - Deployment en Kubernetes

Guía completa para desplegar el Context Service y sus dependencias en Kubernetes.

## 📦 Componentes a Desplegar

### 1. **Neo4j** (Grafo de Decisiones)
- **Imagen**: `neo4j:5.14`
- **Puerto**: 7687 (Bolt), 7474 (HTTP)
- **Storage**: 10Gi (data) + 1Gi (logs)
- **Recursos**: 250m-1000m CPU, 1Gi-2Gi RAM
- **Archivo**: `09-neo4j.yaml`

### 2. **Valkey** (Cache - Redis-compatible)
- **Imagen**: `valkey/valkey:8.0-alpine`
- **Puerto**: 6379
- **Storage**: 2Gi
- **Recursos**: 100m-500m CPU, 256Mi-768Mi RAM
- **Archivo**: `10-valkey.yaml`
- **Nota**: Valkey es un fork de Redis mantenido por Linux Foundation, 100% compatible

### 3. **Context Service** (Microservicio)
- **Imagen**: `registry.underpassai.com/swe-fleet/context:v0.2.0`
- **Puerto**: 50054 (gRPC)
- **Replicas**: 2
- **Recursos**: 100m-500m CPU, 256Mi-512Mi RAM
- **Archivo**: `08-context-service.yaml`

## 🔍 Estado Actual del Cluster

### Verificar cluster
```bash
kubectl cluster-info
kubectl get nodes -o wide
```

### Verificar namespace swe-ai-fleet
```bash
kubectl get namespaces | grep swe-ai-fleet
kubectl get all -n swe-ai-fleet
```

### Verificar servicios existentes
```bash
# Servicios actuales
kubectl get svc -n swe-ai-fleet

# Deployments actuales
kubectl get deployments -n swe-ai-fleet

# StatefulSets actuales
kubectl get statefulsets -n swe-ai-fleet

# ConfigMaps y Secrets
kubectl get configmaps,secrets -n swe-ai-fleet

# Ingress
kubectl get ingress -n swe-ai-fleet
```

### Verificar storage
```bash
# Storage classes disponibles
kubectl get storageclass

# PVCs existentes
kubectl get pvc -n swe-ai-fleet
```

## 🚀 Deployment

### Opción 1: Script Automatizado (Recomendado)

```bash
cd /home/tirso/ai/developents/swe-ai-fleet/deploy/k8s

# Ejecutar deployment completo
./deploy-context.sh
```

El script:
1. Verifica que kubectl está disponible
2. Verifica que el namespace existe
3. Despliega Neo4j y espera que esté listo
4. Despliega Valkey y espera que esté listo
5. Despliega Context Service
6. Muestra el estado final

### Opción 2: Deployment Manual

```bash
cd /home/tirso/ai/developents/swe-ai-fleet/deploy/k8s

# 1. Desplegar Neo4j
kubectl apply -f 09-neo4j.yaml
kubectl wait --for=condition=ready pod -l app=neo4j -n swe-ai-fleet --timeout=300s

# 2. Desplegar Valkey
kubectl apply -f 10-valkey.yaml
kubectl wait --for=condition=ready pod -l app=valkey -n swe-ai-fleet --timeout=180s

# 3. Desplegar Context Service
kubectl apply -f 08-context-service.yaml
kubectl wait --for=condition=available deployment/context -n swe-ai-fleet --timeout=300s
```

## 📊 Verificación del Deployment

### Ver estado de los pods
```bash
# Todos los pods
kubectl get pods -n swe-ai-fleet

# Solo Context Service
kubectl get pods -n swe-ai-fleet -l app=context

# Solo Neo4j
kubectl get pods -n swe-ai-fleet -l app=neo4j

# Solo Valkey
kubectl get pods -n swe-ai-fleet -l app=valkey
```

### Ver logs
```bash
# Context Service
kubectl logs -n swe-ai-fleet -l app=context --tail=100 -f

# Neo4j
kubectl logs -n swe-ai-fleet -l app=neo4j --tail=100 -f

# Valkey
kubectl logs -n swe-ai-fleet -l app=valkey --tail=100 -f
```

### Ver servicios
```bash
# Todos los servicios
kubectl get svc -n swe-ai-fleet

# Descripción detallada del Context Service
kubectl describe svc context -n swe-ai-fleet
```

### Ver estado detallado
```bash
# Deployment del Context Service
kubectl describe deployment context -n swe-ai-fleet

# StatefulSet de Neo4j
kubectl describe statefulset neo4j -n swe-ai-fleet

# StatefulSet de Valkey
kubectl describe statefulset valkey -n swe-ai-fleet
```

## 🔧 Troubleshooting

### Pods no inician
```bash
# Ver eventos
kubectl get events -n swe-ai-fleet --sort-by='.lastTimestamp' | tail -20

# Ver detalles de un pod
kubectl describe pod <pod-name> -n swe-ai-fleet

# Ver logs de un pod con error
kubectl logs <pod-name> -n swe-ai-fleet --previous
```

### Context Service no puede conectar a Neo4j/Valkey
```bash
# Verificar que Neo4j está escuchando
kubectl exec -it neo4j-0 -n swe-ai-fleet -- cypher-shell -u neo4j -p testpassword "RETURN 1"

# Verificar que Valkey está escuchando
kubectl exec -it valkey-0 -n swe-ai-fleet -- valkey-cli ping

# Verificar DNS interno
kubectl run -it --rm debug --image=busybox --restart=Never -n swe-ai-fleet -- nslookup neo4j.swe-ai-fleet.svc.cluster.local
kubectl run -it --rm debug --image=busybox --restart=Never -n swe-ai-fleet -- nslookup valkey.swe-ai-fleet.svc.cluster.local
```

### Storage issues
```bash
# Ver PVCs
kubectl get pvc -n swe-ai-fleet

# Ver detalles de un PVC
kubectl describe pvc <pvc-name> -n swe-ai-fleet

# Ver PVs
kubectl get pv
```

## 🔄 Actualizar la Imagen del Context Service

```bash
# 1. Construir nueva imagen
cd /home/tirso/ai/developents/swe-ai-fleet
podman build -t registry.underpassai.com/swe-fleet/context:v0.2.1 -f services/context/Dockerfile .

# 2. Push al registry
podman push registry.underpassai.com/swe-fleet/context:v0.2.1

# 3. Actualizar deployment
kubectl set image deployment/context context=registry.underpassai.com/swe-fleet/context:v0.2.1 -n swe-ai-fleet

# 4. Ver rollout
kubectl rollout status deployment/context -n swe-ai-fleet

# 5. Ver historia de rollouts
kubectl rollout history deployment/context -n swe-ai-fleet
```

## 🗑️ Limpieza / Rollback

### Eliminar solo el Context Service
```bash
kubectl delete -f 08-context-service.yaml
```

### Eliminar todo (Context + Valkey + Neo4j)
```bash
kubectl delete -f 08-context-service.yaml
kubectl delete -f 10-valkey.yaml
kubectl delete -f 09-neo4j.yaml

# NOTA: Los PVCs se mantienen, eliminar manualmente si es necesario
kubectl delete pvc -n swe-ai-fleet -l app=neo4j
kubectl delete pvc -n swe-ai-fleet -l app=valkey
```

### Rollback del Context Service
```bash
# Ver historia
kubectl rollout history deployment/context -n swe-ai-fleet

# Rollback a versión anterior
kubectl rollout undo deployment/context -n swe-ai-fleet

# Rollback a revisión específica
kubectl rollout undo deployment/context --to-revision=1 -n swe-ai-fleet
```

## 🔐 Port Forwarding (para desarrollo/debug)

```bash
# Context Service (gRPC)
kubectl port-forward -n swe-ai-fleet svc/context 50054:50054

# Neo4j (Browser + Bolt)
kubectl port-forward -n swe-ai-fleet svc/neo4j 7474:7474 7687:7687

# Valkey (Redis CLI)
kubectl port-forward -n swe-ai-fleet svc/valkey 6379:6379
```

## 📈 Monitoring

### Ver métricas de recursos
```bash
# CPU/Memory de todos los pods
kubectl top pods -n swe-ai-fleet

# CPU/Memory del Context Service
kubectl top pods -n swe-ai-fleet -l app=context

# CPU/Memory de Neo4j
kubectl top pods -n swe-ai-fleet -l app=neo4j

# CPU/Memory de Valkey
kubectl top pods -n swe-ai-fleet -l app=valkey
```

### Health checks
```bash
# Verificar readiness del Context Service
kubectl get pods -n swe-ai-fleet -l app=context -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}'

# Verificar liveness
kubectl get pods -n swe-ai-fleet -l app=context -o jsonpath='{.items[*].status.conditions[?(@.type=="ContainersReady")].status}'
```

## 🌐 Acceso desde otros servicios

Los servicios del Context pueden ser accedidos desde otros pods en el cluster usando:

```yaml
# Context Service
context.swe-ai-fleet.svc.cluster.local:50054

# Neo4j
neo4j.swe-ai-fleet.svc.cluster.local:7687  # Bolt
neo4j.swe-ai-fleet.svc.cluster.local:7474  # HTTP

# Valkey (también disponible como 'redis')
valkey.swe-ai-fleet.svc.cluster.local:6379
redis.swe-ai-fleet.svc.cluster.local:6379  # Alias para compatibilidad
```

## 🔗 Integración con Orchestrator

El Orchestrator podrá usar el Context Service vía:
- DNS interno: `internal-context` (ExternalName service)
- URL completa: `context.swe-ai-fleet.svc.cluster.local:50054`

## 📝 Notas Importantes

1. **Valkey vs Redis**: Valkey es 100% compatible con el protocolo Redis. Los clientes Python (redis-py) funcionan sin cambios.

2. **Storage**: Se usa `local-path` StorageClass. Verificar que existe en tu cluster.

3. **Passwords**: Neo4j usa `testpassword` hardcoded. Para producción, mover a Secrets.

4. **Replicas**: Context Service usa 2 replicas para alta disponibilidad.

5. **Security Context**: Todos los pods corren como non-root con seccomp profile.

