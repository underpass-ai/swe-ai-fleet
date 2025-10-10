# Context Service - Integration Tests

Tests de integración para el Context Service que verifican la persistencia de datos y la lógica de detección de scopes.

## 📋 Cobertura de Tests

### 🔄 Persistencia (requiere Neo4j + Redis)

#### `TestDecisionPersistence`
- ✅ **test_create_decision**: Verifica creación de nuevas decisiones en Neo4j
- ✅ **test_update_decision**: Verifica actualización de decisiones existentes
- ✅ **test_delete_decision**: Verifica soft-delete de decisiones (marca como DELETED)

#### `TestSubtaskPersistence`
- ✅ **test_update_subtask**: Verifica actualización de subtasks (estado, assignee, etc.)

#### `TestMilestonePersistence`
- ✅ **test_create_milestone**: Verifica creación de eventos/milestones con timestamp

### 🔍 Detección de Scopes (no requiere infraestructura)

#### `TestScopeDetection`
- ✅ **test_detect_case_header_scope**: Detecta `CASE_HEADER` en contenido
- ✅ **test_detect_plan_header_scope**: Detecta `PLAN_HEADER` en contenido
- ✅ **test_detect_subtasks_scope**: Detecta `SUBTASKS_ROLE` cuando hay subtasks
- ✅ **test_detect_decisions_scope**: Detecta `DECISIONS_RELEVANT_ROLE` cuando hay decisiones
- ✅ **test_detect_milestones_scope**: Detecta `MILESTONES` cuando hay eventos
- ✅ **test_detect_no_scopes_when_empty**: No detecta scopes cuando contenido indica vacío
- ✅ **test_detect_multiple_scopes**: Detecta múltiples scopes en mismo contenido

## 🚀 Ejecución

### Todos los tests de integración
```bash
source .venv/bin/activate
pytest tests/integration/services/context/ -v -m integration
```

### Solo tests de detección de scopes (sin infraestructura)
```bash
source .venv/bin/activate
pytest tests/integration/services/context/test_persistence_integration.py::TestScopeDetection -v
```

### Solo tests de persistencia (requiere Neo4j + Redis)
```bash
source .venv/bin/activate
pytest tests/integration/services/context/test_persistence_integration.py::TestDecisionPersistence -v -m integration
pytest tests/integration/services/context/test_persistence_integration.py::TestSubtaskPersistence -v -m integration
pytest tests/integration/services/context/test_persistence_integration.py::TestMilestonePersistence -v -m integration
```

## 🐳 Prerequisitos para Tests de Persistencia

Los tests de persistencia requieren Neo4j y Redis corriendo:

```bash
# Usando los contenedores de E2E
podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml up -d neo4j redis

# O usar tus instancias locales con variables de entorno
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
```

## 📊 Salida Esperada

```
collected 12 items

test_persistence_integration.py::TestDecisionPersistence::test_create_decision PASSED     [  8%]
test_persistence_integration.py::TestDecisionPersistence::test_update_decision PASSED     [ 16%]
test_persistence_integration.py::TestDecisionPersistence::test_delete_decision PASSED     [ 25%]
test_persistence_integration.py::TestSubtaskPersistence::test_update_subtask PASSED       [ 33%]
test_persistence_integration.py::TestMilestonePersistence::test_create_milestone PASSED   [ 41%]
test_persistence_integration.py::TestScopeDetection::test_detect_case_header_scope PASSED [ 50%]
test_persistence_integration.py::TestScopeDetection::test_detect_plan_header_scope PASSED [ 58%]
test_persistence_integration.py::TestScopeDetection::test_detect_subtasks_scope PASSED    [ 66%]
test_persistence_integration.py::TestScopeDetection::test_detect_decisions_scope PASSED   [ 75%]
test_persistence_integration.py::TestScopeDetection::test_detect_milestones_scope PASSED  [ 83%]
test_persistence_integration.py::TestScopeDetection::test_detect_no_scopes_when_empty PASSED [ 91%]
test_persistence_integration.py::TestScopeDetection::test_detect_multiple_scopes PASSED   [100%]

========================= 12 passed in 0.5s =========================
```

## 🎯 Objetivo de los Tests

Estos tests verifican que las implementaciones de persistencia en `services/context/server.py` funcionan correctamente:

1. **Persistencia real a Neo4j**: Usando `Neo4jCommandStore.upsert_entity()`
2. **Detección inteligente de scopes**: Analizando el contenido de prompts generados
3. **Manejo de diferentes operaciones**: CREATE, UPDATE, DELETE
4. **Soft deletes**: Las decisiones no se borran, se marcan como DELETED
5. **Timestamps automáticos**: Los eventos incluyen timestamp_ms

## 🔗 Relación con E2E Tests

- **E2E tests** (`tests/e2e/services/context/`): Prueban el servicio completo via gRPC
- **Integration tests** (este directorio): Prueban componentes individuales con infraestructura real
- **Unit tests** (`tests/unit/services/context/`): Prueban lógica sin infraestructura

## 🐛 Troubleshooting

### Tests se saltan (skip)
```
5 skipped - Neo4j not available
```
**Solución**: Levantar Neo4j y Redis (ver sección Prerequisitos)

### Error de conexión
```
Neo4j not available: Unable to connect
```
**Solución**: Verificar que Neo4j esté corriendo en el puerto correcto:
```bash
podman ps | grep neo4j
```

### Conflictos de puerto
Si tienes Kubernetes usando los puertos estándar, usa los puertos remapeados del docker-compose E2E:
```bash
export NEO4J_URI="bolt://localhost:17687"
export REDIS_PORT="16379"
```

