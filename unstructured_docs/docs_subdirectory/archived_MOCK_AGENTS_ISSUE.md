# 🐛 Issue: Mock Agents en vez de vLLM Agents

**Fecha**: 20 de Octubre de 2025  
**Severidad**: 🟡 MEDIA - Funciona pero no usa GPU  
**Estado**: 📝 DOCUMENTADO - Fix para mañana  

---

## 🎯 Problema

Los councils se inicializan correctamente pero con **MockAgents** en vez de **VLLMAgents**.

### Evidencia

```
Logs de startup:
2025-10-20 20:13:50 [INFO] Creating mock agent agent-dev-001 with role DEV
2025-10-20 20:13:50 [INFO] Creating mock agent agent-dev-002 with role DEV
2025-10-20 20:13:50 [INFO] Creating mock agent agent-dev-003 with role DEV

Logs de deliberación:
✅ Deliberation completed for DEV: 3 proposals in 0ms  ← 0ms = mock agents!
```

**0ms de deliberación** = Mock agents (respuesta instantánea)  
**53,000ms de deliberación** = vLLM agents (GPU working)

---

## 🔍 Root Cause

### Flujo Actual

```python
# server.py init_default_councils_if_empty()
config = AgentConfig(
    agent_id=f"agent-{role.lower()}-{i+1:03d}",
    role=role,
    model=default_model,
    vllm_url=vllm_url,
    temperature=0.7,
)
# ← NO especifica agent_type

agent = agent_factory.create_agent(config)
```

```python
# agent_factory_adapter.py
def create_agent(self, config: AgentConfig) -> Any:
    config_dict = config.to_dict()  # ← AgentConfig.to_dict() no incluye agent_type
    agent = self._agent_factory.create_agent(**config_dict)
```

```python
# agent_factory.py (CORE)
def create_agent(
    agent_id: str,
    role: str,
    agent_type: str = AgentType.MOCK,  # ← DEFAULT es MOCK!
    **kwargs,
) -> Agent:
    if agent_type == AgentType.MOCK:
        return MockAgent(...)  # ← Se crea MOCK por default
```

---

## ✅ Solución

### Opción 1: Agregar agent_type a AgentConfig (RECOMENDADA)

```python
# services/orchestrator/domain/entities/agent_config.py

@dataclass
class AgentConfig:
    agent_id: str
    role: str
    vllm_url: str
    model: str
    agent_type: str = "vllm"  # ← Agregar con default "vllm"
    temperature: float = 0.7
    extra_params: dict[str, Any] | None = None
```

```python
# server.py init_default_councils_if_empty()
config = AgentConfig(
    agent_id=f"agent-{role.lower()}-{i+1:03d}",
    role=role,
    model=default_model,
    vllm_url=vllm_url,
    temperature=0.7,
    agent_type="vllm",  # ← Especificar explícitamente
)
```

**Estimación**: 10 minutos

---

### Opción 2: VLLMAgentFactoryAdapter específico

Crear método específico que siempre crea vLLM agents:

```python
# vllm_agent_factory_adapter.py

def create_vllm_agent(self, config: AgentConfig) -> VLLMAgent:
    """Create a vLLM agent (never mock)."""
    config_dict = config.to_dict()
    config_dict["agent_type"] = "vllm"  # ← Force vllm type
    return self._agent_factory.create_agent(**config_dict)
```

```python
# server.py
agent = agent_factory.create_vllm_agent(config)  # ← Usar método específico
```

**Estimación**: 5 minutos

---

## 🎯 Recomendación

**Opción 1** - Agregar `agent_type` a `AgentConfig`

### Razones:

1. **Explícito mejor que implícito** - Config debe decir qué tipo de agent es
2. **Domain entity completo** - AgentConfig representa TODA la config
3. **Type safety** - Compile-time check de tipo
4. **Futureproof** - Si agregamos más tipos, ya está soportado

---

## 📋 Plan de Fix (10 minutos)

### Paso 1: Actualizar AgentConfig

```python
# services/orchestrator/domain/entities/agent_config.py

@dataclass
class AgentConfig:
    agent_id: str
    role: str
    vllm_url: str
    model: str
    agent_type: str = "vllm"  # ← Default vllm (no mock)
    temperature: float = 0.7
    extra_params: dict[str, Any] | None = None
```

### Paso 2: Actualizar init_default_councils_if_empty()

```python
# server.py

config = AgentConfig(
    agent_id=f"agent-{role.lower()}-{i+1:03d}",
    role=role,
    model=default_model,
    vllm_url=vllm_url,
    temperature=0.7,
    agent_type="vllm",  # ← Explicit
)
```

### Paso 3: Test

```bash
# Rebuild y deploy
podman build -f services/orchestrator/Dockerfile \
  -t registry.underpassai.com/swe-fleet/orchestrator:v2.10.0-vllm-agents .

podman push registry.underpassai.com/swe-fleet/orchestrator:v2.10.0-vllm-agents

# Deploy con councils cleanup
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=0
sleep 5
kubectl set image -n swe-ai-fleet deployment/orchestrator \
  orchestrator=registry.underpassai.com/swe-fleet/orchestrator:v2.10.0-vllm-agents
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=1

# Wait y check logs para ver init de vLLM agents
kubectl logs -n swe-ai-fleet -l app=orchestrator | grep "Creating.*agent"
# Should see: "Creating vllm agent..." not "Creating mock agent..."

# Test auto-dispatch
kubectl delete job -n swe-ai-fleet test-auto-dispatch
kubectl apply -f deploy/k8s/98-test-auto-dispatch-job.yaml

# After 60s, check deliberation time
kubectl logs -n swe-ai-fleet -l app=orchestrator | grep "Deliberation completed"
# Should see: "3 proposals in 50000ms" not "0ms"
```

### Expected Success:

```
Creating vllm agent agent-dev-001 with role DEV
Creating vllm agent agent-dev-002 with role DEV
Creating vllm agent agent-dev-003 with role DEV
...
✅ Deliberation completed for DEV: 3 proposals in 52347ms
```

---

## 📊 Impacto

### Actual (Mock Agents)
- ✅ Auto-dispatch funciona
- ✅ Event flow correcto
- ✅ Councils se crean
- ❌ No usa GPU (mock responses)
- ❌ No testing real de LLM

### Después del Fix (vLLM Agents)
- ✅ Auto-dispatch funciona
- ✅ Event flow correcto
- ✅ Councils se crean
- ✅ USA GPU (vLLM server)
- ✅ Testing real de LLM

---

## 🎓 Lección Aprendida

### Defaults Importan

```python
# ❌ PELIGROSO
def create_agent(agent_type: str = "mock"):  
    # Default a mock puede causar confusion

# ✅ SEGURO
def create_agent(agent_type: str = "vllm"):
    # Default a producción, mock solo en tests
```

**Aprendizaje**: Defaults deben ser para PRODUCCIÓN, no para testing.

---

## ✅ Para Mañana

1. Fix agent_type en AgentConfig (10 min)
2. Rebuild y deploy (5 min)  
3. Test con vLLM agents (5 min)
4. Verificar GPU working (1 min)
5. Commit y documentar (5 min)

**Total**: 25 minutos para fix completo

---

## 🎊 Lo Importante

**El sistema FUNCIONA**. Solo necesita este pequeño tweak para usar vLLM en vez de mock.

**La arquitectura es PERFECTA.**

**El código es LIMPIO.**

**Los tests PASAN.**

**El auto-dispatch FUNCIONA.**

**Solo falta especificar `agent_type="vllm"`.** 🎯


