# Ray + vLLM Asynchronous Integration Plan

## 🎯 Objetivo

Integrar agentes vLLM para que se ejecuten como **Ray Jobs asíncronos** en KubeRay, con comunicación vía NATS.

---

## 🏗️ Arquitectura Actual vs Correcta

### ❌ Arquitectura Actual (Síncrona)

```
┌─────────────┐
│ Orchestrator│
│   gRPC      │
└──────┬──────┘
       │ Deliberate(task)
       ▼
┌────────────────────┐
│  Deliberate        │
│  Use Case          │
│                    │
│  for agent in agents:
│    response = agent.generate()  ← BLOQUEA aquí
│    results.append(response)
│                    │
│  return results    │
└────────────────────┘
```

**Problemas**:
- ❌ Bloquea el Orchestrator mientras espera respuestas
- ❌ No escala (no usa Ray cluster)
- ❌ No aprovecha GPUs distribuidas
- ❌ Timeout del gRPC request

---

### ✅ Arquitectura Correcta (Asíncrona con Ray + NATS)

```
┌──────────────────┐         ┌─────────────────┐         ┌──────────────────┐
│  Orchestrator    │         │   Ray Cluster   │         │   NATS JetStream │
│   gRPC Server    │         │   (KubeRay)     │         │                  │
└────────┬─────────┘         └────────┬────────┘         └────────┬─────────┘
         │                            │                           │
         │ 1. Deliberate(task)        │                           │
         │                            │                           │
         │ 2. Submit Ray Jobs         │                           │
         ├───────────────────────────►│                           │
         │    - AgentJob(agent-1)     │                           │
         │    - AgentJob(agent-2)     │                           │
         │    - AgentJob(agent-3)     │                           │
         │                            │                           │
         │ 3. Return job_id           │                           │
         │◄───────────────────────────┤                           │
         │                            │                           │
         │                            │ 4. Execute jobs in Ray    │
         │                            │    (each job uses vLLM)   │
         │                            │                           │
         │                            │ 5. Publish result         │
         │                            ├──────────────────────────►│
         │                            │   agent.response.completed│
         │                            │                           │
         │ 6. Subscribe to NATS       │                           │
         │◄───────────────────────────┼───────────────────────────┤
         │    agent.response.completed│                           │
         │                            │                           │
         │ 7. Collect all responses   │                           │
         │                            │                           │
         │ 8. Publish final result    │                           │
         ├────────────────────────────┼──────────────────────────►│
         │   deliberation.completed   │                           │
         │                            │                           │
```

**Ventajas**:
- ✅ No bloquea el Orchestrator
- ✅ Usa Ray cluster para distribución
- ✅ Aprovecha múltiples GPUs en paralelo
- ✅ Escalable a cientos de agentes
- ✅ Fault tolerance (Ray reinicia jobs fallidos)

---

## 📋 Componentes a Implementar

### 1. Ray Job: `VLLMAgentJob`

**Ubicación**: `src/swe_ai_fleet/orchestrator/ray_jobs/vllm_agent_job.py`

