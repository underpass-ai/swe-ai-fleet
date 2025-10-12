# Pull Request: Reorganización de Tests por Tipo

## 🎯 Objetivo

Reorganizar la estructura de tests para que refleje correctamente su tipo:
- **Unit tests**: Con mocks, sin servicios externos
- **Integration tests**: Con Docker/Podman
- **E2E tests**: Contra cluster Kubernetes real

## 📊 Problema Anterior

Tests mal clasificados y estructura confusa:
- ❌ Tests unitarios (con mocks) en `tests/integration/`
- ❌ Tests con Docker en `tests/e2e/` (deberían ser integration)
- ❌ No había tests reales contra cluster K8s
- ❌ Scripts con nombres confusos (`run-e2e.sh` para Docker)
- ❌ Tests archived sin documentar razones

## ✅ Solución Implementada

### 1. Reclasificación de Tests (6 archivos)

**Movidos de integration → unit:**
- `orchestrator/test_model_adapter_integration.py` (usa Mock)
- `orchestrator/test_deliberate_integration.py` (usa MockAgent)
- `orchestrator/test_orchestrate_integration.py` (usa MockAgent)
- `test_context_service_integration.py` (usa Mock)
- `test_context_service.py` (usa Mock)
- `test_router_integration.py` (usa DummyAgent)

### 2. Reorganización e2e → integration (11 tests)

**Context Service (7 tests):**
- test_grpc_e2e.py
- test_persistence_e2e.py
- test_project_case_e2e.py
- test_project_plan_e2e.py
- test_project_subtask_e2e.py
- test_projector_coordinator_e2e.py
- test_realistic_workflows_e2e.py

**Orchestrator Service (4 tests):**
- test_deliberate_e2e.py
- test_orchestrate_e2e.py
- test_ray_vllm_async_e2e.py
- test_realistic_workflows_e2e.py

**Razón**: Todos usan Docker/Podman, no cluster K8s

### 3. Tests E2E Reales Creados

**Nuevos tests contra cluster Kubernetes:**
- `tests/e2e/test_orchestrator_cluster.py` (5 tests pytest)
- `tests/e2e/conftest.py` (fixtures para cluster)
- `tests/e2e/run-e2e-tests.sh` (script con kubectl port-forward)

**Verificados**: ✅ 5 tests passed contra cluster real (0.27s)

### 4. Infraestructura Docker para Integration Tests

**Creado:**
- `tests/integration/docker-compose.integration.yml`
  - Neo4j 5.14 (puertos 7687, 7474)
  - Redis 7 (puerto 6379)
  - NATS 2.10 (puertos 4222, 8222)

- `tests/integration/run-integration-tests.sh`
  - Levanta servicios automáticamente
  - Espera healthchecks
  - Ejecuta tests
  - Limpia al terminar

**Verificado**: ✅ 28 tests passed en Context Service

### 5. Dockerfiles Arreglados

**Context Service (Dockerfile.test):**
- ✅ Paths actualizados: tests/e2e → tests/integration
- ✅ Agregado: COPY src/ (para imports swe_ai_fleet.*)
- ✅ PYTHONPATH: /workspace:/workspace/src
- ✅ CMD: -m integration (era -m e2e)

**Orchestrator Service (Dockerfile.test):**
- ✅ Mismos cambios que Context

### 6. Scripts Renombrados

**Para claridad (integration tests usan Docker, no son E2E):**
- `run-e2e.sh` → `run-integration.sh` (context)
- `run-e2e.sh` → `run-integration.sh` (orchestrator)
- `run-e2e-ray-vllm.sh` → `run-integration-ray-vllm.sh`
- `docker-compose.e2e.yml` → `docker-compose.integration.yml` (2 archivos)

### 7. Tests Archived Investigados

**Investigados 6 tests archived:**
- ✅ Todos tienen razones válidas para estar archived
- ✅ Imports rotos (`RedisKvPort` no existe)
- ✅ Arquitectura obsoleta (pre-microservices)
- ✅ Ya cubiertos por tests modernos

**Documentado en:**
- `ARCHIVED_TESTS_INVESTIGATION.md` (análisis detallado)
- `tests/integration/archived/README.md` (actualizado)

### 8. Renombrados para Claridad

- `test_vllm_agent_e2e.py` → `test_vllm_agent_integration.py`
- `test_grpc_simple_e2e.py` → `test_grpc_simple_integration.py`

**Razón**: Usan Docker/servicios locales, no cluster K8s

---

## 📊 Resultado Final

### Estructura de Tests

```
tests/
├── unit/                           # 541 tests (1.75s)
│   ├── orchestrator/
│   ├── context/
│   ├── services/
│   └── ...
│
├── integration/                    # 28+ tests (10-60s)
│   ├── orchestrator/
│   │   └── test_vllm_agent_integration.py
│   ├── services/
│   │   ├── context/ (28 tests en Docker)
│   │   └── orchestrator/ (4 tests en Docker)
│   ├── docker-compose.integration.yml
│   ├── run-integration-tests.sh
│   ├── README.md
│   └── archived/ (6 tests documentados)
│
└── e2e/                            # 5 tests (0.27s)
    ├── test_orchestrator_cluster.py
    ├── conftest.py
    ├── run-e2e-tests.sh
    ├── README.md
    └── helpers/ (setup_all_councils.py, etc)
```

