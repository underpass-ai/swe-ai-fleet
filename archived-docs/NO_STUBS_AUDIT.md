# 🔍 Auditoría de Stubs/Mocks en Microservicios

**Fecha**: 16 de Octubre de 2025  
**Objetivo**: Verificar que NO hay stubs, mocks o código de prueba en microservicios de producción

---

## ✅ SERVICIOS AUDITADOS

### 1. **Planning Service** (Go)
**Ubicación**: `services/planning/`

**Búsqueda**: Mock, mock, Stub, stub, Fake, fake, Dummy, dummy

**Resultado**: ✅ **LIMPIO** - No hay mocks ni stubs

**Archivos revisados**:
- `services/planning/internal/fsmx/engine.go` - Solo lógica de negocio
- `services/planning/gen/fleet/planning/v1/planning_grpc.pb.go` - Código generado (Stubs normales de gRPC)

**Conclusión**: Servicio de producción 100% limpio.

---

### 2. **StoryCoach Service** (Go)
**Ubicación**: `services/storycoach/`

**Búsqueda**: Mock, mock, Stub, stub, Fake, fake, Dummy, dummy

**Resultado**: ✅ **LIMPIO** - No hay mocks ni stubs

**Archivos revisados**:
- `services/storycoach/internal/scorer/scorer.go` - Solo lógica de scoring INVEST
- `services/storycoach/gen/fleet/storycoach/v1/storycoach_grpc.pb.go` - Código generado

**Conclusión**: Servicio de producción 100% limpio.

---

### 3. **Workspace Service** (Go)
**Ubicación**: `services/workspace/`

**Búsqueda**: Mock, mock, Stub, stub, Fake, fake, Dummy, dummy

**Resultado**: ✅ **LIMPIO** - No hay mocks ni stubs

**Archivos revisados**:
- `services/workspace/internal/scorer/scorer.go` - Solo lógica de rigor scoring
- `services/workspace/gen/fleet/workspace/v1/workspace_grpc.pb.go` - Código generado

**Conclusión**: Servicio de producción 100% limpio.

---

### 4. **Context Service** (Python)
**Ubicación**: `services/context/`

**Búsqueda**: Mock, mock, Stub, stub, Fake, fake, Dummy, dummy

**Resultado**: ✅ **LIMPIO** - Solo referencias en código generado

**Archivos revisados**:
- `services/context/gen/context_pb2_grpc.py` - Código generado (Stub normal de gRPC)
- `services/context/server.py` - Solo lógica de negocio
- `services/context/consumers/*.py` - Solo consumers reales

**Conclusión**: Servicio de producción 100% limpio.

---

### 5. **Orchestrator Service** (Python) ⚠️
**Ubicación**: `services/orchestrator/`

**Búsqueda**: Mock, mock, Stub, stub, Fake, fake, Dummy, dummy

**Resultado**: ⚠️ **CÓDIGO DE MOCK ENCONTRADO (CORREGIDO)**

**Archivos con menciones**:
- `services/orchestrator/gen/orchestrator_pb2_grpc.py` - Código generado (OK)
- `services/orchestrator/server.py` - **TENÍA código de mock agents**

---

## ⚠️ PROBLEMAS ENCONTRADOS Y CORREGIDOS

### Problema 1: Default a Mock Agents en CreateCouncil

**Ubicación**: `services/orchestrator/server.py:489`

**ANTES (INCORRECTO)**:
```python
# Determine agent type from config or environment
agent_type = "mock"  # Default to mock for backward compatibility
```

**DESPUÉS (CORREGIDO)**:
```python
# Determine agent type from config or environment
# DEFAULT: RAY_VLLM for production (real vLLM agents)
agent_type = "RAY_VLLM"  # Production default: real vLLM agents
```

**Impacto**: 
- ❌ ANTES: Cualquier council sin config explícito usaba MOCK agents
- ✅ AHORA: Por defecto usa RAY_VLLM (agentes reales con vLLM)

---

### Problema 2: Default a Mock en RegisterAgent

**Ubicación**: `services/orchestrator/server.py:409`

**ANTES (INCORRECTO)**:
```python
agent_type = os.getenv("AGENT_TYPE", "mock")
```

**DESPUÉS (CORREGIDO)**:
```python
# DEFAULT: vllm for production (real vLLM agents, not mock)
agent_type = os.getenv("AGENT_TYPE", "vllm")
```

**Impacto**:
- ❌ ANTES: Agents registrados individualmente defaulteaban a mock
- ✅ AHORA: Defaultean a vLLM real

---

### Problema 3: Rama de Mock Agents en CreateCouncil

**Ubicación**: `services/orchestrator/server.py:549-584`

**ANTES (PELIGROSO)**:
```python
else:
    # Use mock agents (default)
    from swe_ai_fleet.orchestrator.domain.agents.mock_agent import (
        AgentBehavior,
    )
    # ... crear mock agents silenciosamente
```