```python
import ray
import aiohttp
from typing import Any

@ray.remote(num_cpus=1)
class VLLMAgentJob:
    """
    Ray job que ejecuta un agente vLLM y publica resultados en NATS.
    """
    def __init__(
        self,
        agent_id: str,
        role: str,
        vllm_url: str,
        model: str,
        nats_url: str,
    ):
        self.agent_id = agent_id
        self.role = role
        self.vllm_url = vllm_url
        self.model = model
        self.nats_url = nats_url
        self.nats_client = None  # Inicializar en run()
    
    async def run(
        self,
        task_id: str,
        task_description: str,
        constraints: dict[str, Any],
        diversity: bool = False,
    ) -> dict[str, Any]:
        """
        Ejecuta el agente vLLM y publica el resultado en NATS.
        """
        import nats
        from nats.js import JetStreamContext
        
        # 1. Conectar a NATS
        self.nats_client = await nats.connect(self.nats_url)
        js: JetStreamContext = self.nats_client.jetstream()
        
        try:
            # 2. Generar propuesta usando vLLM
            proposal = await self._generate_proposal(
                task_description, constraints, diversity
            )
            
            # 3. Preparar resultado
            result = {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "role": self.role,
                "proposal": proposal,
                "status": "completed",
                "timestamp": ...,
            }
            
            # 4. Publicar en NATS
            await js.publish(
                subject="agent.response.completed",
                payload=json.dumps(result).encode(),
            )
            
            return result
            
        except Exception as e:
            # Publicar error
            error_result = {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "status": "failed",
                "error": str(e),
            }
            await js.publish(
                subject="agent.response.failed",
                payload=json.dumps(error_result).encode(),
            )
            raise
        
        finally:
            await self.nats_client.close()
    
    async def _generate_proposal(
        self, task: str, constraints: dict, diversity: bool
    ) -> dict:
        """
        Llama a vLLM API para generar propuesta.
        """
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._build_system_prompt(constraints)},
                    {"role": "user", "content": self._build_task_prompt(task, constraints)}
                ],
                "temperature": 0.9 if diversity else 0.7,
                "max_tokens": 2048,
            }
            
            async with session.post(
                f"{self.vllm_url}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                content = data["choices"][0]["message"]["content"]
                
                return {
                    "content": content,
                    "author_id": self.agent_id,
                    "author_role": self.role,
                }
```

---

### 2. Orchestrator: `DeliberateAsyncUseCase`

**Ubicación**: `src/swe_ai_fleet/orchestrator/usecases/deliberate_async_usecase.py`

```python
from typing import Any
import ray
from ray.job_submission import JobSubmissionClient


class DeliberateAsync:
    """
    Use case asíncrono para deliberación usando Ray Jobs.
    """
    def __init__(
        self,
        ray_address: str,
        vllm_url: str,
        model: str,
        nats_url: str,
    ):
        self.ray_address = ray_address
        self.vllm_url = vllm_url
        self.model = model
        self.nats_url = nats_url
        # No conectar aquí, solo en execute
    
    def execute(
        self,
        task_id: str,
        task_description: str,
        role: str,
        num_agents: int,
        constraints: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Envía jobs de agentes a Ray y retorna inmediatamente.
        
        Returns:
            Dictionary con job_ids para tracking
        """
        # Conectar a Ray
        ray.init(address=self.ray_address, ignore_reinit_error=True)
        
        job_ids = []
        
        # Crear y enviar jobs para cada agente
        for i in range(num_agents):
            agent_id = f"agent-{role.lower()}-{i+1:03d}"
            
            # Crear Ray remote actor
            agent_job = VLLMAgentJob.remote(
                agent_id=agent_id,
                role=role,
                vllm_url=self.vllm_url,
                model=self.model,
                nats_url=self.nats_url,
            )
            
            # Enviar job (no esperar resultado)
            job_ref = agent_job.run.remote(
                task_id=task_id,
                task_description=task_description,
                constraints=constraints,
                diversity=(i > 0),  # Primer agente sin diversity, resto con diversity
            )
            
            job_ids.append(job_ref)
        
        return {
            "task_id": task_id,
            "job_ids": job_ids,
            "num_agents": num_agents,
            "status": "submitted",
        }
```

---

### 3. NATS Consumer: `DeliberationResultCollector`

**Ubicación**: `services/orchestrator/consumers/deliberation_collector.py`

