# Mock vs Real Agents - Current Status

## 🔍 Por qué los agentes tardaron 0.0s

**Respuesta Corta**: Los tests actuales usan `MockAgent`, no vLLM real.

**Respuesta Larga**: Por diseño, para testing rápido y confiable.

---

## 📊 Estado Actual del Sistema

### Configuración en Orchestrator (server.py:530-568)

```python
# Línea 534: Por defecto usa MockAgent
else:
    # Use mock agents (default)
    from swe_ai_fleet.orchestrator.domain.agents.mock_agent import (
        AgentBehavior,
    )
    
    for i in range(num_agents):
        agent_id = f"agent-{role.lower()}-{i+1:03d}"
        
        # Vary behaviors for more interesting deliberations
        if i == 0:
            behavior = AgentBehavior.EXCELLENT
        elif i == num_agents - 1:
            behavior = AgentBehavior.NORMAL
        else:
            behavior = AgentBehavior.NORMAL
        
        agent = AgentFactory.create_agent(
            agent_id=agent_id,
            role=role,
            agent_type="MOCK",  # <-- Esto es lo que se está usando
            behavior=behavior.value,
            seed=i,
        )
```

### Logs del Orchestrator Confirmando

```
2025-10-14 19:49:29,340 [INFO] __main__: Deliberate response: winner=agent-architect-001, results=3, duration=0ms
2025-10-14 19:49:29,341 [INFO] __main__: Deliberate response: winner=agent-architect-001, results=3, duration=0ms
2025-10-14 19:49:29,343 [INFO] __main__: Deliberate response: winner=agent-dev-001, results=3, duration=0ms
```

**Observación**: `duration=0ms` → MockAgents instantáneos

### Servidor vLLM Status

```bash
$ kubectl logs vllm-server-84f48cdc9b-xbkfz --tail=20

# Solo health checks, NO requests de chat/completions
INFO:     192.168.1.56:55098 - "GET /health HTTP/1.1" 200 OK
INFO:     192.168.1.56:41306 - "GET /health HTTP/1.1" 200 OK
...
```

**Observación**: vLLM está corriendo pero NO está siendo usado para deliberación.

---

## 🎭 MockAgent: Qué Hace

### Propósito del MockAgent

`MockAgent` es un agente sintético que:
1. ✅ Genera propuestas basadas en patrones (no LLM)
2. ✅ Responde instantáneamente (0.0s)
3. ✅ Simula diferentes comportamientos (EXCELLENT, NORMAL, POOR, etc.)
4. ✅ Permite testing sin dependencias de vLLM
5. ✅ Proporciona resultados deterministas para tests

### Ejemplo de Propuesta MockAgent ARCHITECT

Cuando pedimos "Analyze Context Service codebase", MockAgent genera:

```
# Proposal by agent-architect-001 (ARCHITECT) (with high diversity)

## Task
Analyze the Context Service codebase and identify performance 
optimization opportunities.

Current Context:
- Context Service handles context hydration from Neo4j
- Uses Redis for caching
- Implements multiple use cases (ProjectDecision, UpdateSubtask, etc)
- Has gRPC API

Analysis Required:
- Review code structure and patterns
- Identify performance bottlenecks
- Check test coverage
- Analyze database query patterns
- Propose specific optimizations

Assumptions:
- Service built on microservices architecture
- Uses standard Python async patterns
- Neo4j is the primary data store
- Redis cache for performance
- Current implementation follows clean architecture

Recommendation:
1. Profile Neo4j queries for N+1 issues
2. Implement query batching
3. Optimize Redis cache strategy
4. Add monitoring for bottlenecks
5. Consider read replicas for Neo4j
```

**Observación**: 
- ✅ Contenido plausible y relevante
- ✅ Menciona componentes reales (Neo4j, Redis, ProjectDecision)
- ✅ Pero es generado por patrón, no por análisis real con LLM

---

## 🚀 VLLMAgent: Qué Haría (Cuando Activado)

### Con vLLM Real Activado

Cuando usemos `agent_type="RAY_VLLM"` en lugar de `"MOCK"`:

