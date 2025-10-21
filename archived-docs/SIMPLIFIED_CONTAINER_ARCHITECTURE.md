# 🎯 Arquitectura Simplificada: Containers sin Ray

## Idea

En lugar de usar Ray (complejo), usar **containers simples** que se comuniquen vía NATS.

---

## 🏗️ Arquitectura Propuesta

```
┌────────────────────────────────────────────────────────────────┐
│                    Kubernetes / Podman                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │             Orchestrator Service                        │   │
│  │                                                          │   │
│  │  Deliberate(task) ──> Publica NATS:                    │   │
│  │                       "agent.task.assigned"             │   │
│  │                       {task_id, description, role}      │   │
│  │                                                          │   │
│  │  GetDeliberationResult(task_id) ──> Query Redis/NATS   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   NATS JetStream                        │   │
│  │                                                          │   │
│  │  Subjects:                                               │   │
│  │  - agent.task.assigned                                   │   │
│  │  - agent.response.completed                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         vLLM Agent Workers (Deployment/StatefulSet)     │   │
│  │                                                          │   │
│  │  Replicas: 3 (o más según carga)                       │   │
│  │                                                          │   │
│  │  Pod 1: ──┐                                             │   │
│  │  Pod 2: ──┼──> Subscribe NATS: agent.task.assigned     │   │
│  │  Pod 3: ──┘    └─> Procesa task                        │   │
│  │                    └─> Llama vLLM                       │   │
│  │                    └─> Publica NATS: agent.response.*  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 vLLM Server (GPU)                       │   │
│  │                                                          │   │
│  │  HTTP API: /v1/chat/completions                        │   │
│  │  Model: Qwen3-0.6B                                      │   │
│  │  GPU: 1x RTX 3090                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo Simplificado

### 1. Cliente → Orchestrator
```python
stub.Deliberate(task="Write factorial", role="DEV", num_agents=3)
```

### 2. Orchestrator → NATS (x3 mensajes)
```json
// Message 1
{
  "task_id": "task-123",
  "agent_id": "agent-dev-001",
  "description": "Write factorial",
  "role": "DEV",
  "constraints": {...},
  "diversity": false
}

// Message 2  
{
  "task_id": "task-123",
  "agent_id": "agent-dev-002",
  "description": "Write factorial",
  "role": "DEV",
  "constraints": {...},
  "diversity": true
}

// Message 3
{...}
```

**Subject**: `agent.task.assigned.DEV` (queue group por rol)

### 3. vLLM Agent Workers → Consume NATS
```
Worker Pod 1 ──> Recibe agent-dev-001 task
               └─> Llama vLLM API
               └─> Publica: agent.response.completed

Worker Pod 2 ──> Recibe agent-dev-002 task
               └─> Llama vLLM API  
               └─> Publica: agent.response.completed

Worker Pod 3 ──> Recibe agent-dev-003 task
               └─> Llama vLLM API
               └─> Publica: agent.response.completed
```

### 4. DeliberationResultCollector → Acumula
```
Escucha: agent.response.completed
Acumula por task_id
Cuando 3/3 ──> Publica: deliberation.completed
```

### 5. Cliente → Consulta
```python
result = stub.GetDeliberationResult(task_id="task-123")
# Retorna las 3 propuestas
```

---

## 💡 Ventajas vs Ray

### Simplicidad
- ✅ No necesita Ray cluster
- ✅ Solo containers simples
- ✅ Fácil de debuggear
- ✅ Menos moving parts

### Escalabilidad
- ✅ Kubernetes Deployment (auto-scaling)
- ✅ HPA basado en queue depth
- ✅ Multiple pods procesando en paralelo

### Compatibilidad
- ✅ Funciona en E2E containers
- ✅ Funciona en K8s
- ✅ Funciona en Podman
- ✅ No requiere Ray operators

---

## 🛠️ Implementación

### vLLM Agent Worker Container

```python
# src/swe_ai_fleet/orchestrator/workers/vllm_agent_worker.py

import asyncio
import json
import nats
import aiohttp


