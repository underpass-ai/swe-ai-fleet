# Context Service - Unit Tests de Persistencia

Tests unitarios para las funciones de persistencia del Context Service.

## 📋 Cobertura (15 tests)

### `TestProcessContextChange` (8 tests)
Tests para el método `_process_context_change` que procesa y rutea cambios de contexto:

- ✅ **test_validate_required_fields**: Valida que `operation`, `entity_type` y `entity_id` son requeridos
- ✅ **test_parse_json_payload**: Verifica parseo correcto del payload JSON
- ✅ **test_route_to_decision_handler**: Verifica ruteo a `_persist_decision_change` 
- ✅ **test_route_to_subtask_handler**: Verifica ruteo a `_persist_subtask_change`
- ✅ **test_route_to_milestone_handler**: Verifica ruteo a `_persist_milestone_change`
- ✅ **test_handle_unknown_entity_type**: Verifica que tipos desconocidos no crashean
- ✅ **test_handle_persistence_error_gracefully**: Verifica que errores Neo4j no crashean

### `TestPersistDecisionChange` (3 tests)
Tests para el método `_persist_decision_change` que persiste decisiones:

- ✅ **test_create_decision**: Verifica CREATE llama `upsert_entity` con propiedades correctas
- ✅ **test_update_decision**: Verifica UPDATE llama `upsert_entity` para actualizar
- ✅ **test_delete_decision**: Verifica DELETE marca como `status=DELETED` (soft delete)

### `TestPersistSubtaskChange` (1 test)
Tests para el método `_persist_subtask_change`:

- ✅ **test_update_subtask**: Verifica UPDATE de subtask con status y assignee

### `TestPersistMilestoneChange` (1 test)
Tests para el método `_persist_milestone_change`:

- ✅ **test_create_milestone**: Verifica creación de evento con timestamp automático

### `TestDetectScopes` (3 tests)
Tests para el método `_detect_scopes` que detecta scopes en prompts:

- ✅ **test_empty_content**: Contenido vacío retorna lista vacía
- ✅ **test_detect_single_scope**: Detecta un scope individual
- ✅ **test_ignore_empty_sections**: Ignora secciones con "No ..." indicators

## 🚀 Ejecución

```bash
source .venv/bin/activate

# Todos los tests unitarios de persistencia
pytest tests/unit/services/context/test_persistence_unit.py -v

# Solo una clase específica
pytest tests/unit/services/context/test_persistence_unit.py::TestProcessContextChange -v

# Con coverage
pytest tests/unit/services/context/test_persistence_unit.py --cov=services.context.server
```

## 📊 Resultado Esperado

```
collected 15 items

test_persistence_unit.py::TestProcessContextChange::test_validate_required_fields PASSED [ 6%]
test_persistence_unit.py::TestProcessContextChange::test_parse_json_payload PASSED      [13%]
test_persistence_unit.py::TestProcessContextChange::test_route_to_decision_handler PASSED [20%]
test_persistence_unit.py::TestProcessContextChange::test_route_to_subtask_handler PASSED [26%]
test_persistence_unit.py::TestProcessContextChange::test_route_to_milestone_handler PASSED [33%]
test_persistence_unit.py::TestProcessContextChange::test_handle_unknown_entity_type PASSED [40%]
test_persistence_unit.py::TestProcessContextChange::test_handle_persistence_error_gracefully PASSED [46%]
test_persistence_unit.py::TestPersistDecisionChange::test_create_decision PASSED        [53%]
test_persistence_unit.py::TestPersistDecisionChange::test_update_decision PASSED        [60%]
test_persistence_unit.py::TestPersistDecisionChange::test_delete_decision PASSED        [66%]
test_persistence_unit.py::TestPersistSubtaskChange::test_update_subtask PASSED          [73%]
test_persistence_unit.py::TestPersistMilestoneChange::test_create_milestone PASSED      [80%]
test_persistence_unit.py::TestDetectScopes::test_empty_content PASSED                   [86%]
test_persistence_unit.py::TestDetectScopes::test_detect_single_scope PASSED             [93%]
test_persistence_unit.py::TestDetectScopes::test_ignore_empty_sections PASSED          [100%]

========================= 15 passed in 0.52s =========================
```

## 🎯 Características de los Tests

### Uso de Mocks
- **Mock de Neo4jCommandStore**: No requiere Neo4j real
- **Mock de change objects**: Simula requests de gRPC
- **Verificación de llamadas**: Usa `assert_called_once()` para verificar interacciones

### Validación de Lógica
- **Ruteo correcto**: Verifica que cada entity_type va al handler correcto
- **Transformación de datos**: Verifica que payloads se transforman correctamente
- **Manejo de errores**: Verifica que errores no crashean el servicio
- **Soft deletes**: Verifica que DELETE marca como DELETED, no borra

### Sin Dependencias Externas
- **No requiere Neo4j**: Usa mocks
- **No requiere Redis**: Usa mocks
- **Ejecución rápida**: < 1 segundo
- **CI-friendly**: Puede correr en cualquier entorno

## 🔗 Relación con otros tests

- **Unit tests** (aquí): Lógica aislada con mocks ✅ 15 tests
- **Integration tests** (`tests/integration/`): Componentes con infraestructura real ✅ 12 tests
- **E2E tests** (`tests/e2e/`): Servicio completo via gRPC ✅ 27 tests

Total: **54 tests** cubriendo persistencia desde diferentes niveles.

