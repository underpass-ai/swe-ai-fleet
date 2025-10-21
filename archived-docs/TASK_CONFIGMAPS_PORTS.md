# 🔧 Task 4.1: Centralizar Puertos en ConfigMaps

**Prioridad**: 🟡 MEDIA  
**Estimación**: 1-2 horas  
**Estado**: ⏳ Pendiente

---

## 🎯 Objetivo

Centralizar todos los puertos de servicios en ConfigMaps de Kubernetes en lugar de tenerlos hardcodeados en múltiples lugares (código fuente, deployments, environment variables).

## ❌ Problema Actual

Los puertos están dispersos y duplicados en múltiples ubicaciones:

### Ejemplos de Inconsistencias Encontradas:

1. **Orchestrator**:
   - `services/orchestrator/server.py`: `GRPC_PORT = 50055`
   - `deploy/k8s/11-orchestrator-service.yaml`: `port: 50055`
   - `services/monitoring/sources/orchestrator_source.py`: ~~`50052`~~ ❌ **INCORRECTO**
   
2. **Ray Executor**:
   - `services/ray-executor/server.py`: `GRPC_PORT = 50056`
   - `deploy/k8s/14-ray-executor.yaml`: `port: 50056`
   - Correcto en monitoring

3. **Context Service**:
   - Puerto en deployment
   - Puerto en código
   - Potencialmente inconsistente

## ✅ Solución Propuesta

Crear un ConfigMap centralizado con todos los puertos y referencias de servicios.

---

## 📋 Implementación

### Paso 1: Crear ConfigMap de Servicios

**Archivo**: `deploy/k8s/00-service-config.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: service-ports
  namespace: swe-ai-fleet
data:
  # gRPC Services
  ORCHESTRATOR_PORT: "50055"
  ORCHESTRATOR_ADDRESS: "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
  
  CONTEXT_PORT: "50051"
  CONTEXT_ADDRESS: "context.swe-ai-fleet.svc.cluster.local:50051"
  
  RAY_EXECUTOR_PORT: "50056"
  RAY_EXECUTOR_ADDRESS: "ray-executor.swe-ai-fleet.svc.cluster.local:50056"
  
  PLANNING_PORT: "50053"
  PLANNING_ADDRESS: "planning.swe-ai-fleet.svc.cluster.local:50053"
  
  # Infrastructure Services
  NATS_PORT: "4222"
  NATS_ADDRESS: "nats://nats.swe-ai-fleet.svc.cluster.local:4222"
  
  VALKEY_PORT: "6379"
  VALKEY_ADDRESS: "redis://valkey.swe-ai-fleet.svc.cluster.local:6379"
  
  NEO4J_BOLT_PORT: "7687"
  NEO4J_HTTP_PORT: "7474"
  NEO4J_ADDRESS: "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687"
  
  # Ray Cluster
  RAY_CLIENT_PORT: "10001"
  RAY_DASHBOARD_PORT: "8265"
  RAY_ADDRESS: "ray://ray-gpu-head-svc.ray.svc.cluster.local:10001"
  
  # vLLM
  VLLM_PORT: "8000"
  VLLM_ADDRESS: "http://vllm-server-service.ray.svc.cluster.local:8000"
  
  # Monitoring
  MONITORING_PORT: "8080"
  MONITORING_ADDRESS: "http://monitoring-dashboard.swe-ai-fleet.svc.cluster.local:8080"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: service-defaults
  namespace: swe-ai-fleet
data:
  # Default values
  VLLM_MODEL: "Qwen/Qwen3-0.6B"
  DEFAULT_TIMEOUT: "300"
  DEFAULT_MAX_RETRIES: "3"
  
  # Python versions
  PYTHON_VERSION: "3.13"
  RAY_PYTHON_VERSION: "3.9"
  
  # Ray versions
  RAY_VERSION: "2.49.2"
```

### Paso 2: Actualizar Deployments

Ejemplo para **Monitoring Dashboard**:

```yaml
# deploy/k8s/13-monitoring-dashboard.yaml
spec:
  containers:
  - name: monitoring
    env:
    - name: PORT
      valueFrom:
        configMapKeyRef:
          name: service-ports
          key: MONITORING_PORT
    - name: NATS_URL
      valueFrom:
        configMapKeyRef:
          name: service-ports
          key: NATS_ADDRESS
    - name: RAY_EXECUTOR_ADDRESS
      valueFrom:
        configMapKeyRef:
          name: service-ports
          key: RAY_EXECUTOR_ADDRESS
    - name: ORCHESTRATOR_ADDRESS
      valueFrom:
        configMapKeyRef:
          name: service-ports
          key: ORCHESTRATOR_ADDRESS
    - name: NEO4J_URI
      valueFrom:
        configMapKeyRef:
          name: service-ports
          key: NEO4J_ADDRESS
    - name: VALKEY_URL
      valueFrom:
        configMapKeyRef:
          name: service-ports
          key: VALKEY_ADDRESS
```

