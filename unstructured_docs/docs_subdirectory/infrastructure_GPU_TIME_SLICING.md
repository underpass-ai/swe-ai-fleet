# NVIDIA GPU Time-Slicing Configuration

## 🎯 Configuración Actual

Tu cluster está usando **NVIDIA Time-Slicing** para multiplicar el número de GPUs disponibles:

```
GPUs Físicas:    4x RTX 3090 (24GB VRAM c/u)
Time-Slicing:    2 replicas por GPU
GPUs Virtuales:  8 (disponibles para Kubernetes)
```

### Estado Actual

```bash
$ kubectl describe node wrx80-node1 | grep nvidia.com/gpu
  nvidia.com/gpu:     8  ✅
```

---

## 🔧 Cómo Funciona Time-Slicing

**Time-Slicing** permite que **múltiples pods compartan una sola GPU física** mediante time-sharing del contexto CUDA:

```
┌─────────────────────────────────────────┐
│  GPU Física 0 (RTX 3090 - 24GB VRAM)    │
├─────────────────────────────────────────┤
│  Slice 0: Pod A (12GB asignado virtual) │
│  Slice 1: Pod B (12GB asignado virtual) │
└─────────────────────────────────────────┘
       Time-sharing de contextos CUDA
```

### Ventajas
✅ **Más GPUs disponibles** para schedulear pods  
✅ **Mejor utilización** de recursos GPU  
✅ **Ideal para cargas intermitentes** (LLM inference)

### Desventajas
⚠️ **VRAM compartida:** Los 24GB son compartidos entre ambos pods  
⚠️ **Latencia variable:** Si ambos pods usan GPU simultáneamente, hay context switching  
⚠️ **No es aislamiento real:** No hay garantías de VRAM exclusiva

---

## 📊 Configuración del NVIDIA GPU Operator

### ConfigMap Actual

```yaml
# kubectl get cm time-slicing-config -n nvidia -o yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: time-slicing-config
  namespace: nvidia
data:
  default: |
    version: v1
    sharing:
      timeSlicing:
        resources:
          - name: nvidia.com/gpu
            replicas: 2  # ← 2 pods por GPU física
```

### ClusterPolicy

```yaml
# kubectl get clusterpolicy cluster-policy -n nvidia -o yaml
spec:
  devicePlugin:
    config:
      default: default
      name: time-slicing-config  # ← Referencia al ConfigMap
    enabled: true
```

---

## 🚀 Uso en RayCluster

Tu RayCluster actual (`ray-gpu` en namespace `ray`) ya está aprovechando las 8 GPUs virtuales:

```yaml
workerGroupSpecs:
  - groupName: gpu-workers
    replicas: 8  # ← 8 workers, 1 GPU virtual c/u
    rayStartParams:
      num-gpus: '1'
    template:
      spec:
        containers:
          - name: ray-worker
            resources:
              requests:
                nvidia.com/gpu: 1  # ← Solicita 1 GPU virtual
              limits:
                nvidia.com/gpu: 1
```

**Resultado:**
- 8 Ray workers corriendo simultáneamente
- Cada worker cree tener 1 GPU dedicada
- En realidad, están compartiendo las 4 GPUs físicas (2 workers por GPU)

---

## 📈 Ajustar Time-Slicing

### Aumentar a 4 pods por GPU (16 GPUs virtuales)

Si quieres más paralelismo (ideal para inference de modelos pequeños):

```bash
kubectl patch configmap time-slicing-config -n nvidia --type merge -p '
{
  "data": {
    "default": "version: v1\nsharing:\n  timeSlicing:\n    resources:\n      - name: nvidia.com/gpu\n        replicas: 4"
  }
}'

# Reiniciar device plugin para aplicar cambios
kubectl delete pod -n nvidia -l app=nvidia-device-plugin-daemonset
```

Verificar:
```bash
kubectl describe node wrx80-node1 | grep nvidia.com/gpu
# Debería mostrar: nvidia.com/gpu: 16
```

### Reducir a 1 pod por GPU (sin time-slicing)

Si necesitas VRAM exclusiva por pod:

```bash
kubectl patch configmap time-slicing-config -n nvidia --type merge -p '
{
  "data": {
    "default": "version: v1\nsharing:\n  timeSlicing:\n    resources:\n      - name: nvidia.com/gpu\n        replicas: 1"
  }
}'

kubectl delete pod -n nvidia -l app=nvidia-device-plugin-daemonset
```