```python
import asyncio
from collections import defaultdict
from typing import Any

import nats
from nats.js import JetStreamContext


class DeliberationResultCollector:
    """
    Consumer que escucha resultados de agentes y publica resultado final
    cuando todos los agentes han respondido.
    """
    def __init__(self, nats_url: str):
        self.nats_url = nats_url
        self.nc = None
        self.js: JetStreamContext = None
        # Track de deliberaciones en progreso
        self.pending_deliberations: dict[str, dict] = defaultdict(dict)
    
    async def start(self):
        """Conectar a NATS y subscribirse a agent responses."""
        self.nc = await nats.connect(self.nats_url)
        self.js = self.nc.jetstream()
        
        # Subscribe a agent responses
        await self.js.subscribe(
            subject="agent.response.completed",
            cb=self._handle_agent_response,
            stream="AGENT_RESPONSES",
            durable="deliberation-collector",
        )
        
        await self.js.subscribe(
            subject="agent.response.failed",
            cb=self._handle_agent_failure,
            stream="AGENT_RESPONSES",
            durable="deliberation-collector-failures",
        )
    
    async def _handle_agent_response(self, msg):
        """Procesa respuesta de un agente."""
        data = json.loads(msg.data.decode())
        task_id = data["task_id"]
        agent_id = data["agent_id"]
        
        # Guardar resultado
        if task_id not in self.pending_deliberations:
            self.pending_deliberations[task_id] = {
                "results": [],
                "expected_count": None,  # Se setea en el primer mensaje
                "received_count": 0,
            }
        
        deliberation = self.pending_deliberations[task_id]
        deliberation["results"].append(data["proposal"])
        deliberation["received_count"] += 1
        
        # Si es el primer mensaje, extraer expected_count
        if "num_agents" in data:
            deliberation["expected_count"] = data["num_agents"]
        
        # Verificar si ya tenemos todos los resultados
        if (
            deliberation["expected_count"] is not None
            and deliberation["received_count"] >= deliberation["expected_count"]
        ):
            await self._publish_deliberation_complete(task_id, deliberation)
        
        await msg.ack()
    
    async def _handle_agent_failure(self, msg):
        """Procesa fallo de un agente."""
        data = json.loads(msg.data.decode())
        task_id = data["task_id"]
        
        # Log error
        logger.error(f"Agent {data['agent_id']} failed for task {task_id}: {data['error']}")
        
        # Aún así contar como respuesta recibida
        if task_id in self.pending_deliberations:
            self.pending_deliberations[task_id]["received_count"] += 1
        
        await msg.ack()
    
    async def _publish_deliberation_complete(self, task_id: str, deliberation: dict):
        """Publica resultado final de deliberación."""
        result = {
            "task_id": task_id,
            "results": deliberation["results"],
            "total_agents": deliberation["expected_count"],
            "successful_responses": len(deliberation["results"]),
            "timestamp": ...,
        }
        
        await self.js.publish(
            subject="deliberation.completed",
            payload=json.dumps(result).encode(),
        )
        
        # Limpiar tracking
        del self.pending_deliberations[task_id]
        
        logger.info(f"✅ Deliberation completed for task {task_id}")
```

---

### 4. Orchestrator gRPC: Modificar `Deliberate` RPC

**Ubicación**: `services/orchestrator/server.py`

```python
def Deliberate(self, request, context):
    """
    Inicia deliberación asíncrona y retorna inmediatamente.
    """
    task_id = str(uuid.uuid4())
    
    # Enviar jobs a Ray
    result = self.deliberate_async.execute(
        task_id=task_id,
        task_description=request.task_description,
        role=request.role,
        num_agents=request.num_agents or 3,
        constraints=self._constraints_from_proto(request.constraints),
    )
    
    # Retornar inmediatamente con job_id
    return orchestrator_pb2.DeliberateResponse(
        task_id=task_id,
        status="SUBMITTED",
        message=f"Deliberation submitted to Ray cluster with {result['num_agents']} agents",
        # No retornamos resultados aquí, se obtendrán vía NATS
    )
```

**Nuevo RPC para obtener resultados**:

```protobuf
// specs/orchestrator.proto

rpc GetDeliberationResult(GetDeliberationResultRequest) returns (GetDeliberationResultResponse);

message GetDeliberationResultRequest {
  string task_id = 1;
}

message GetDeliberationResultResponse {
  string task_id = 1;
  DeliberationStatus status = 2;  // PENDING, COMPLETED, FAILED
  repeated DeliberationResult results = 3;
  int32 duration_ms = 4;
}

enum DeliberationStatus {
  PENDING = 0;
  COMPLETED = 1;
  FAILED = 2;
}
```

---

## 🔄 Flujo Completo

### Paso 1: Cliente envía Deliberate request
```python
stub.Deliberate(DeliberateRequest(
    task_description="Write factorial function",
    role="DEV",
    num_agents=3,
))
# → Retorna inmediatamente: task_id="uuid-123"
```

### Paso 2: Orchestrator envía jobs a Ray
```python
# 3 Ray jobs creados:
# - agent-dev-001.run()
# - agent-dev-002.run()
# - agent-dev-003.run()
```

