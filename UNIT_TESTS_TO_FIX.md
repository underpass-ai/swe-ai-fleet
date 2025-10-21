# Tests Unitarios a Arreglar

**Fecha:** 2025-10-18  
**Última actualización:** Después de arreglar generate-test-stubs.sh  
**Total inicial:** 56 tests (35 ERRORS + 21 FAILED)  
**Total actual:** 36 tests (16 ERRORS + 20 FAILED) ✅ **-20 tests arreglados!**

## 📊 Resumen por Categoría

| Categoría | Tests | Prioridad | Causa Raíz |
|-----------|-------|-----------|------------|
| **Módulos 'gen' faltantes** | 50 | 🔴 ALTA | `services.X.gen` no existe en tests |
| **Mocks async mal configurados** | 4 | 🟡 MEDIA | Mock no es awaitable |
| **Assertions incorrectas** | 2 | 🟢 BAJA | Estructura de datos cambió |

---

## 🔴 CATEGORIA 1: Módulos 'gen' Faltantes (50 tests)

### Problema
Los tests intentan importar o patchear módulos generados (`services.context.gen`, `services.orchestrator.gen`) que no existen en tiempo de test.

### Archivos Afectados

#### `tests/unit/services/context/test_server.py` (19 ERRORS)
```python
# Error: AttributeError: module 'services.context' has no attribute 'server'
# Causa: patch('services.context.server.Neo4jQueryStore') falla
```

**Tests:**
- `TestGetContext::test_get_context_success`
- `TestGetContext::test_get_context_with_subtask`
- `TestGetContext::test_get_context_error_handling`
- `TestGetContext::test_serialize_prompt_blocks`
- `TestGetContext::test_generate_version_hash`
- `TestUpdateContext::test_update_context_success`
- `TestUpdateContext::test_update_context_multiple_changes`
- `TestUpdateContext::test_update_context_with_nats`
- `TestUpdateContext::test_update_context_error_handling`
- `TestRehydrateSession::test_rehydrate_session_success`
- `TestRehydrateSession::test_rehydrate_session_multiple_roles`
- `TestRehydrateSession::test_rehydrate_session_error_handling`
- `TestValidateScope::test_validate_scope_allowed`
- `TestValidateScope::test_validate_scope_missing_scopes`
- `TestValidateScope::test_validate_scope_extra_scopes`
- `TestValidateScope::test_validate_scope_error_handling`
- `TestHelperMethods::test_detect_scopes`
- `TestHelperMethods::test_generate_context_hash`
- `TestHelperMethods::test_format_scope_reason`

#### `tests/unit/services/orchestrator/test_server.py` (16 ERRORS)
```python
# Error: AttributeError: module 'services.orchestrator' has no attribute 'server'
# Causa: patch('services.orchestrator.server.SystemConfig') falla
```

**Tests:**
- `TestDeliberate::test_deliberate_no_agents`
- `TestDeliberate::test_deliberate_unknown_role`
- `TestDeliberate::test_deliberate_error_handling`
- `TestOrchestrate::test_orchestrate_no_agents`
- `TestOrchestrate::test_orchestrate_error_handling`
- `TestGetStatus::test_get_status_basic`
- `TestGetStatus::test_get_status_with_stats`
- `TestGetStatus::test_get_status_error_handling`
- `TestHelperMethods::test_generate_execution_id`
- `TestHelperMethods::test_proto_to_constraints`
- `TestHelperMethods::test_check_suite_to_proto`
- `TestNewRPCs::test_list_councils`
- `TestNewRPCs::test_register_agent_no_council`
- `TestNewRPCs::test_derive_subtasks_unimplemented`
- `TestNewRPCs::test_get_task_context_unimplemented`
- `TestNewRPCs::test_process_planning_event_unimplemented`

#### `tests/unit/services/context/test_persistence_unit.py` (15 FAILED)
```python
# Error: ModuleNotFoundError: No module named 'services.context.gen'
# Causa: from services.context.gen import context_pb2 falla
```

**Tests:**
- `TestProcessContextChange::test_validate_required_fields`
- `TestProcessContextChange::test_parse_json_payload`
- `TestProcessContextChange::test_route_to_decision_handler`
- `TestProcessContextChange::test_route_to_subtask_handler`
- `TestProcessContextChange::test_route_to_milestone_handler`
- `TestProcessContextChange::test_handle_unknown_entity_type`
- `TestProcessContextChange::test_handle_persistence_error_gracefully`
- `TestPersistDecisionChange::test_create_decision`
- `TestPersistDecisionChange::test_update_decision`
- `TestPersistDecisionChange::test_delete_decision`
- `TestPersistSubtaskChange::test_update_subtask`
- `TestPersistMilestoneChange::test_create_milestone`
- `TestDetectScopes::test_empty_content`
- `TestDetectScopes::test_detect_single_scope`
- `TestDetectScopes::test_ignore_empty_sections`