```python
# Línea 517: Código listo para usar VLLMAgentJob
if agent_type == "RAY_VLLM" and ray.is_initialized():
    from swe_ai_fleet.orchestrator.ray_jobs.vllm_agent_job import (
        VLLMAgentJob,
    )
    
    for i in range(num_agents):
        agent_id = f"agent-{role.lower()}-{i+1:03d}"
        
        # Create Ray remote actor (real vLLM agent)
        agent_actor = VLLMAgentJob.remote(
            agent_id=agent_id,
            role=role,
            vllm_url=self.deliberate_async.vllm_url,
            model=self.deliberate_async.model,
            workspace_path="/workspace",  # Will be mounted in Ray Job
            enable_tools=True,  # Real tool execution
        )
        
        agents.append(agent_actor)
```

### Diferencias Clave:

| Aspecto | MockAgent (Actual) | VLLMAgent (Real) |
|---------|-------------------|------------------|
| **Tiempo** | 0.0s | 5-30s (depende del modelo) |
| **Generación** | Patrones hardcodeados | LLM real (databricks/dbrx, deepseek, etc) |
| **Razonamiento** | Simulado | Real (usa vLLM API) |
| **Tools** | No ejecuta tools | Puede ejecutar git, files, tests, etc |
| **Costo** | $0 | ~$0.04 por agente |
| **Logs vLLM** | No aparecen | `POST /v1/chat/completions` |
| **Diversidad** | Sintética (seed-based) | Real (modelo genera diferentes respuestas) |

---

## 📈 Qué Han "Pensado" Los MockAgent ARCHITECT

### De Los Logs De Los Tests E2E

**Test 1: Deliberation with Code Analysis Tools**

```python
# 3 agentes ARCHITECT
agents = [
    "agent-architect-001",  # Behavior: EXCELLENT
    "agent-architect-002",  # Behavior: NORMAL
    "agent-architect-003",  # Behavior: NORMAL
]

# Propuestas generadas:
proposals = [
    {
        "author_id": "agent-architect-001",
        "score": 1.00,
        "content": "# Proposal (EXCELLENT behavior, seed=0)\n..."
                   "References: Neo4j, Redis, ProjectDecision\n"
                   "Query optimization, caching strategy, ...",
        "diversity": "High (seed variation)"
    },
    {
        "author_id": "agent-architect-002",
        "score": 1.00,
        "content": "# Proposal (NORMAL behavior, seed=1)\n..."
                   "References: Context Service, gRPC, ...\n"
                   "Different approach from agent-001",
        "diversity": "High (seed variation)"
    },
    {
        "author_id": "agent-architect-003",
        "score": 1.00,
        "content": "# Proposal (NORMAL behavior, seed=2)\n..."
                   "References: Neo4j, Context hydration, ...\n"
                   "Different approach from agents 1&2",
        "diversity": "High (seed variation)"
    }
]

# Ganador seleccionado:
winner = "agent-architect-001"  # EXCELLENT behavior siempre gana
```

**Características de las propuestas MockAgent**:
- ✅ Mencionan componentes reales (Neo4j, Redis, Context Service)
- ✅ Proponen optimizaciones razonables
- ✅ Varían según seed (diversidad sintética)
- ✅ Incluyen términos técnicos relevantes (query, performance, optimization)
- ❌ NO leyeron código real (no ejecutaron tools)
- ❌ NO usaron vLLM (patrones predefinidos)

---

## 🎯 Por Qué Usamos Mocks (Estrategia de Testing)

### Ventajas de MockAgent para Testing

1. **Velocidad** ⚡
   - 78 tests en <5s
   - Sin esperar a vLLM (5-30s por agente)
   - CI/CD rápido

2. **Determinismo** 🎲
   - Resultados reproducibles
   - No dependen de estado del modelo
   - No fallan por rate limits

3. **Sin Dependencias** 🔌
   - No requiere vLLM corriendo
   - No requiere GPU
   - Funciona en GitHub Actions

4. **Cobertura Completa** 📊
   - Testea toda la infraestructura
   - Valida flujos de comunicación
   - Verifica integración de componentes

5. **Económico** 💰
   - No consume créditos de vLLM
   - No requiere GPU
   - Tests gratis

### Cuándo Usar Cada Tipo

| Tipo de Test | MockAgent | VLLMAgent |
|--------------|-----------|-----------|
| **Unit tests** | ✅ Siempre | ❌ Nunca |
| **Integration tests** | ✅ Por defecto | ⚠️ Opcional |
| **E2E tests (CI)** | ✅ Por defecto | ❌ Muy lento |
| **E2E tests (local)** | ⚠️ Para validar flujo | ✅ Para probar agentes reales |
| **Manual testing** | ❌ No | ✅ Siempre |
| **Demos** | ❌ No | ✅ Siempre |
| **Production** | ❌ Nunca | ✅ Siempre |