---

## 🧪 Verificar Time-Slicing en Acción

### Ver qué pods están usando GPUs

```bash
kubectl get pods -A -o custom-columns=\
NAMESPACE:.metadata.namespace,\
NAME:.metadata.name,\
GPU_REQUEST:.spec.containers[*].resources.requests.'nvidia\.com/gpu',\
NODE:.spec.nodeName | grep -v '<none>'
```

### Ver VRAM usada en cada GPU física

```bash
kubectl exec -it -n ray ray-gpu-gpu-workers-worker-29sp7 -- nvidia-smi

# Output:
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 550.90.07    Driver Version: 550.90.07    CUDA Version: 12.4     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
|   0  NVIDIA GeForce ... On   | 00000000:01:00.0 Off |                  N/A |
|-------------------------------+----------------------+----------------------+
|  0%   45C    P8    25W / 350W |  4512MiB / 24576MiB  |      0%      Default |
+-------------------------------+----------------------+----------------------+

# ← 4.5GB usados de 24GB (este pod comparte la GPU con otro pod)
```

### Test de Aislamiento

Ejecutar 2 pods en la misma GPU y ver VRAM:

```bash
# Pod 1
kubectl run gpu-test-1 --image=docker.io/nvidia/cuda:12.4.0-base-ubuntu22.04 \
  --restart=Never --rm -it -n default \
  --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"wrx80-node1"},"containers":[{"name":"gpu-test","image":"docker.io/nvidia/cuda:12.4.0-base-ubuntu22.04","command":["sh","-c","nvidia-smi && sleep 300"],"resources":{"limits":{"nvidia.com/gpu":"1"}}}]}}'

# En otra terminal - Pod 2
kubectl run gpu-test-2 --image=docker.io/nvidia/cuda:12.4.0-base-ubuntu22.04 \
  --restart=Never --rm -it -n default \
  --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"wrx80-node1"},"containers":[{"name":"gpu-test","image":"docker.io/nvidia/cuda:12.4.0-base-ubuntu22.04","command":["sh","-c","nvidia-smi && sleep 300"],"resources":{"limits":{"nvidia.com/gpu":"1"}}}]}}'
```

Ambos pods verán **la misma GPU física** con `nvidia-smi`, pero Kubernetes los scheduló en diferentes "slices".

---

## ⚠️ Consideraciones para LLMs

### Modelos que Caben en VRAM (con time-slicing)

Con 24GB por GPU física y 2 pods compartiendo:

| Modelo              | VRAM Típica | ¿Cabe con 2 pods? |
|---------------------|-------------|-------------------|
| Llama 3.3 70B Q4    | ~40GB       | ❌ No (muy grande)|
| Llama 3.1 8B Q4     | ~5GB        | ✅ Sí (10GB total)|
| Qwen2.5 7B          | ~5GB        | ✅ Sí             |
| Mistral 7B          | ~5GB        | ✅ Sí             |
| Phi-3 3.8B          | ~3GB        | ✅ Sí             |
| Gemma 2B            | ~2GB        | ✅ Sí             |

**Recomendación:**  
Si tu workload usa modelos ≤ 7B quantizados, **time-slicing con 2 replicas es óptimo**.

### Si Necesitas Modelos Grandes (70B+)

Tienes 3 opciones:

1. **Desactivar time-slicing** (1 GPU por pod):
   ```bash
   replicas: 1
   ```
   Pero pierdes paralelismo.

2. **Usar tensor parallelism** (multi-GPU por modelo):
   ```bash
   # vLLM con 2 GPUs por modelo
   nvidia.com/gpu: 2
   ```

3. **Pipeline parallelism** (modelo dividido entre GPUs):
   ```python
   # DeepSpeed / Hugging Face Accelerate
   ```

---

## 📚 Referencias

- [NVIDIA Time-Slicing Guide](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)
- [KubeRay + GPU Sharing](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/gpu.html)
- [GPU Operator ClusterPolicy](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/getting-started.html#cluster-policy-options)

---

## 🎯 Próximos Pasos

- ✅ Time-slicing configurado (2 replicas)
- ✅ RayCluster usando 8 GPUs virtuales
- ⬜ Monitorear uso real de VRAM
- ⬜ Ajustar replicas según carga (2/4/8)
- ⬜ Implementar métricas de GPU en Prometheus
