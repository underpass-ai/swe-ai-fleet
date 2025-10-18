# 🔍 Estado de Integración: vLLM + Ray + Microservicios

**Fecha**: 16 de Octubre de 2025, 22:30  
**Objetivo**: Verificar integración completa de vLLM con KubeRay y microservicios

---

## ✅ COMPONENTES VERIFICADOS

### 1. vLLM Server
```
✅ Pod: vllm-server-856489758-wbv4g (Running, 3h34m)
✅ Service: vllm-server-service (ClusterIP 10.97.216.94:8000)
✅ Model: Qwen/Qwen3-0.6B
✅ Max context: 40960 tokens
✅ Status: Healthy
```

---

### 2. Ray Cluster
```
✅ Namespace: ray
✅ Cluster: ray-gpu (ready, 12d uptime)
✅ Ray Version: 2.49.2
✅ Head: ray-gpu-head-nbgmw (Running)
✅ Workers: 2/2 Running (cmzjx, vpwh9)
✅ Resources: 2 GPUs, 8 CPUs, 128Gi RAM
```

---

### 3. Orchestrator Service
```
✅ Version: v0.8.1 (gRPC async + Pull Consumers)
✅ Pods: 2/2 Running
✅ AGENT_TYPE: vllm
✅ VLLM_URL: http://vllm-server-service.swe-ai-fleet.svc.cluster.local:8000
✅ VLLM_MODEL: Qwen/Qwen3-0.6B
✅ RAY_ADDRESS: ray://ray-gpu-head-svc.ray.svc.cluster.local:10001
```

---

## 🔌 CONECTIVIDAD VERIFICADA

### Orchestrator → vLLM
```bash
✅ Status: 200 OK
✅ Model disponible: Qwen/Qwen3-0.6B
✅ Latencia: <100ms
```

### Ray Workers → vLLM
```bash
✅ Status: 200 OK
✅ Acceso cross-namespace: Funcional
```

### Ray Workers → NATS
```bash
✅ Puerto 4222: Connected
✅ Service: nats.swe-ai-fleet.svc.cluster.local
```

---

## ❌ PROBLEMA CRÍTICO ENCONTRADO

### Dependencias Faltantes en Ray Workers

**Verificación realizada**:
```bash
kubectl exec -n ray ray-gpu-gpu-workers-worker-cmzjx -- python3 -c "import nats"
```

**Resultado**:
```
ModuleNotFoundError: No module named 'nats'
```

### Dependencias Actuales en Ray Workers

| Paquete | Versión | Estado |
|---------|---------|--------|
| **ray** | 2.49.2 | ✅ Instalado |
| **requests** | 2.32.3 | ✅ Instalado |
| **aiohttp** | 3.11.16 | ✅ Instalado |
| **nats-py** | - | ❌ **FALTANTE** |
| **Python** | 3.9.23 | ✅ Compatible |

### Dependencias Requeridas por VLLMAgentJob

**Archivo**: `src/swe_ai_fleet/orchestrator/ray_jobs/vllm_agent_job.py:186`

```python
async def run(self, task_id, task_description, constraints):
    try:
        # Import NATS here to avoid dependency issues
        import nats                      # ← REQUERIDO
        from nats.js import JetStreamContext  # ← REQUERIDO
        
        # Connect to NATS
        nats_client = await nats.connect(self.nats_url)
        js: JetStreamContext = nats_client.jetstream()
        
        # ... ejecutar tarea ...
        
        # Publish results to NATS
        await js.publish(
            subject="agent.response.completed",
            payload=json.dumps(result).encode(),
        )
```

**Dependencias completas**:
1. ✅ `ray` - Framework distribuido
2. ✅ `aiohttp` - HTTP async client para vLLM API
3. ✅ `requests` - HTTP client (fallback)
4. ❌ `nats-py` - **CRÍTICO**: Para publicar resultados
5. ⚠️ `VLLMAgent` dependencies (si `enable_tools=True`):
   - `swe_ai_fleet.agents.vllm_agent`
   - `swe_ai_fleet.tools.*` (git, file, test, etc.)

---

## 🚨 IMPACTO

### Sin nats-py en Ray Workers:

```
Ray Job inicia → VLLMAgent genera propuesta → 
Intenta importar nats → ModuleNotFoundError → 
Job falla → No se publican resultados → 
Orchestrator nunca recibe respuesta
```

**Estado actual**: 
- ✅ Ray jobs SE PUEDEN CREAR
- ❌ Ray jobs FALLARÁN al intentar publicar a NATS
- ❌ Sistema NO está funcional para deliberaciones distribuidas

---

## 🛠️ SOLUCIÓN

### Opción 1: Imagen Custom de Ray (RECOMENDADO)

**Crear imagen con todas las dependencias**:

```dockerfile
# Dockerfile.ray-swe-fleet
FROM docker.io/rayproject/ray:2.49.2

# Instalar dependencias del proyecto
RUN pip install --no-cache-dir \
    nats-py==2.10.0 \
    aiohttp==3.11.16 \
    requests==2.32.3

# Opcional: Instalar swe_ai_fleet si se usa enable_tools=True
COPY src/ /app/src/
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

ENV PYTHONPATH=/app/src:/app
```

