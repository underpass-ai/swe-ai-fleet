# Auditoría: Tests en tests/integration/

**Fecha**: 2025-10-12  
**Objetivo**: Verificar si los tests en `tests/integration/` son realmente de integración o unitarios

---

## 📊 Análisis por Archivo

### ✅ VERDADEROS TESTS DE INTEGRACIÓN

#### 1. `orchestrator/test_vllm_agent_integration.py`
- **Requiere**: vLLM server + NATS corriendo
- **Sin mocks**: Llama APIs reales
- **Skip si no disponible**: ✅
- **Veredicto**: ✅ **INTEGRACIÓN REAL**

#### 2. `test_router_integration.py`
- **Requiere**: Servicios externos (probablemente)
- **Sin mocks obvios**
- **Veredicto**: ✅ **PROBABLEMENTE INTEGRACIÓN** (revisar contenido completo)

---

### ❌ TESTS UNITARIOS MAL CLASIFICADOS

#### 3. `orchestrator/test_model_adapter_integration.py`
```python
from unittest.mock import Mock, patch
```
- **Usa**: `Mock`, `patch`
- **No requiere**: Servicios externos
- **Veredicto**: ❌ **UNITARIO** → Mover a `tests/unit/orchestrator/`

#### 4. `orchestrator/test_deliberate_integration.py`
```python
from swe_ai_fleet.orchestrator.domain.agents.mock_agent import MockAgent
```
- **Usa**: `MockAgent` (no servicios reales)
- **No requiere**: Servicios externos
- **Veredicto**: ❌ **UNITARIO** → Mover a `tests/unit/orchestrator/`

#### 5. `orchestrator/test_orchestrate_integration.py`
```python
from swe_ai_fleet.orchestrator.domain.agents.mock_agent import MockAgent
```
- **Usa**: `MockAgent` (no servicios reales)
- **No requiere**: Servicios externos
- **Veredicto**: ❌ **UNITARIO** → Mover a `tests/unit/orchestrator/`

#### 6. `test_context_service_integration.py`
```python
from unittest.mock import AsyncMock, Mock, patch
```
- **Usa**: `Mock`, `patch`, `AsyncMock`
- **No requiere**: Servicios externos
- **Veredicto**: ❌ **UNITARIO** → Mover a `tests/unit/`

#### 7. `test_context_service.py`
```python
from unittest.mock import AsyncMock, Mock, patch
```
- **Usa**: `Mock`, `patch`, `AsyncMock`
- **No requiere**: Servicios externos
- **Veredicto**: ❌ **UNITARIO** → Mover a `tests/unit/`

---

### 🐳 TESTS CON DOCKER/TESTCONTAINERS

#### 8. `services/orchestrator/test_grpc_integration.py`
```python
from testcontainers.core.container import DockerContainer
```
- **Usa**: testcontainers (Docker)
- **Requiere**: Docker/Podman
- **Veredicto**: ✅ **INTEGRACIÓN CORRECTA**

#### 9. `services/orchestrator/test_grpc_simple.py`
- **Requiere**: Servicio corriendo manualmente
- **Sin testcontainers**: Pero requiere servicio real
- **Veredicto**: ✅ **INTEGRACIÓN CORRECTA**

#### 10. `services/context/test_persistence_integration.py`
- **Requiere**: Verificar contenido
- **Veredicto**: 🔍 **REVISAR**

---

## 📊 Resumen

| Archivo | Tipo Real | Ubicación Actual | Acción |
|---------|-----------|------------------|--------|
| `orchestrator/test_vllm_agent_e2e.py` ✅ | Integration | ✅ Correcta | ✅ Renombrado |
| `orchestrator/test_model_adapter_integration.py` | **Unit** | ❌ Incorrecta | Mover a unit/ |
| `orchestrator/test_deliberate_integration.py` | **Unit** | ❌ Incorrecta | Mover a unit/ |
| `orchestrator/test_orchestrate_integration.py` | **Unit** | ❌ Incorrecta | Mover a unit/ |
| `test_context_service_integration.py` | **Unit** | ❌ Incorrecta | Mover a unit/ |
| `test_context_service.py` | **Unit** | ❌ Incorrecta | Mover a unit/ |
| `test_router_integration.py` | Integration? | 🔍 Revisar | Verificar |
| `services/orchestrator/test_grpc_integration.py` | Integration | ✅ Correcta | Ninguna |
| `services/orchestrator/test_grpc_simple_e2e.py` ✅ | Integration | ✅ Correcta | ✅ Renombrado |
| `services/context/test_persistence_integration.py` | ? | 🔍 Revisar | Verificar |

---

## 🎯 Criterios de Clasificación

### Unit Test
- ✅ Usa `Mock`, `patch`, `MagicMock`, `AsyncMock`
- ✅ Usa `MockAgent` u otros test doubles
- ✅ NO requiere servicios externos
- ✅ Rápido (<1s)
- ✅ **Ubicación**: `tests/unit/`

### Integration Test
- ✅ Requiere servicios reales (vLLM, NATS, Redis, Neo4j, etc)
- ✅ Usa Docker/Podman/testcontainers
- ✅ Puede fallar si servicios no están disponibles
- ✅ Más lento (10s-60s)
- ✅ **Ubicación**: `tests/integration/`

### E2E Test
- ✅ Contra cluster Kubernetes real
- ✅ Sin Docker (cluster ya corriendo)
- ✅ kubectl port-forward o Ingress
- ✅ Muy lento (30s-5min)
- ✅ **Ubicación**: `tests/e2e/`

---

## 📋 Plan de Acción

### 1. Mover tests unitarios mal clasificados

```bash
# Mover 5 tests unitarios de integration/ → unit/
mv tests/integration/orchestrator/test_model_adapter_integration.py \
   tests/unit/orchestrator/test_model_adapter_integration.py

mv tests/integration/orchestrator/test_deliberate_integration.py \
   tests/unit/orchestrator/test_deliberate_integration.py

mv tests/integration/orchestrator/test_orchestrate_integration.py \
   tests/unit/orchestrator/test_orchestrate_integration.py

mv tests/integration/test_context_service_integration.py \
   tests/unit/test_context_service_integration.py

mv tests/integration/test_context_service.py \
   tests/unit/test_context_service.py
```

### 2. Verificar tests dudosos

- `test_router_integration.py` - Revisar contenido
- `services/context/test_persistence_integration.py` - Revisar contenido

### 3. Actualizar marcas pytest

Quitar `@pytest.mark.integration` de los 5 tests que se mueven a unit/

---

## 🔍 Siguiente Paso

Revisar contenido completo de:
1. `test_router_integration.py`
2. `services/context/test_persistence_integration.py`

Para determinar si son realmente de integración o unitarios.

---

## ✅ Cambios Realizados

### Renombrados (2 archivos)

1. ✅ `tests/integration/orchestrator/test_vllm_agent_integration.py`  
   → `tests/integration/orchestrator/test_vllm_agent_e2e.py`
   - **Razón**: Requiere vLLM + NATS reales (no Docker, servicios externos)

2. ✅ `tests/integration/services/orchestrator/test_grpc_simple.py`  
   → `tests/integration/services/orchestrator/test_grpc_simple_e2e.py`
   - **Razón**: Requiere servicio real corriendo manualmente

### Pendientes

- [ ] Mover 5 tests unitarios de `integration/` → `unit/`
- [ ] Revisar `test_router_integration.py`
- [ ] Revisar `services/context/test_persistence_integration.py`
- [ ] Actualizar marcas pytest en archivos movidos
- [ ] Ejecutar tests para verificar
- [ ] Commit

