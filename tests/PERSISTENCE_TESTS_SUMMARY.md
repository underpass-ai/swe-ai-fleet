# Context Service - Resumen de Tests de Persistencia

Documentación completa de los tests creados para verificar la persistencia de datos en el Context Service.

## 📊 Cobertura Total: 54 Tests

### 🧪 Unit Tests (15 tests) ✅
**Ubicación**: `tests/unit/services/context/test_persistence_unit.py`

**Características**:
- Sin dependencias externas (usa mocks)
- Ejecución rápida (< 1 segundo)
- CI-friendly
- Tests de lógica aislada

**Cobertura**:
- `TestProcessContextChange` (8 tests) - Ruteo y validación de cambios
- `TestPersistDecisionChange` (3 tests) - CREATE, UPDATE, DELETE de decisiones
- `TestPersistSubtaskChange` (1 test) - Actualización de subtasks
- `TestPersistMilestoneChange` (1 test) - Creación de milestones
- `TestDetectScopes` (3 tests) - Detección de scopes en prompts

**Ejecución**:
```bash
source .venv/bin/activate
pytest tests/unit/services/context/test_persistence_unit.py -v
```

**Resultado**: ✅ 15 passed in 0.52s

---

### 🔄 Integration Tests (12 tests)
**Ubicación**: `tests/integration/services/context/test_persistence_integration.py`

**Características**:
- Usa Neo4j y Redis reales
- Tests de componentes con infraestructura
- 7 tests funcionan sin infraestructura (detección de scopes)
- 5 tests requieren Neo4j/Redis

**Cobertura**:
- `TestDecisionPersistence` (3 tests) - Persistencia real a Neo4j
- `TestSubtaskPersistence` (1 test) - Actualización de subtasks en Neo4j
- `TestMilestonePersistence` (1 test) - Creación de eventos en Neo4j
- `TestScopeDetection` (7 tests) - Detección de scopes (sin infraestructura)

**Ejecución**:
```bash
# Solo tests sin infraestructura
pytest tests/integration/services/context/test_persistence_integration.py::TestScopeDetection -v

# Con infraestructura (Neo4j + Redis)
podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml up -d neo4j redis
export NEO4J_URI="bolt://localhost:17687"
export NEO4J_PASSWORD="testpassword"
pytest tests/integration/services/context/ -v -m integration
```

**Resultado**: ✅ 7 passed, 5 skipped (sin infraestructura local)

---

### 🚀 E2E Tests (27 tests) ✅
**Ubicación**: `tests/e2e/services/context/`

**Archivos**:
- `test_grpc_e2e.py` (20 tests) - Tests gRPC originales
- `test_persistence_e2e.py` (7 tests) - **NUEVOS** tests de persistencia

**Nuevos Tests de Persistencia**:
1. ✅ `test_create_decision_persists_to_neo4j` - Verifica CREATE de decisión
2. ✅ `test_update_decision_persists_to_neo4j` - Verifica UPDATE de decisión
3. ✅ `test_delete_decision_marks_as_deleted` - Verifica soft-delete
4. ✅ `test_update_subtask_persists_to_neo4j` - Verifica UPDATE de subtask
5. ✅ `test_create_milestone_persists_to_neo4j` - Verifica CREATE de milestone
6. ✅ `test_multiple_changes_all_persist` - Verifica batch updates
7. ✅ `test_invalid_json_payload_does_not_crash` - Verifica error handling

**Características**:
- Usa infraestructura completa (Neo4j, Redis, NATS, Context Service)
- Verifica persistencia end-to-end via gRPC
- Incluye verificación directa en Neo4j después de cada operación
- Tests de batch updates y error handling

**Ejecución**:
```bash
# Todos los tests E2E
./tests/e2e/services/context/run-e2e.sh

# O manualmente
podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml up -d
sleep 40
podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml run --rm tests
```

**Resultado**: ✅ 27 passed in 8.09s

---

## 🎯 Lo que Verifican los Tests

### 1. Persistencia de Decisiones
- **CREATE**: Nuevas decisiones se crean en Neo4j con todas las propiedades
- **UPDATE**: Decisiones existentes se actualizan correctamente
- **DELETE**: Soft delete - marca como `status=DELETED` en lugar de borrar