**Build y push**:
```bash
podman build -t registry.underpassai.com/swe-fleet/ray:2.49.2-swe -f Dockerfile.ray-swe-fleet .
podman push registry.underpassai.com/swe-fleet/ray:2.49.2-swe
```

**Actualizar RayCluster**:
```yaml
spec:
  headGroupSpec:
    template:
      spec:
        containers:
          - name: ray-head
            image: registry.underpassai.com/swe-fleet/ray:2.49.2-swe
  
  workerGroupSpecs:
    - groupName: gpu-workers
      template:
        spec:
          containers:
            - name: ray-worker
              image: registry.underpassai.com/swe-fleet/ray:2.49.2-swe
```

---

### Opción 2: Runtime Environment (Temporal)

**Instalar en runtime** (más lento, menos confiable):

```python
# En DeliberateAsync.execute()
runtime_env = {
    "pip": ["nats-py==2.10.0"]
}

agent_actor = VLLMAgentJob.options(
    runtime_env=runtime_env
).remote(...)
```

**Desventajas**:
- ❌ Slow primera ejecución (instala cada vez)
- ❌ No garantiza versiones
- ❌ Puede fallar si no hay internet

---

### Opción 3: Manual Install (NO RECOMENDADO)

```bash
# Instalar manualmente en cada worker (NO PERSISTENTE)
kubectl exec -n ray ray-gpu-gpu-workers-worker-cmzjx -- pip install nats-py
```

**Problemas**:
- ❌ No persiste al reiniciar pods
- ❌ Requiere instalación en todos los workers
- ❌ No es reproducible

---

## 📋 PLAN DE ACCIÓN

### Paso 1: Crear imagen custom de Ray ✅

```bash
# 1. Crear Dockerfile
cat > Dockerfile.ray-swe-fleet << 'EOF'
FROM docker.io/rayproject/ray:2.49.2

# Install NATS client (CRÍTICO)
RUN pip install --no-cache-dir \
    nats-py==2.10.0

# Opcional: otras dependencias si se necesitan
# RUN pip install --no-cache-dir \
#     anthropic \
#     openai

ENV PYTHONPATH=/app
EOF

# 2. Build
podman build -t registry.underpassai.com/swe-fleet/ray:2.49.2-nats \
  -f Dockerfile.ray-swe-fleet .

# 3. Push
podman push registry.underpassai.com/swe-fleet/ray:2.49.2-nats

# 4. Actualizar RayCluster
kubectl patch raycluster ray-gpu -n ray --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/headGroupSpec/template/spec/containers/0/image",
    "value": "registry.underpassai.com/swe-fleet/ray:2.49.2-nats"
  },
  {
    "op": "replace",
    "path": "/spec/workerGroupSpecs/0/template/spec/containers/0/image",
    "value": "registry.underpassai.com/swe-fleet/ray:2.49.2-nats"
  }
]'

# 5. Restart workers para aplicar nueva imagen
kubectl delete pod -n ray -l groupName=gpu-workers
```

---

### Paso 2: Verificar instalación ✅

```bash
# Esperar a que workers reinicien
kubectl wait --for=condition=Ready pod -l groupName=gpu-workers -n ray --timeout=120s

# Verificar nats-py instalado
kubectl exec -n ray <nuevo-worker-pod> -- python3 -c "import nats; print(f'✅ nats v{nats.__version__}')"
```

---

### Paso 3: Test E2E con VLLMAgentJob ✅

```python
# Crear script de test
python tests/e2e/test_vllm_agent_job_with_nats.py
```

**Verificar**:
1. Ray job se crea sin errores
2. vLLM genera respuesta
3. Resultados se publican a NATS
4. Orchestrator recibe respuesta

---

## 📊 CHECKLIST DE INTEGRACIÓN

### Infraestructura
- [x] vLLM server deployed y accesible
- [x] Ray cluster deployed (head + workers)
- [x] NATS JetStream deployed
- [x] Conectividad cross-namespace (ray → swe-ai-fleet)

### Configuración
- [x] Orchestrator apunta a vLLM correcto
- [x] Orchestrator apunta a Ray cluster correcto
- [x] Ray workers acceden a vLLM
- [x] Ray workers acceden a NATS

### Dependencias
- [x] Ray 2.49.2 en workers
- [x] aiohttp en workers
- [x] requests en workers
- [ ] **nats-py en workers** ← PENDIENTE (CRÍTICO)

### Testing
- [ ] Ray job puede importar nats
- [ ] VLLMAgentJob puede conectar a NATS
- [ ] VLLMAgentJob puede publicar resultados
- [ ] Orchestrator recibe resultados de Ray jobs

---

## 🎯 PRÓXIMOS PASOS

1. **AHORA**: Crear imagen custom de Ray con nats-py
2. **AHORA**: Actualizar RayCluster para usar nueva imagen
3. **AHORA**: Verificar nats-py instalado en workers
4. **DESPUÉS**: Ejecutar test E2E completo
5. **DESPUÉS**: Crear councils y probar deliberación real

---

## 📚 REFERENCIAS

- RayCluster actual: `namespace: ray`, `name: ray-gpu`
- Código VLLMAgentJob: `src/swe_ai_fleet/orchestrator/ray_jobs/vllm_agent_job.py`
- Documentación: `docs/infrastructure/RAYCLUSTER_INTEGRATION.md`
- Tests: `tests/integration/services/orchestrator/test_ray_vllm_integration.py`