class VLLMAgentWorker:
    """
    Simple worker que consume tasks de NATS y ejecuta con vLLM.
    """
    
    def __init__(self, vllm_url, nats_url, role):
        self.vllm_url = vllm_url
        self.nats_url = nats_url
        self.role = role
    
    async def run(self):
        """Main loop: consume NATS, execute, publish."""
        nc = await nats.connect(self.nats_url)
        js = nc.jetstream()
        
        # Subscribe to tasks for this role (queue group)
        await js.subscribe(
            subject=f"agent.task.assigned.{self.role}",
            queue=f"agent-workers-{self.role}",  # Load balancing
            cb=self._handle_task
        )
        
        print(f"✅ Worker started for role {self.role}")
        
        # Keep running
        await asyncio.Event().wait()
    
    async def _handle_task(self, msg):
        """Process a task."""
        data = json.loads(msg.data)
        task_id = data["task_id"]
        agent_id = data["agent_id"]
        description = data["description"]
        
        print(f"[{agent_id}] Processing task {task_id}")
        
        # Call vLLM
        proposal = await self._call_vllm(description, data.get("constraints", {}))
        
        # Publish result
        result = {
            "task_id": task_id,
            "agent_id": agent_id,
            "role": self.role,
            "proposal": proposal,
            "status": "completed"
        }
        
        await msg.ack()
        
        nc = await nats.connect(self.nats_url)
        js = nc.jetstream()
        await js.publish("agent.response.completed", json.dumps(result).encode())
        
        print(f"[{agent_id}] ✅ Completed")
    
    async def _call_vllm(self, task, constraints):
        """Call vLLM API."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "Qwen/Qwen3-0.6B",
                "messages": [
                    {"role": "system", "content": f"You are a {self.role} expert"},
                    {"role": "user", "content": task}
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
            
            async with session.post(
                f"{self.vllm_url}/v1/chat/completions",
                json=payload
            ) as response:
                data = await response.json()
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "author_id": self.agent_id,
                    "author_role": self.role
                }


if __name__ == "__main__":
    import os
    
    worker = VLLMAgentWorker(
        vllm_url=os.getenv("VLLM_URL", "http://vllm-server-service:8000"),
        nats_url=os.getenv("NATS_URL", "nats://nats:4222"),
        role=os.getenv("AGENT_ROLE", "DEV")
    )
    
    asyncio.run(worker.run())
```

### Kubernetes Deployment

```yaml
# deploy/k8s/vllm-agent-workers.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-agent-dev
  namespace: swe-ai-fleet
spec:
  replicas: 3  # 3 workers para role DEV
  selector:
    matchLabels:
      app: vllm-agent
      role: dev
  template:
    metadata:
      labels:
        app: vllm-agent
        role: dev
    spec:
      containers:
      - name: agent-worker
        image: registry.underpassai.com/swe-fleet/vllm-agent-worker:v0.1.0
        env:
        - name: AGENT_ROLE
          value: "DEV"
        - name: VLLM_URL
          value: "http://vllm-server-service:8000"
        - name: NATS_URL
          value: "nats://nats:4222"
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"

---
# Similar deployments para QA, ARCHITECT, DEVOPS, DATA
```

### Modificación en Orchestrator

```python
# En server.py, método Deliberate:

def Deliberate(self, request, context):
    """Envía tasks a NATS para que agents procesen."""
    task_id = str(uuid.uuid4())
    
    # Publicar N tasks a NATS (uno por agent)
    for i in range(request.num_agents or 3):
        agent_id = f"agent-{request.role.lower()}-{i+1:03d}"
        
        task_message = {
            "task_id": task_id,
            "agent_id": agent_id,
            "description": request.task_description,
            "role": request.role,
            "constraints": self._proto_to_dict(request.constraints),
            "diversity": (i > 0),
            "num_agents": request.num_agents or 3
        }
        
        # Publish a NATS
        await self.js.publish(
            subject=f"agent.task.assigned.{request.role}",
            payload=json.dumps(task_message).encode()
        )
    
    # Retornar inmediatamente
    return orchestrator_pb2.DeliberateResponse(
        task_id=task_id,
        # ... resto de campos
    )
```

---

## ✅ Ventajas de esta Arquitectura

### 1. Simplicidad
- ❌ No Ray (no operators, no complejidad)
- ✅ Solo NATS + containers
- ✅ Fácil de entender y debuggear

### 2. Escalabilidad
- ✅ Kubernetes HPA (auto-scaling)
- ✅ Queue depth metrics para scaling
- ✅ Multiple pods en paralelo

### 3. Fault Tolerance
- ✅ K8s restart policy
- ✅ NATS redelivery si falla
- ✅ Liveness/readiness probes

### 4. Testing
- ✅ Funciona en E2E containers
- ✅ Funciona en K8s
- ✅ Fácil local testing

---

## 🚀 Próximos Pasos

¿Quieres que implemente esta arquitectura simplificada? Sería:

1. **Crear `VLLMAgentWorker`** (container simple NATS consumer)
2. **Dockerfile** para el worker
3. **Deployment K8s** para workers (uno por rol)
4. **Modificar Orchestrator** para publicar tasks a NATS
5. **Mantener DeliberationResultCollector** (ya funciona)

**Ventajas**:
- ✅ Más simple que Ray
- ✅ Funciona en E2E containers
- ✅ Fácil de escalar en K8s
- ✅ Compatible con Podman/CRI-O

¿Vamos con esta arquitectura? 🚀