**DESPUÉS (FAIL-FAST)**:
```python
else:
    # PRODUCTION: Should NEVER reach here (default is RAY_VLLM)
    # Mock agents are ONLY for unit tests, not for production/E2E
    logger.error(
        f"❌ CRITICAL: Attempted to create MOCK agents in production! "
        f"agent_type={agent_type}. "
        f"Production must use RAY_VLLM agents."
    )
    context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
    context.set_details("Mock agents not allowed in production")
    return orchestrator_pb2.CreateCouncilResponse()
```

**Impacto**:
- ❌ ANTES: Creaba mock agents silenciosamente si fallaba configuración
- ✅ AHORA: FALLA RÁPIDO con error explícito

---

### Problema 4: Rama de Mock Agent en RegisterAgent

**Ubicación**: `services/orchestrator/server.py:417-422`

**ANTES (PELIGROSO)**:
```python
else:
    # Create mock agent (default)
    new_agent = AgentFactory.create_agent(
        agent_id=agent_id,
        role=role,
        agent_type=agent_type,
        behavior="normal",
    )
```

**DESPUÉS (FAIL-FAST)**:
```python
else:
    # PRODUCTION: Should NEVER reach here
    logger.error(
        f"❌ CRITICAL: Attempted to create MOCK agent in RegisterAgent!"
    )
    context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
    context.set_details("Mock agents not allowed in production")
    return orchestrator_pb2.RegisterAgentResponse(success=False)
```

---

## ✅ CONFIGURACIÓN VERIFICADA

### Deployment de Orchestrator

**Variable de Entorno**:
```yaml
env:
  - name: AGENT_TYPE
    value: "vllm"  # ✅ CORRECTO
```

**ConfigMap**: `deploy/k8s/11-orchestrator-service.yaml`

---

## 📋 RESUMEN FINAL

| Servicio | Stubs/Mocks | Estado | Acción |
|----------|-------------|--------|--------|
| **Planning** | ❌ No | ✅ Limpio | Ninguna |
| **StoryCoach** | ❌ No | ✅ Limpio | Ninguna |
| **Workspace** | ❌ No | ✅ Limpio | Ninguna |
| **Context** | ❌ No | ✅ Limpio | Ninguna |
| **Orchestrator** | ⚠️ Sí (mock agents) | ✅ Corregido | Rebuild v0.6.2 requerido |

---

## 🚀 CAMBIOS APLICADOS

### Archivos Modificados

1. ✅ `services/orchestrator/server.py`
   - Línea 490: Default cambiado de `"mock"` a `"RAY_VLLM"`
   - Línea 410: Default cambiado de `"mock"` a `"vllm"`
   - Líneas 550-563: Rama else cambiada a fail-fast (error en lugar de crear mocks)
   - Líneas 417-425: Rama else cambiada a fail-fast

### Despliegue Requerido

```bash
# Rebuild Orchestrator v0.6.2 (con cambios)
cd /home/tirso/ai/developents/swe-ai-fleet
podman build -t registry.underpassai.com/swe-fleet/orchestrator:v0.6.2 -f services/orchestrator/Dockerfile .
podman push registry.underpassai.com/swe-fleet/orchestrator:v0.6.2

# Deploy
kubectl set image deployment/orchestrator orchestrator=registry.underpassai.com/swe-fleet/orchestrator:v0.6.2 -n swe-ai-fleet
```

---

## 🎯 GARANTÍAS DE PRODUCCIÓN

Con estos cambios, el sistema ahora garantiza:

1. ✅ **Fail-Fast**: Si se intenta crear mock agents en producción, falla con error explícito
2. ✅ **Default Seguro**: Todos los defaults apuntan a vLLM real, no mocks
3. ✅ **Código Limpio**: Todos los microservicios Go libres de mocks
4. ✅ **Configuración Explícita**: AGENT_TYPE=vllm en deployment

---

## 🔐 RECOMENDACIONES

### 1. Unit Tests con Mocks
Los mocks SOLO deben estar en:
- `tests/unit/` - Tests unitarios
- `tests/conftest.py` - Fixtures de pytest
- **NUNCA** en `services/*/` (código de producción)

### 2. Variable de Entorno Defensiva
```yaml
env:
  - name: AGENT_TYPE
    value: "vllm"  # Explícito, no defaultear a mock
  - name: ALLOW_MOCK_AGENTS
    value: "false"  # Feature flag para bloquear mocks
```

### 3. CI/CD Check
Agregar check en pipeline:
```bash
# Fallar build si encuentra mocks en services/
grep -r "MockAgent\|mock_agent" services/ && exit 1
```

---

**Conclusión**: Todos los microservicios están limpios excepto Orchestrator que tenía defaults a mock. Corregido para que defaultee a vLLM real y falle rápido si se intenta usar mocks en producción.

**Próximo Deploy**: Orchestrator v0.6.2 → Elimina completamente risk de usar mock agents en producción.