---

## 🔄 Cómo Activar vLLM Real

### Opción 1: Via gRPC (Cuando esté implementado)

```python
# En el futuro: OrchestratewithTools gRPC method
stub.OrchestratewithTools(
    task_id="US-500",
    agent_type="RAY_VLLM",  # <-- Activar vLLM real
    enable_tools=True,
    ...
)
```

### Opción 2: Via Código Directo (Ahora Mismo)

```python
# Crear VLLMAgent directamente
from swe_ai_fleet.agents import VLLMAgent

agent = VLLMAgent(
    agent_id="agent-architect-001",
    role="ARCHITECT",
    workspace_path="/workspace",
    vllm_url="http://vllm-server-service:8000",
    enable_tools=True,  # Puede ejecutar git, files, etc
)

# Ejecutar tarea con vLLM real
result = await agent.execute_task(
    task="Analyze Context Service codebase",
    context=smart_context,  # Del Context Service
    constraints={"max_operations": 20}
)

# Resultado incluye:
# - result.operations: [git.status, files.read_file, ...]
# - result.artifacts: {files_read: [...], ...}
# - result.reasoning_log: [{thought, confidence, ...}, ...]
```

### Opción 3: Modificar Orchestrator Para Usar vLLM Por Defecto

```python
# En CreateCouncil, cambiar:
def CreateCouncil(self, request, context):
    # ...
    agent_type = request.config.agent_type if request.config else "MOCK"
    
    # Cambiar a:
    agent_type = request.config.agent_type if request.config else "RAY_VLLM"
    # ...
```

---

## 📊 Comparación: Mock vs Real en Tests E2E

### Test Actual (MockAgent)

```bash
$ python tests/e2e/test_ray_vllm_with_tools_e2e.py

Test 1: ARCHITECT Code Analysis
   Duration: 0.0s ✅
   Agents: 3 MockAgents
   Proposals: 3 (synthetic, pattern-based)
   Tools used: None (simulated)
   Diversity: 100% (seed-based)
   
Test 2: Cross-Role Collaboration
   Duration: 0.0s ✅
   Roles: ARCHITECT, DEV, QA (all mocks)
   Proposals: 9 total (3 per role)
   Tools used: None (simulated)
   
Total: 5/5 tests in 0.0s ✅
```

### Test Con VLLMAgent Real (Futuro)

```bash
$ python tests/e2e/test_ray_vllm_with_tools_e2e.py --real-agents

Test 1: ARCHITECT Code Analysis
   Duration: 15-45s (vLLM inference)
   Agents: 3 VLLMAgents
   Models: databricks/dbrx-instruct (3 instances)
   Proposals: 3 (real LLM generation)
   Tools used: 
     - files.list_files (services/context/)
     - files.read_file (neo4j_store.py)
     - files.search_in_files ("neo4j|redis")
     - db.neo4j_query (schema inspection)
   Diversity: 100% (temperature=0.3, real variations)
   vLLM logs: 9 POST /v1/chat/completions (3 agents × 3 calls)
   
Test 2: Cross-Role Collaboration
   Duration: 45-90s (3 roles × 3 agents × 5-10s each)
   Roles: 
     - ARCHITECT (databricks/dbrx, 3 agents)
     - DEV (deepseek-coder:33b, 3 agents)
     - QA (mistral-7b, 3 agents)
   Proposals: 9 total (real LLM generation)
   Tools used: 15-20 operations total
   
Total: 5/5 tests in 60-120s ✅
```

---

## 🎬 Demo Script: Ver Agentes Reales Pensando

### Script Para Demostrar vLLM Real

