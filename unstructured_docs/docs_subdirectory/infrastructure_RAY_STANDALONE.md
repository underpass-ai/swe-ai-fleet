# Ray Standalone - Uso sin KubeRay

## 📋 Índice

1. [Ray con KubeRay vs Standalone](#ray-con-kuberay-vs-standalone)
2. [Dashboard de Ray](#dashboard-de-ray)
3. [Usar Ray Standalone en K8s](#usar-ray-standalone-en-k8s)
4. [Conectarse a Ray desde fuera del cluster](#conectarse-a-ray-desde-fuera-del-cluster)
5. [Ray en modo local (desarrollo)](#ray-en-modo-local-desarrollo)

---

## 🔀 Ray con KubeRay vs Standalone

### Con KubeRay (Configuración Actual)

**Ventajas:**
✅ **Gestión declarativa:** Define el cluster en YAML  
✅ **Auto-scaling:** Ajusta workers automáticamente  
✅ **Monitoreo integrado:** Dashboard y métricas  
✅ **RBAC y aislamiento:** Usa ServiceAccounts de K8s  
✅ **Recuperación automática:** KubeRay reinicia pods caídos

**Configuración Actual:**
```yaml
RayCluster: ray-gpu
Namespace: ray
Head: 1 pod (CPU only)
Workers: 8 pods (1 GPU c/u)
Estado: ready (4+ días)
```

### Standalone (Sin KubeRay)

**Ventajas:**
✅ **Más control:** Configuración manual completa  
✅ **Más ligero:** Sin overhead del operator  
✅ **Testing rápido:** Ideal para experimentos  
✅ **Portabilidad:** Funciona igual en laptop/VM/K8s

**Desventajas:**
❌ **Manual:** Tienes que iniciar/parar pods tú mismo  
❌ **Sin auto-scaling:** Workers fijos  
❌ **Sin recuperación automática:** Si un pod muere, queda muerto

---

## 📊 Dashboard de Ray

### Acceso Actual (Port-Forward)

El dashboard está disponible pero **no expuesto públicamente**:

```bash
# Port-forward temporal
kubectl port-forward -n ray svc/ray-gpu-head-svc 8265:8265

# Abrir en navegador
http://localhost:8265
```

### Exponer vía Ingress (Recomendado)

Para acceso permanente con HTTPS:

```bash
# Desplegar ingress
./scripts/expose-ray-dashboard.sh

# Acceder vía web
https://ray.underpassai.com
```

**Features del Dashboard:**
- 📊 Estado del cluster (head + workers)
- 🎯 Jobs en ejecución
- 📈 Uso de CPU/GPU/Memoria por worker
- 📝 Logs de tasks
- 🔄 Actualizaciones en tiempo real (WebSocket)

### Acceso Interno (desde pods)

```python
# Desde cualquier pod en K8s
import ray

# Conectar al dashboard vía DNS interno
ray.init("ray://ray-gpu-head-svc.ray.svc.cluster.local:10001")

# Ver recursos disponibles
print(ray.cluster_resources())
```

---

## 🐳 Usar Ray Standalone en K8s

### Opción 1: Pod Individual (Testing Rápido)

```bash
# Iniciar Ray head (sin KubeRay)
kubectl run ray-standalone \
  --image=docker.io/rayproject/ray:2.49.2 \
  --restart=Never \
  -n default \
  -- ray start --head --port=6379 --dashboard-host=0.0.0.0 --block

# Verificar
kubectl logs -f ray-standalone

# Conectarse desde otro pod
kubectl run ray-test --rm -it \
  --image=docker.io/rayproject/ray:2.49.2 \
  -- python3 -c "import ray; ray.init('ray://ray-standalone:10001'); print(ray.cluster_resources())"
```

### Opción 2: Deployment + StatefulSet (Más Robusto)

```yaml
# ray-standalone.yaml
---
apiVersion: v1
kind: Service
metadata:
  name: ray-head
  namespace: default
spec:
  selector:
    app: ray-head
  ports:
    - name: client
      port: 10001
      targetPort: 10001
    - name: dashboard
      port: 8265
      targetPort: 8265
    - name: gcs
      port: 6379
      targetPort: 6379
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ray-head
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ray-head
  template:
    metadata:
      labels:
        app: ray-head
    spec:
      containers:
        - name: ray-head
          image: docker.io/rayproject/ray:2.49.2
          command:
            - ray
            - start
            - --head
            - --port=6379
            - --dashboard-host=0.0.0.0
            - --num-cpus=0
            - --block
          ports:
            - containerPort: 10001
              name: client
            - containerPort: 8265
              name: dashboard
            - containerPort: 6379
              name: gcs
          resources:
            requests:
              cpu: 1
              memory: 2Gi
            limits:
              cpu: 2
              memory: 4Gi
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: ray-worker
  namespace: default
spec:
  serviceName: ray-worker
  replicas: 4
  selector:
    matchLabels:
      app: ray-worker
  template:
    metadata:
      labels:
        app: ray-worker
    spec:
      containers:
        - name: ray-worker
          image: docker.io/rayproject/ray:2.49.2
          command:
            - ray
            - start
            - --address=ray-head.default.svc.cluster.local:6379
            - --num-cpus=4
            - --num-gpus=1
            - --block
          resources:
            requests:
              cpu: 4
              memory: 8Gi
              nvidia.com/gpu: 1
            limits:
              cpu: 4
              memory: 8Gi
              nvidia.com/gpu: 1
```

Desplegar:
```bash
kubectl apply -f ray-standalone.yaml

# Verificar
kubectl get pods -l app=ray-head
kubectl get pods -l app=ray-worker

# Conectarse
kubectl run ray-test --rm -it \
  --image=docker.io/rayproject/ray:2.49.2 \
  -- python3 -c "import ray; ray.init('ray://ray-head:10001'); print(ray.cluster_resources())"
```

---

## 🌐 Conectarse a Ray desde fuera del cluster

### Opción 1: Port-Forward (Desarrollo)

```bash
# Terminal 1: Port-forward
kubectl port-forward -n ray svc/ray-gpu-head-svc 10001:10001

# Terminal 2: Script local
cat > test_ray.py << 'EOF'
import ray

# Conectar a Ray en K8s
ray.init("ray://localhost:10001")

@ray.remote
def hello():
    import socket
    return f"Hello from {socket.gethostname()}"

# Ejecutar tarea en el cluster
result = ray.get(hello.remote())
print(result)

ray.shutdown()
EOF

python3 test_ray.py
```

### Opción 2: LoadBalancer (Producción)

```yaml
# ray-loadbalancer.yaml
apiVersion: v1
kind: Service
metadata:
  name: ray-client-external
  namespace: ray
spec:
  type: LoadBalancer
  selector:
    ray.io/cluster: ray-gpu
    ray.io/node-type: head
  ports:
    - name: client
      port: 10001
      targetPort: 10001
```

```bash
kubectl apply -f ray-loadbalancer.yaml

# Obtener IP externa
EXTERNAL_IP=$(kubectl get svc -n ray ray-client-external -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Conectar desde laptop
python3 -c "import ray; ray.init('ray://$EXTERNAL_IP:10001'); print(ray.cluster_resources())"
```

### Opción 3: Ray Job Submission (API REST)

Ray tiene una API REST para enviar jobs sin necesidad de Ray client:

```bash
# Exponer API via port-forward
kubectl port-forward -n ray svc/ray-gpu-head-svc 8265:8265

# Submit job vía CLI
ray job submit --address http://localhost:8265 -- python my_script.py

# Submit job vía Python API
cat > submit_job.py << 'EOF'
from ray.job_submission import JobSubmissionClient

client = JobSubmissionClient("http://localhost:8265")

job_id = client.submit_job(
    entrypoint="python my_script.py",
    runtime_env={"pip": ["numpy", "pandas"]}
)

print(f"Job submitted: {job_id}")
print(client.get_job_status(job_id))
EOF

python3 submit_job.py
```

---

## 💻 Ray en modo local (desarrollo)

### Instalación Local

```bash
# Instalar Ray
pip install 'ray[default]'

# Con soporte GPU
pip install 'ray[default]' torch
```

### Uso Local (Sin Cluster)

```python
import ray

# Modo local: Ray usa CPUs/GPUs de tu laptop
ray.init()

@ray.remote
def compute():
    return sum(range(1000000))

# Se ejecuta en threads/procesos locales
result = ray.get(compute.remote())
print(result)

ray.shutdown()
```

### Cluster Local (Head + Workers en laptop)

```bash
# Terminal 1: Head
ray start --head --port=6379 --dashboard-host=0.0.0.0

# Terminal 2, 3, 4: Workers
ray start --address=127.0.0.1:6379 --num-cpus=4
ray start --address=127.0.0.1:6379 --num-cpus=4
ray start --address=127.0.0.1:6379 --num-cpus=4

# Terminal 5: Python script
python3 << 'EOF'
import ray

ray.init("ray://localhost:10001")

@ray.remote
def hello():
    import socket
    return f"Hello from {socket.gethostname()}"

results = ray.get([hello.remote() for _ in range(10)])
for r in results:
    print(r)

ray.shutdown()
EOF

# Detener todo
ray stop
```

---

## 🔍 Comparación de Opciones

| Opción | Setup | Auto-Scaling | GPU Support | Mejor Para |
|--------|-------|--------------|-------------|------------|
| **KubeRay** | Declarativo (YAML) | ✅ Sí | ✅ Sí | Producción, multi-tenant |
| **K8s Standalone** | Manual (kubectl) | ❌ No | ✅ Sí | Testing, entornos aislados |
| **Local Ray** | `ray start` | ❌ No | ✅ Sí (si tienes GPU local) | Desarrollo rápido |
| **Ray Client** | Port-forward | N/A | ✅ Sí | Desarrollo remoto |
| **Ray Job Submission** | API REST | N/A | ✅ Sí | CI/CD, automatización |

---

## 🎯 Recomendaciones

### Para tu caso actual:

1. **Producción:** Usa **KubeRay** (ya lo tienes funcionando perfecto)
2. **Testing rápido:** Usa **Ray Job Submission API** (no necesitas otro cluster)
3. **Desarrollo local:** Usa **`ray.init()` local** para probar lógica antes de desplegar

### Workflow típico:

```
1. Desarrollo local:
   ray.init()  # Test rápido en laptop
   
2. Testing en K8s:
   ray job submit --address http://localhost:8265 -- python my_script.py
   
3. Producción:
   kubectl apply -f rayjob.yaml  # KubeRay Job CRD
```

---

## 📚 Referencias

- [Ray Cluster Quickstart](https://docs.ray.io/en/latest/cluster/getting-started.html)
- [Ray Job Submission](https://docs.ray.io/en/latest/cluster/running-applications/job-submission/index.html)
- [KubeRay Documentation](https://docs.ray.io/en/latest/cluster/kubernetes/index.html)
- [Ray Dashboard](https://docs.ray.io/en/latest/ray-observability/getting-started.html)

---

## ✅ Próximos Pasos

- ⬜ Exponer Ray Dashboard vía ingress
- ⬜ Probar Ray Job Submission API
- ⬜ Configurar métricas de Ray en Prometheus
- ⬜ Documentar workflows típicos de desarrollo
