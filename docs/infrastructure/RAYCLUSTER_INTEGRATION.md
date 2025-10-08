# RayCluster Integration Guide

## 📊 Estado Actual

Tu cluster de Kubernetes ya tiene un **RayCluster productivo** funcionando:

### Configuración Actual (namespace `ray`)

```yaml
Namespace: ray
Nombre: ray-gpu
Ray Version: 2.49.2
Estado: ready (4 días en producción)

Head Node:
  CPU: 8 cores (límite), 2 cores (request)
  Memory: 32Gi (límite), 16Gi (request)
  GPUs: 0
  Node: wrx80-node1

GPU Workers: 8 replicas
  CPU por worker: 12 cores (límite), 3 cores (request)
  Memory por worker: 64Gi (límite), 56Gi (request)
  GPUs por worker: 1
  Node: wrx80-node1

Totales:
  CPUs: 26 (8 head + 18 workers request, 104 límite)
  Memory: 464Gi (request), 544Gi (límite)
  GPUs: 8
```

### Hardware de tu Estación de Trabajo

**Plataforma:** AMD WRX80  
**CPU:** AMD Threadripper PRO 5955WX (16 cores, 32 threads @ 4.0GHz)  
**RAM:** 512GB DDR4 ECC (8x64GB, 8 canales)  
**GPUs:** 4x NVIDIA RTX 3090 (24GB VRAM cada una) = 96GB VRAM total  
**PCIe Lanes:** 128 (soporte completo para 4 GPUs x16)

**Kubernetes detecta:** 32 vCPUs, 516GB RAM, 8 GPUs (posiblemente reportando 2 MIG instances por GPU física)

---

## 🔀 Opciones de Integración

### Opción 1: **Usar el RayCluster Existente** (Recomendado)

**Ventajas:**
- ✅ Ya está funcionando y probado
- ✅ No duplicas recursos (32 cores totales disponibles)
- ✅ Más eficiente: 1 solo control plane de Ray
- ✅ Configuración optimizada para tu hardware

**Desventajas:**
- ⚠️ Necesitas configurar RBAC cross-namespace
- ⚠️ Menos aislamiento entre workloads

**Implementación:**

1. **Dar permisos cross-namespace al workspace runner:**

```yaml
# deploy/k8s-optional/raycluster-cross-namespace.yaml
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ray-client-access
rules:
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["get", "list"]
  - apiGroups: ["ray.io"]
    resources: ["rayclusters", "rayjobs"]
    verbs: ["get", "list", "create", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: swe-ai-fleet-ray-access
subjects:
  - kind: ServiceAccount
    name: workspace-runner-sa
    namespace: swe-ai-fleet
roleRef:
  kind: ClusterRole
  name: ray-client-access
  apiGroup: rbac.authorization.k8s.io
```

2. **Actualizar workspace runner para conectarse a `ray` namespace:**

```python
# workers/workspace_runner.py
RAY_ADDRESS = "ray://ray-gpu-head-svc.ray.svc.cluster.local:10001"
```

3. **Exponer el Ray Dashboard internamente:**

```yaml
# deploy/k8s/02-nats-internal-dns.yaml
---
apiVersion: v1
kind: Service
metadata:
  name: internal-ray-dashboard
  namespace: swe-ai-fleet
spec:
  type: ExternalName
  externalName: ray-gpu-head-svc.ray.svc.cluster.local
  ports:
    - name: dashboard
      port: 8265
      targetPort: 8265
```

---

### Opción 2: **Cluster Separado para swe-ai-fleet**

**Ventajas:**
- ✅ Aislamiento completo de workloads
- ✅ Políticas de recursos independientes
- ✅ Más fácil rollback si algo falla

**Desventajas:**
- ❌ Duplicas overhead (2 head nodes)
- ❌ Fragmentas recursos limitados (32 cores totales)
- ❌ Mayor complejidad operacional

**Implementación:**

```bash
kubectl apply -f deploy/k8s-optional/raycluster-agents.yaml
```

**Ajustes recomendados para evitar resource contention:**

Reducir el cluster existente temporalmente:
```bash
kubectl scale raycluster ray-gpu -n ray --replicas=4  # Reducir a 4 workers
```

O ajustar los recursos del nuevo cluster en `03-raycluster-agents.yaml`:
```yaml
workerGroupSpecs:
  - groupName: gpu-workers
    replicas: 4  # Reducir a 4 para no saturar
    minReplicas: 2
    maxReplicas: 4
```

---

## 🎯 Recomendación para tu Setup

### **Usa el RayCluster existente** (`ray-gpu` en namespace `ray`)