### Solución
```bash
# Opción 1: Generar stubs antes de tests (ya existe script)
bash scripts/generate-test-stubs.sh

# Opción 2: Mock el import en conftest.py
# Opción 3: Usar pytest fixture autouse para generar módulos
```

---

## 🟡 CATEGORIA 2: Mocks Async Mal Configurados (4 tests)

### Problema
```python
# Error: TypeError: object Mock can't be used in 'await' expression
# Causa: await self.js.pull_subscribe(...) pero pull_subscribe es Mock, no AsyncMock
```

### Archivos Afectados

#### `tests/unit/context/consumers/test_orchestration_consumer.py` (1 FAILED)
- `TestOrchestrationEventsConsumer::test_start_subscribes_to_events`

#### `tests/unit/context/consumers/test_planning_consumer.py` (3 FAILED)
- `TestPlanningEventsConsumer::test_start_subscribes_to_events`
- `TestPlanningEventsConsumer::test_handle_story_transitioned_records_in_graph`
- `TestPlanningEventsConsumer::test_handle_plan_approved_records_in_graph`

### Solución
```python
# ANTES (incorrecto):
mock_js.pull_subscribe = Mock(return_value=mock_subscription)

# DESPUÉS (correcto):
mock_js.pull_subscribe = AsyncMock(return_value=mock_subscription)
```

---

## 🟢 CATEGORIA 3: Assertions Incorrectas (2 tests)

### Problema
```python
# Error 1: KeyError: 'entity_type'
# Error 2: AssertionError: Expected 'ack' to have been called once. Called 0 times.
```

### Archivos Afectados

#### `tests/unit/context/consumers/test_orchestration_consumer.py` (1 FAILED)
- `TestOrchestrationEventsConsumer::test_handle_task_dispatched_records_dispatch_event`
  - **Causa**: `call_args[1]["entity_type"]` no existe
  - **Fix**: Verificar estructura real de `call_args`

#### `tests/unit/context/consumers/test_planning_consumer.py` (1 FAILED)
- `TestPlanningEventsConsumer::test_handle_plan_approved_handles_graph_error`
  - **Causa**: `msg.ack` no se llama cuando hay error en graph
  - **Fix**: Ajustar lógica de consumer o test

### Solución
1. Leer código actual del consumer
2. Verificar qué estructura de datos se pasa realmente
3. Ajustar assertions en tests

---

## 🎯 Plan de Acción Recomendado

### Fase 1: Arreglar CATEGORIA 1 (50 tests) 🔴
1. Crear fixture pytest para generar módulos 'gen' automáticamente
2. O modificar `conftest.py` para mockear imports de 'gen'
3. O usar `scripts/generate-test-stubs.sh` en CI

**Impacto:** Desbloqueará 50 tests de golpe

### Fase 2: Arreglar CATEGORIA 2 (4 tests) 🟡
1. Modificar fixtures de consumers para usar `AsyncMock`
2. Verificar que todos los métodos async estén mockeados correctamente

**Impacto:** Arreglará 4 tests

### Fase 3: Arreglar CATEGORIA 3 (2 tests) 🟢
1. Investigar lógica de consumers
2. Ajustar assertions para coincidir con comportamiento real

**Impacto:** Arreglará 2 tests finales

---

## 📈 Progreso Esperado

| Fase | Tests Arreglados | Tests Restantes | % Completado |
|------|------------------|-----------------|--------------|
| Inicial | 0 | 56 | 0% |
| Después de Fase 1 | 50 | 6 | 89% |
| Después de Fase 2 | 54 | 2 | 96% |
| Después de Fase 3 | 56 | 0 | 100% |

---

## ⚠️ Notas Importantes

1. **Estos errores ya existían ANTES de la migración de `ray_jobs`**
   - La migración no introdujo regresiones
   - Los tests de `ray_jobs` pasan correctamente ✅

2. **Warnings de deprecación (4):**
   ```python
   # datetime.utcnow() → datetime.now(datetime.UTC)
   # No bloquean tests, solo warnings
   ```

3. **Tests relacionados con ray_jobs:**
   ```
   tests/unit/ray_jobs/test_vllm_agent_job_unit.py: 12 passed, 1 skipped ✅
   ```

---

## 🔗 Referencias

- Script de generación: `scripts/generate-test-stubs.sh`
- Configuración pytest: `pytest.ini`
- Tests unitarios: `tests/unit/`

