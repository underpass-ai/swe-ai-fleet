# 🏗️ Arquitectura: Agents vs Modelos LLM

**Fecha**: 16 de Octubre de 2025  
**Aclaración**: Diferencia entre "agents" y "modelos" en el sistema

---

## 📊 ESTADO ACTUAL

### GPU Usage Verificado

```
vLLM Server (GPU 0 - RTX 3090):
  Memoria usada: 23.4 GB / 24 GB (95%)
  Utilización: 0% (idle, esperando requests)
  Modelo cargado: Qwen/Qwen3-0.6B
```

---

## 🔍 ARQUITECTURA REAL

### Configuración Actual: 1 Modelo Compartido

```
┌─────────────────────────────────────────────────────────────────┐
│                    vLLM Server (1 GPU)                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Qwen/Qwen3-0.6B (cargado en VRAM: 23.4 GB)              │  │
│  │  Batch size: 64                                           │  │
│  │  Max model len: 40960 tokens                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Endpoint: http://vllm-server-service:8000/v1/chat/completions │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ HTTP Requests (OpenAI API compatible)
                           │
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
   ┌─────────┐       ┌─────────┐       ┌─────────┐
   │ Agent 1 │       │ Agent 2 │  ...  │Agent 15 │
   │ (DEV)   │       │ (QA)    │       │ (DATA)  │
   └─────────┘       └─────────┘       └─────────┘
   
   Objetos Python AsyncVLLMAgent:
     - Memoria: ~3-5 MB cada uno
     - CPU: Mínimo (solo HTTP calls)
     - GPU: 0 GB (no cargan modelos)
     - Ubicación: En pods de Orchestrator
```

**Explicación**:

1. **1 Modelo en vLLM** = Qwen/Qwen3-0.6B (23.4 GB VRAM)
2. **15 Agents** = 15 objetos Python que llaman a ese mismo modelo
3. **Compartido**: Todos los agents usan el mismo endpoint

---

## 🔄 FLUJO DE INFERENCIA

### Cuando un Agent "Piensa":

```python
# Agent DEV-001 recibe tarea
agent = AsyncVLLMAgent(
    agent_id="agent-dev-001",
    role="DEV",
    vllm_url="http://vllm-server-service:8000",  # ← Shared endpoint
    model="Qwen/Qwen3-0.6B"
)

# Agent hace HTTP request
response = await agent.generate(task="Add /health endpoint")

# Internamente:
async def generate(self, task):
    # HTTP POST a vLLM server
    payload = {
        "model": "Qwen/Qwen3-0.6B",
        "messages": [{"role": "user", "content": task}],
        "temperature": 0.7
    }
    
    response = await aiohttp.post(
        "http://vllm-server-service:8000/v1/chat/completions",
        json=payload
    )
    
    return response.json()["choices"][0]["message"]["content"]
```

**Resultado**:
- vLLM server recibe request
- Usa el modelo YA CARGADO en GPU
- Genera respuesta
- Retorna al agent
- **NO se carga ningún modelo nuevo**

---

## ⚡ PARALELISMO ACTUAL

### Con 1 vLLM Server:

```
Request Timeline (si 3 agents deliberan simultáneamente):

Agent DEV-001 → vLLM (request 1) → espera en queue
Agent DEV-002 → vLLM (request 2) → espera en queue  
Agent DEV-003 → vLLM (request 3) → espera en queue

vLLM procesa:
  └→ Batch de hasta 64 requests simultáneos
     ├→ Request 1: genera en 2s
     ├→ Request 2: genera en 2s (paralelo con batch)
     └→ Request 3: genera en 2s (paralelo con batch)

Total: ~2-3 segundos para 3 agents (batch processing)
```

**Throughput real**: ~20-30 agents/minuto (depende de longitud de respuesta)

---

## 🚀 OPCIONES PARA ESCALAR

### Opción 1: Múltiples vLLM Servers (RECOMENDADO)

**Setup**: 1 vLLM server por rol, cada uno en su GPU