### 2. Persistencia de Subtasks
- **UPDATE**: Actualización de status, assignee, y otros campos

### 3. Persistencia de Milestones/Eventos
- **CREATE**: Eventos se crean con timestamp automático y metadata

### 4. Detección de Scopes
- **Análisis de contenido**: Detecta qué secciones están presentes en el prompt
- **Scopes soportados**: CASE_HEADER, PLAN_HEADER, SUBTASKS_ROLE, DECISIONS_RELEVANT_ROLE, DEPS_RELEVANT, MILESTONES

### 5. Manejo de Errores
- **JSON inválido**: No crashea el servicio
- **Tipos de entidad desconocidos**: Se loguean pero no fallan
- **Errores de Neo4j**: Se capturan y loguean, servicio continúa funcionando

---

## 🏗️ Arquitectura de los Tests

```
tests/
├── unit/services/context/
│   ├── test_persistence_unit.py          # 15 tests con mocks
│   └── README_PERSISTENCE.md             # Documentación unit tests
│
├── integration/services/context/
│   ├── test_persistence_integration.py   # 12 tests (7 sin infra, 5 con infra)
│   ├── conftest.py                       # Fixtures Neo4j/Redis
│   └── README.md                         # Documentación integration tests
│
└── e2e/services/context/
    ├── test_grpc_e2e.py                  # 20 tests gRPC originales
    ├── test_persistence_e2e.py           # 7 tests nuevos de persistencia
    ├── conftest.py                       # Fixtures para E2E
    ├── docker-compose.e2e.yml            # Infraestructura completa
    ├── Dockerfile.test                   # Imagen de tests
    ├── run-e2e.sh                        # Script de ejecución
    └── README.md                         # Documentación E2E
```

---

## ✅ Resumen de Resultados

| Tipo de Test | Cantidad | Estado | Tiempo |
|--------------|----------|--------|--------|
| **Unit** | 15 | ✅ Todos pasando | 0.52s |
| **Integration** | 12 | ✅ 7 pasando (sin infra) | 0.22s |
| **E2E** | 27 | ✅ Todos pasando | 8.09s |
| **TOTAL** | **54** | ✅ **42 pasando** | **8.83s** |

> Nota: Los 5 integration tests de persistencia requieren Neo4j/Redis locales.
> Los 7 integration tests de detección de scopes funcionan sin infraestructura.

---

## 🚀 Quick Start

### Ejecutar todos los tests (que no requieren infra)
```bash
source .venv/bin/activate

# Unit tests (15 tests)
pytest tests/unit/services/context/test_persistence_unit.py -v

# Integration tests - Solo detección de scopes (7 tests)
pytest tests/integration/services/context/test_persistence_integration.py::TestScopeDetection -v
```

### Ejecutar E2E completos (con infraestructura)
```bash
# Script automatizado
./tests/e2e/services/context/run-e2e.sh

# El script:
# 1. Levanta Neo4j, Redis, NATS, Context Service
# 2. Ejecuta 27 tests E2E
# 3. Limpia contenedores
```

---

## 📚 Documentación Adicional

- **Unit Tests**: `tests/unit/services/context/README_PERSISTENCE.md`
- **Integration Tests**: `tests/integration/services/context/README.md`
- **E2E Tests**: `tests/e2e/services/context/README.md`

---

## 🎓 Aprendizajes Clave

1. **Testing Pyramid**: Cobertura en 3 niveles (unit → integration → e2e)
2. **Soft Deletes**: Las decisiones no se borran, se marcan como DELETED
3. **Graceful Degradation**: Errores de persistencia no crashean el servicio
4. **Scope Detection**: Análisis inteligente de contenido de prompts
5. **Batch Updates**: UpdateContext puede procesar múltiples cambios atómicamente

---

## 🔧 Implementaciones Probadas

Los tests verifican las implementaciones en `services/context/server.py`:

- ✅ `_process_context_change()` - Ruteo y validación
- ✅ `_persist_decision_change()` - Persistencia de decisiones
- ✅ `_persist_subtask_change()` - Persistencia de subtasks
- ✅ `_persist_milestone_change()` - Persistencia de eventos
- ✅ `_detect_scopes()` - Detección de scopes en prompts

Todas estas funciones pasaron de **stubs a implementaciones reales** y están **completamente testeadas**.