**Razones:**
1. Tu hardware tiene **32 vCPUs y 4-8 GPUs**
2. El cluster existente ya usa **26 vCPUs** (request) de manera eficiente
3. Crear un segundo cluster requeriría al menos **10-15 vCPUs más** → excedes capacidad
4. El cluster actual tiene **8 workers con 1 GPU c/u** → perfecto para multi-tenancy

**Configuración cross-namespace:**

```yaml
# workers/config.yaml
ray:
  address: "ray://ray-gpu-head-svc.ray.svc.cluster.local:10001"
  namespace: ray
  cluster_name: ray-gpu
  runtime_env:
    pip: 
      - "openai"
      - "anthropic"
      - "nats-py"
```

---

## 🚀 Plan de Despliegue

### Paso 1: Configurar acceso cross-namespace

```bash
# Crear RBAC para acceso desde swe-ai-fleet → ray
kubectl apply -f deploy/k8s-optional/raycluster-cross-namespace.yaml
```

### Paso 2: Actualizar workspace runner

```bash
# Modificar workers/workspace_runner.py con la nueva dirección
vi workers/workspace_runner.py

# Rebuild imagen del worker
cd services
make build-worker
make push-worker
```

### Paso 3: Exponer dashboard internamente

```bash
# Añadir servicio internal-ray-dashboard
kubectl apply -f deploy/k8s/02-nats-internal-dns.yaml
```

### Paso 4: Verificar conectividad

```bash
# Desde un pod en swe-ai-fleet
kubectl run -it --rm debug --image=docker.io/rayproject/ray:2.49.2 -n swe-ai-fleet -- bash
python3 -c "import ray; ray.init('ray://ray-gpu-head-svc.ray.svc.cluster.local:10001'); print(ray.cluster_resources())"
```

---

## 📊 Monitoreo

### Dashboard de Ray (interno)

```bash
# Port-forward para acceder localmente
kubectl port-forward -n ray svc/ray-gpu-head-svc 8265:8265

# Abrir en navegador
http://localhost:8265
```

### Métricas de GPU

```bash
# Verificar uso de GPU en workers
kubectl exec -it -n ray ray-gpu-gpu-workers-worker-XXXXX -- nvidia-smi

# Ver todos los workers
for pod in $(kubectl get pods -n ray -l ray-cluster=ray-gpu,groupName=gpu-workers -o name); do
  echo "=== $pod ==="
  kubectl exec -n ray $pod -- nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv
done
```

---

## 🔧 Troubleshooting

### Ray no conecta cross-namespace

**Síntoma:** `ConnectionError: Failed to connect to Ray`

**Solución:**
```bash
# Verificar DNS
kubectl run -it --rm dnstest --image=busybox -n swe-ai-fleet -- nslookup ray-gpu-head-svc.ray.svc.cluster.local

# Verificar puerto 10001 abierto
kubectl run -it --rm nettest --image=nicolaka/netshoot -n swe-ai-fleet -- nc -zv ray-gpu-head-svc.ray.svc.cluster.local 10001
```

### GPU no disponible en workers

**Síntoma:** Ray reporta `num-gpus: 0`

**Solución:**
```bash
# Verificar NVIDIA device plugin
kubectl get daemonset -n kube-system nvidia-device-plugin-daemonset

# Verificar node labels
kubectl describe node wrx80-node1 | grep nvidia.com/gpu
```

### Out of Memory (OOM)

**Síntoma:** Workers reiniciando frecuentemente

**Solución:**
```bash
# Reducir número de workers
kubectl patch raycluster ray-gpu -n ray --type='json' -p='[{"op": "replace", "path": "/spec/workerGroupSpecs/0/replicas", "value": 4}]'

# O reducir memoria por worker
kubectl patch raycluster ray-gpu -n ray --type='json' -p='[{"op": "replace", "path": "/spec/workerGroupSpecs/0/template/spec/containers/0/resources/limits/memory", "value": "48Gi"}]'
```

---

## 📝 Próximos Pasos

1. ✅ Revisar este documento
2. ⬜ Decidir opción de integración (cross-namespace vs. cluster separado)
3. ⬜ Aplicar configuración RBAC
4. ⬜ Actualizar workspace runner
5. ⬜ Probar conectividad
6. ⬜ Desplegar workspace runner actualizado
7. ⬜ Verificar ejecución de agentes

---

## 📚 Referencias

- [KubeRay Documentation](https://docs.ray.io/en/latest/cluster/kubernetes/index.html)
- [Ray Client](https://docs.ray.io/en/latest/cluster/running-applications/job-submission/ray-client.html)
- [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/index.html)
- [Threadripper PRO 5955WX Specs](https://www.amd.com/en/products/cpu/amd-ryzen-threadripper-pro-5955wx)
