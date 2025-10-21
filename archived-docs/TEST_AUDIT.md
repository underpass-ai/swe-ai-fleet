# Auditoría de Tests - Uso de Docker

**Fecha**: 2025-10-12  
**Objetivo**: Identificar tests que usan Docker para reclasificarlos correctamente

---

## 📊 Resumen

### Tests en `tests/e2e/` (TODOS usan Docker)
**Total**: 16 archivos de test

#### Archived (5 tests - obsoletos)
- ❌ `archived/test_context_assembler_e2e.py`
- ❌ `archived/test_decision_enriched_report_e2e.py`
- ❌ `archived/test_redis_store_e2e.py`
- ❌ `archived/test_report_usecase_e2e.py`
- ❌ `archived/test_session_rehydration_e2e.py`

**Acción**: Ya están documentados como obsoletos en `archived/README.md`

#### Context Service (7 tests - usan docker-compose)
- 🐳 `services/context/test_grpc_e2e.py`
- 🐳 `services/context/test_persistence_e2e.py`
- 🐳 `services/context/test_project_case_e2e.py`
- 🐳 `services/context/test_project_plan_e2e.py`
- 🐳 `services/context/test_project_subtask_e2e.py`
- 🐳 `services/context/test_projector_coordinator_e2e.py`
- 🐳 `services/context/test_realistic_workflows_e2e.py`

**Docker setup**: `tests/e2e/services/context/docker-compose.e2e.yml`  
**Acción**: Mover a `tests/integration/services/context/`

#### Orchestrator Service (4 tests - usan docker-compose)
- 🐳 `services/orchestrator/test_deliberate_e2e.py`
- 🐳 `services/orchestrator/test_orchestrate_e2e.py`
- 🐳 `services/orchestrator/test_ray_vllm_async_e2e.py`
- 🐳 `services/orchestrator/test_realistic_workflows_e2e.py`

**Docker setup**: 
- `tests/e2e/services/orchestrator/docker-compose.e2e.yml`
- `tests/e2e/services/orchestrator/docker-compose.ray-vllm.yml`
- `tests/e2e/services/orchestrator/docker-compose.ray.yml`

**Acción**: Mover a `tests/integration/services/orchestrator/`

---

### Tests en `tests/integration/` (algunos usan Docker)

#### Con Docker/testcontainers (2 tests)
- 🐳 `services/orchestrator/test_grpc_integration.py` (usa testcontainers)
- 🐳 `services/orchestrator/test_grpc_simple.py` (requiere servicio manual)

**Acción**: Ya están en el lugar correcto ✅

#### Sin Docker (tests puros de integración)
- ✅ `orchestrator/test_deliberate_integration.py`
- ✅ `orchestrator/test_model_adapter_integration.py`
- ✅ `orchestrator/test_orchestrate_integration.py`
- ✅ `orchestrator/test_vllm_agent_integration.py`
- ✅ `services/context/test_persistence_integration.py`
- ✅ `test_context_service.py`
- ✅ `test_context_service_integration.py`
- ✅ `test_router_integration.py`

**Acción**: Ya están correctos ✅

---

## 🎯 Plan de Acción

### 1. Mover tests de e2e → integration

```bash
# Context Service (7 tests + docker-compose + scripts)
mv tests/e2e/services/context/* tests/integration/services/context/

# Orchestrator Service (4 tests + docker-compose + scripts)
mv tests/e2e/services/orchestrator/* tests/integration/services/orchestrator/
```

### 2. Actualizar marcas pytest

Cambiar todos los `@pytest.mark.e2e` → `@pytest.mark.integration` en:
- 7 tests de context
- 4 tests de orchestrator

### 3. Limpiar tests/e2e/

- Eliminar `tests/e2e/services/` (ya movido)
- Mantener `tests/e2e/archived/` (con README explicativo)
- Crear `tests/e2e/README.md` explicando que es para tests contra cluster K8s

### 4. Actualizar documentación

- Crear `TESTING_LEVELS.md` con definiciones claras
- Actualizar READMEs de cada carpeta

---

## 📋 Definiciones Finales

### Unit Tests (`tests/unit/`)
- ✅ Mocks para todas las dependencias
- ✅ Sin Docker
- ✅ Sin servicios externos
- ✅ Rápidos (<1s)
- ✅ Marca: (default, sin marca)

### Integration Tests (`tests/integration/`)
- ✅ Docker/Podman con servicios reales
- ✅ testcontainers o docker-compose
- ✅ Más lentos (10s-60s)
- ✅ Marca: `@pytest.mark.integration`

### E2E Tests (`tests/e2e/`)
- ✅ Cluster Kubernetes real
- ✅ Sin Docker (cluster ya corriendo)
- ✅ kubectl port-forward o Ingress
- ✅ Muy lentos (30s-5min)
- ✅ Marca: `@pytest.mark.e2e`

---

## 📊 Estadísticas

| Carpeta | Total Tests | Con Docker | Sin Docker | Obsoletos |
|---------|-------------|------------|------------|-----------|
| `tests/unit/` | ~516 | 0 | 516 | 0 |
| `tests/integration/` | ~10 | 2 | 8 | 0 |
| `tests/e2e/` | 16 | 11 | 0 | 5 |

**Después del refactor:**
- `tests/unit/`: 516 tests (sin cambios)
- `tests/integration/`: ~21 tests (10 actuales + 11 de e2e)
- `tests/e2e/`: 0 tests (preparado para futuros tests contra cluster)

---

## ✅ Checklist

- [ ] Mover 11 tests de e2e → integration
- [ ] Cambiar marcas e2e → integration (11 archivos)
- [ ] Mover docker-compose files
- [ ] Mover scripts (run-e2e.sh, etc)
- [ ] Crear tests/e2e/README.md
- [ ] Crear TESTING_LEVELS.md
- [ ] Actualizar pytest.ini si es necesario
- [ ] Ejecutar tests para verificar
- [ ] Commit con mensaje descriptivo