### Estadísticas

| Tipo | Antes | Después | Cambio |
|------|-------|---------|--------|
| **Unit** | 516 | 541 | +25 |
| **Integration** | 10 (mal clasificados) | 28+ (correctos) | +18 |
| **E2E** | 0 (eran integration) | 5 (reales vs K8s) | +5 |
| **Archived** | 5 | 6 | +1 |

### Comandos de Ejecución

```bash
# Unit tests (desarrollo diario)
pytest -m "not e2e and not integration"
# 541 passed, 2 skipped (1.75s)

# Integration tests (con Docker)
./tests/integration/run-integration-tests.sh
# Levanta Neo4j + Redis + NATS
# Ejecuta tests que no requieren gen/

# Integration tests específicos (con gen/)
cd tests/integration/services/context && ./run-integration.sh
# 28 passed en Docker

# E2E tests (contra cluster K8s)
./tests/e2e/run-e2e-tests.sh
# 5 passed vs cluster real (0.27s)
```

---

## 📚 Documentación Creada

1. **ARCHIVED_TESTS_INVESTIGATION.md**
   - Investigación detallada de cada test archived
   - Razones para mantenerlos archived
   - Plan de rescate (ninguno rescatable por ahora)

2. **TEST_REORGANIZATION_SUMMARY.md**
   - Resumen completo del refactor
   - Estadísticas antes/después
   - Comandos de ejecución

3. **tests/integration/README.md**
   - Guía completa de integration tests
   - Cómo ejecutar con Docker
   - Troubleshooting

4. **tests/e2e/README.md**
   - Guía de E2E tests contra cluster
   - Diferencias con integration tests
   - Setup con kubectl port-forward

5. **tests/integration/archived/README.md** (actualizado)
   - Razones específicas por cada test
   - Qué funcionalidad cubren ahora
   - Prioridades para futuro

---

## 🔧 Cambios Técnicos

### Dockerfiles
- ✅ COPY src/ agregado
- ✅ PYTHONPATH incluye /workspace/src
- ✅ Paths actualizados (e2e → integration)
- ✅ CMD usa -m integration

### Docker Compose
- ✅ NATS config corregida (flags inválidos eliminados)
- ✅ Healthchecks apropiados
- ✅ Network isolation

### Scripts
- ✅ Detección automática de podman-compose/docker-compose
- ✅ Healthcheck verification
- ✅ Cleanup automático
- ✅ Nombres claros (run-integration, run-e2e)

---

## ✅ Tests Verificados

### Unit Tests
```bash
pytest -m "not e2e and not integration"
```
**Resultado**: ✅ **541 passed, 2 skipped** (1.75s)

### Integration Tests (Context Service)
```bash
cd tests/integration/services/context && ./run-integration.sh
```
**Resultado**: ✅ **28 passed** en Docker (~60s)

### E2E Tests (Cluster K8s)
```bash
./tests/e2e/run-e2e-tests.sh
```
**Resultado**: ✅ **5 passed** vs cluster real (0.27s)

---

## 🎯 Beneficios

### Claridad
- ✅ Cada test está en la carpeta correcta según su tipo
- ✅ Nombres de archivos consistentes
- ✅ Scripts con nombres descriptivos

### Mantenibilidad
- ✅ Fácil identificar qué tests requieren Docker
- ✅ Fácil identificar qué tests requieren cluster
- ✅ Documentación exhaustiva

### Velocidad
- ✅ Unit tests rápidos (1.75s) para desarrollo diario
- ✅ Integration tests opcionales (solo cuando se necesitan)
- ✅ E2E tests manuales (validación final)

### CI/CD
- ✅ Unit tests: Siempre en PRs
- ✅ Integration tests: Solo en merge a main
- ✅ E2E tests: Solo en merge a main

---

## 🔍 Revisión Recomendada

### Archivos Clave
1. `tests/unit/` - Verificar que todos son realmente unitarios
2. `tests/integration/services/*/Dockerfile.test` - Verificar builds
3. `tests/e2e/test_orchestrator_cluster.py` - Verificar tests E2E
4. `ARCHIVED_TESTS_INVESTIGATION.md` - Verificar análisis

### Tests a Ejecutar
```bash
# Verificar unit tests
pytest -m "not e2e and not integration"

# Verificar integration tests (requiere Docker)
./tests/integration/run-integration-tests.sh

# Verificar E2E tests (requiere cluster)
./tests/e2e/run-e2e-tests.sh
```

---

## 📝 Notas

- Tests archived tienen razones válidas y están documentados
- Infraestructura Docker lista para integration tests
- E2E tests funcionan contra cluster real
- Todos los tests verificados y pasando

---

**Commits**: 9  
**Files changed**: ~100  
**Tests reorganizados**: 547  
**Documentación**: 5 documentos nuevos/actualizados

🚀 **Ready to merge!**