```yaml
# 5 deployments de vLLM:
- vllm-dev: GPU 0 (Qwen3-0.6B optimizado para código)
- vllm-qa: GPU 1 (Qwen3-0.6B optimizado para testing)
- vllm-architect: GPU 2 (Modelo más grande para decisiones)
- vllm-devops: GPU 3 (Qwen3-0.6B)
- vllm-data: GPU 4 (Modelo especializado en SQL/datos)
```

**Beneficios**:
- ✅ 5 modelos en paralelo real
- ✅ Modelos especializados por rol
- ✅ No hay queue contention
- ✅ Fácil de configurar

**Costo GPU**: 5 GPUs (tienes 4 físicas, puedes usar MIG)

---

### Opción 2: vLLM con Tensor Parallelism

**Setup**: 1 modelo grande distribuido en múltiples GPUs

```bash
# vLLM con 4 GPUs
vllm serve \
  --model "deepseek-ai/deepseek-coder-33b-instruct" \
  --tensor-parallel-size 4
```

**Beneficios**:
- ✅ Modelo más grande y capaz
- ✅ Mayor throughput (4x)
- ✅ Latencia reducida

**Desventajas**:
- ❌ Solo 1 modelo para todos los roles
- ❌ No especialización por rol

---

### Opción 3: Ray Serve con Model Replicas

**Setup**: Mismo modelo replicado N veces

```python
# Ray Serve deployment
@serve.deployment(num_replicas=4)
class VLLMDeployment:
    def __init__(self):
        self.model = load_model("Qwen3-0.6B")
    
    async def generate(self, prompt):
        return await self.model.generate(prompt)
```

**Beneficios**:
- ✅ Throughput escalable (4x)
- ✅ Load balancing automático
- ✅ Failover si un replica falla

**Desventajas**:
- ❌ 4 copias del mismo modelo (4 x 23 GB = 92 GB)
- ❌ Solo puedes tener 4 replicas con 4 GPUs

---

## 🎯 RECOMENDACIÓN PARA TU HARDWARE

**Hardware**: 4x RTX 3090 (24 GB cada una) = 96 GB VRAM total

### Setup Óptimo: 4 vLLM Servers Especializados

```
GPU 0: vllm-dev (Qwen3-0.6B) - 23 GB
GPU 1: vllm-qa (Qwen3-0.6B) - 23 GB
GPU 2: vllm-architect (Qwen-14B o similar) - 23 GB
GPU 3: vllm-data (Qwen3-0.6B) - 23 GB

Total: 92 GB / 96 GB disponibles
```

**Configuración de Agents**:
```python
# Cada rol apunta a su vLLM server
agents_dev = [
    AsyncVLLMAgent(vllm_url="http://vllm-dev:8000"),
    AsyncVLLMAgent(vllm_url="http://vllm-dev:8000"),
    AsyncVLLMAgent(vllm_url="http://vllm-dev:8000"),
]

agents_qa = [
    AsyncVLLMAgent(vllm_url="http://vllm-qa:8000"),
    ...
]
```

**Beneficio**:
- 4 deliberaciones en paralelo REAL (1 por GPU)
- Latencia reducida 4x
- Modelos optimizados por rol

---

## 📊 COMPARACIÓN DE THROUGHPUT

| Setup | GPUs | Agents Paralelos | Latencia/Agent | Throughput |
|-------|------|------------------|----------------|------------|
| **Actual** (1 vLLM) | 1 | 64 (batch) | 2s | ~30 agents/min |
| **Opción 1** (4 vLLM) | 4 | 4 reales | 2s | ~120 agents/min |
| **Opción 2** (Tensor Parallel) | 4 | 64 (batch) | 0.5s | ~120 agents/min |
| **Opción 3** (Ray Serve 4x) | 4 | 4 reales | 2s | ~120 agents/min |

---

## ✅ ESTADO ACTUAL CORRECTO

Tu observación es correcta: **solo usas 1 GPU porque solo hay 1 vLLM server**.

Los 15 agents son:
- ❌ NO son 15 modelos
- ❌ NO cargan nada en GPU
- ✅ SÍ son 15 "cerebros" diferentes (diversidad en prompts/temperature)
- ✅ SÍ pueden deliberar en paralelo (hasta 64 en batch)
- ✅ SÍ comparten eficientemente 1 modelo

**Esto es CORRECTO para empezar**, pero para escalar necesitarás más vLLM servers.