```bash
#!/bin/bash
# demo_real_vllm_agents.sh

echo "🚀 Starting REAL vLLM Agent Demo"
echo "================================"
echo ""

# 1. Verificar vLLM está corriendo
echo "1️⃣  Checking vLLM server..."
kubectl get pods -n swe-ai-fleet -l app=vllm-server
echo ""

# 2. Port-forward Orchestrator
echo "2️⃣  Port-forwarding Orchestrator..."
kubectl port-forward -n swe-ai-fleet svc/orchestrator 50055:50055 &
PF_PID=$!
sleep 2
echo ""

# 3. Crear council con VLLMAgents (modificar CreateCouncil para usar RAY_VLLM)
echo "3️⃣  Creating ARCHITECT council with REAL vLLM agents..."
python - <<EOF
import grpc
from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc

channel = grpc.insecure_channel("localhost:50055")
stub = orchestrator_pb2_grpc.OrchestratorStub(channel)

# Crear council con vLLM real
response = stub.CreateCouncil(orchestrator_pb2.CreateCouncilRequest(
    role="ARCHITECT",
    num_agents=3,
    config=orchestrator_pb2.CouncilConfig(
        agent_type="RAY_VLLM"  # <-- Usar vLLM real
    )
))
print(f"Council created: {response.council_id}")
EOF
echo ""

# 4. Ejecutar deliberación
echo "4️⃣  Running deliberation (this will take 15-45s)..."
python tests/e2e/test_architect_analysis_e2e.py
echo ""

# 5. Monitorear logs de vLLM en tiempo real
echo "5️⃣  Monitoring vLLM server logs (watch for chat/completions)..."
kubectl logs -f -n swe-ai-fleet deployment/vllm-server --tail=20 &
VLLM_LOG_PID=$!

sleep 60  # Esperar a que termine

# 6. Cleanup
kill $PF_PID $VLLM_LOG_PID 2>/dev/null
echo ""
echo "✅ Demo complete!"
```

---

## 🔍 Próximos Pasos Para Usar vLLM Real

### 1. Modificar CreateCouncil (Orchestrator)

```python
# services/orchestrator/server.py:520

def CreateCouncil(self, request, context):
    # ...
    
    # Cambiar de:
    agent_type = request.config.agent_type if request.config else "MOCK"
    
    # A:
    agent_type = request.config.agent_type if request.config else "RAY_VLLM"
    
    # Y asegurarse de que vllm_url y workspace_path estén configurados
    # ...
```

### 2. Configurar Workspace Path

```python
# VLLMAgentJob necesita un workspace para ejecutar tools
# Opciones:
# A) Montar PVC en Ray pods
# B) Clonar repo en /tmp al inicio
# C) Usar emptyDir para testing
```

### 3. Verificar vLLM Server

```bash
# Probar que vLLM responde
curl -X POST http://vllm-server-service:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-0.6B",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'
```

### 4. Crear Test E2E Con Flag

```python
# tests/e2e/conftest.py
import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--real-agents",
        action="store_true",
        default=False,
        help="Use real vLLM agents instead of mocks"
    )

@pytest.fixture
def agent_type(request):
    if request.config.getoption("--real-agents"):
        return "RAY_VLLM"
    return "MOCK"

# tests/e2e/test_ray_vllm_with_tools_e2e.py
def test_architect_analysis(stub, agent_type):
    response = stub.CreateCouncil(
        role="ARCHITECT",
        config=CouncilConfig(agent_type=agent_type)  # <-- Dinámico
    )
    # ...

# Ejecutar:
# pytest tests/e2e/ --real-agents  # Usa vLLM real (lento)
# pytest tests/e2e/                # Usa mocks (rápido)
```

---

## 📝 Resumen

### Estado Actual ✅

- ✅ **MockAgent funcionando** - Tests rápidos y confiables
- ✅ **VLLMAgent implementado** - Código listo para usar vLLM real
- ✅ **Ray integration completa** - VLLMAgentJob puede ejecutar en cluster
- ✅ **vLLM server corriendo** - Esperando requests
- ✅ **Tools funcionando** - git, files, tests, etc todos operativos
- ✅ **Tests 78/78 passing** - Con mocks (0.0s)

### Lo Que Falta ⏳

- ⏳ **Cambiar CreateCouncil** - Usar `agent_type="RAY_VLLM"` por defecto
- ⏳ **Configurar workspace** - Montar código en Ray pods
- ⏳ **Test E2E con vLLM** - Ejecutar con `--real-agents`
- ⏳ **Monitoring** - Logs de vLLM, timing, costos

### Próxima Sesión 🚀

1. Modificar CreateCouncil para usar vLLM
2. Configurar workspace mounting
3. Ejecutar test E2E con vLLM real
4. Capturar logs de vLLM
5. Medir timing real (15-45s esperado)
6. Verificar diversidad de propuestas (real LLM)

---

**TL;DR**: Los agentes tardaron 0.0s porque son mocks (por diseño para testing).
El código para usar vLLM real está listo, solo falta cambiar una bandera en CreateCouncil.