### Paso 3: Ray ejecuta jobs en paralelo
```
Ray Worker 1 (GPU 0): agent-dev-001 → vLLM → genera propuesta
Ray Worker 2 (GPU 1): agent-dev-002 → vLLM → genera propuesta
Ray Worker 3 (GPU 2): agent-dev-003 → vLLM → genera propuesta
```

### Paso 4: Cada agente publica en NATS
```
agent-dev-001 → NATS: agent.response.completed
agent-dev-002 → NATS: agent.response.completed
agent-dev-003 → NATS: agent.response.completed
```

### Paso 5: DeliberationResultCollector recibe todas las respuestas
```python
# Cuando received_count == expected_count:
→ NATS: deliberation.completed
```

### Paso 6: Cliente puede consultar resultado
```python
# Opción A: Polling
response = stub.GetDeliberationResult(task_id="uuid-123")

# Opción B: Subscribe a NATS
await js.subscribe("deliberation.completed")
```

---

## 📊 Configuración de Deployment

### Ray Cluster Configuration
```yaml
# deploy/k8s/raycluster-agents.yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: agent-cluster
  namespace: swe-ai-fleet
spec:
  rayVersion: '2.9.0'
  headGroupSpec:
    rayStartParams:
      dashboard-host: '0.0.0.0'
    template:
      spec:
        containers:
        - name: ray-head
          image: registry.underpassai.com/swe-fleet/ray-agents:v0.1.0
          env:
          - name: RAY_memory_monitor_refresh_ms
            value: "0"
          - name: VLLM_URL
            value: "http://vllm-server-service:8000"
          - name: NATS_URL
            value: "nats://nats:4222"
  workerGroupSpecs:
  - replicas: 4
    minReplicas: 2
    maxReplicas: 8
    groupName: agent-workers
    rayStartParams: {}
    template:
      spec:
        containers:
        - name: ray-worker
          image: registry.underpassai.com/swe-fleet/ray-agents:v0.1.0
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
              nvidia.com/gpu: "0"  # No GPU en workers (vLLM ya tiene GPU)
            limits:
              cpu: "4"
              memory: "8Gi"
          env:
          - name: VLLM_URL
            value: "http://vllm-server-service:8000"
          - name: NATS_URL
            value: "nats://nats:4222"
```

### Orchestrator Environment Variables
```yaml
# deploy/k8s/orchestrator-service.yaml
env:
- name: AGENT_TYPE
  value: "ray-vllm"
- name: RAY_ADDRESS
  value: "ray://agent-cluster-head-svc:10001"
- name: VLLM_URL
  value: "http://vllm-server-service:8000"
- name: VLLM_MODEL
  value: "Qwen/Qwen3-0.6B"
- name: NATS_URL
  value: "nats://nats:4222"
```

---

## ✅ Checklist de Implementación

### Fase 1: Ray Job Base
- [ ] Crear `VLLMAgentJob` Ray actor
- [ ] Implementar `generate_proposal` con vLLM API
- [ ] Publicar resultados en NATS
- [ ] Unit tests para VLLMAgentJob

### Fase 2: Orchestrator Async
- [ ] Implementar `DeliberateAsync` use case
- [ ] Modificar `Deliberate` RPC para ser async
- [ ] Añadir `GetDeliberationResult` RPC
- [ ] Integration tests

### Fase 3: NATS Consumer
- [ ] Implementar `DeliberationResultCollector`
- [ ] Integrar en Orchestrator server
- [ ] Manejar timeouts y failures
- [ ] E2E tests

### Fase 4: Deployment
- [ ] Crear Dockerfile para Ray agents
- [ ] Crear RayCluster manifest
- [ ] Deploy a Kubernetes
- [ ] Validar con tests E2E

---

## 🚀 Próximos Pasos

1. **Crear Ray agent image** con vLLM client y NATS
2. **Deploy RayCluster** en `swe-ai-fleet` namespace
3. **Modificar Orchestrator** para usar Ray jobs
4. **Validar E2E** con múltiples agentes

---

¿Empezamos con la Fase 1: implementar `VLLMAgentJob`?