### Paso 3: Actualizar Código Fuente

Remover valores hardcodeados y usar solo env vars:

**Antes** (orchestrator_source.py):
```python
self.address = os.getenv(
    "ORCHESTRATOR_ADDRESS",
    "orchestrator.swe-ai-fleet.svc.cluster.local:50055"  # ❌ Hardcoded
)
```

**Después**:
```python
self.address = os.getenv("ORCHESTRATOR_ADDRESS")
if not self.address:
    raise ValueError("ORCHESTRATOR_ADDRESS not configured")
```

### Paso 4: Actualizar Services en K8s

Los manifests de Service deben referenciar el ConfigMap también (opcional):

```yaml
# deploy/k8s/11-orchestrator-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: swe-ai-fleet
  annotations:
    service.port: "50055"  # Documentación
spec:
  ports:
  - name: grpc
    port: 50055  # Debe coincidir con ConfigMap
    targetPort: grpc
```

---

## 📝 Checklist de Archivos a Actualizar

### ConfigMaps
- [ ] `deploy/k8s/00-service-config.yaml` - **CREAR NUEVO**

### Deployments (usar ConfigMap refs)
- [ ] `deploy/k8s/08-context-service.yaml`
- [ ] `deploy/k8s/11-orchestrator-service.yaml`
- [ ] `deploy/k8s/12-planning-service.yaml`
- [ ] `deploy/k8s/13-monitoring-dashboard.yaml`
- [ ] `deploy/k8s/14-ray-executor.yaml`

### Código Fuente (remover defaults hardcoded)
- [ ] `services/monitoring/sources/orchestrator_source.py`
- [ ] `services/monitoring/sources/ray_source.py`
- [ ] `services/monitoring/sources/neo4j_source.py`
- [ ] `services/monitoring/sources/valkey_source.py`
- [ ] `services/context/server.py`
- [ ] `services/orchestrator/server.py`
- [ ] `services/ray-executor/server.py`

### Validación
- [ ] Verificar que todos los puertos coincidan
- [ ] Verificar que no haya defaults hardcoded
- [ ] Testing en cluster local
- [ ] Deploy a producción

---

## 🎯 Beneficios

1. **Single Source of Truth**: Un solo lugar para configuración
2. **Fácil Mantenimiento**: Cambiar puerto una sola vez
3. **Menos Errores**: No más puertos incorrectos hardcoded
4. **Documentación**: ConfigMap sirve como documentación de arquitectura
5. **Flexibilidad**: Fácil cambiar configuración sin rebuild

---

## ⚠️ Consideraciones

1. **Backward Compatibility**: 
   - Mantener defaults en código para desarrollo local
   - Pero hacer que fallen rápido si env var falta en K8s

2. **Order of Deployment**:
   - ConfigMap debe desplegarse ANTES que los deployments
   - Renumerar: `00-service-config.yaml` para que se aplique primero

3. **Documentation**:
   - Actualizar README de cada servicio
   - Documentar en INSTALLATION.md

---

## 🚀 Plan de Ejecución

### Fase 1: Crear ConfigMaps
1. Crear `deploy/k8s/00-service-config.yaml`
2. Aplicar al cluster: `kubectl apply -f deploy/k8s/00-service-config.yaml`

### Fase 2: Actualizar Deployments (uno por uno)
1. Monitoring Dashboard
2. Orchestrator
3. Context
4. Ray Executor
5. Planning

### Fase 3: Actualizar Código
1. Remover defaults hardcoded
2. Agregar validación de env vars

### Fase 4: Testing
1. Deploy a dev environment
2. Verificar todas las conexiones
3. Verificar logs (no debe haber defaults usados)
4. Deploy a producción

---

## 📚 Referencias

- [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Using ConfigMap data in Pods](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)
- [12-Factor App - Config](https://12factor.net/config)

---

**Creado**: 2025-10-17  
**Prioridad**: 🟡 MEDIA  
**Owner**: Tirso (Lead Architect)

