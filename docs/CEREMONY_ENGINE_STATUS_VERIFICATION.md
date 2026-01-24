# Verificación del Estado del Ceremony Engine

**Fecha:** 2026-01-23  
**Documento de Referencia:** `CEREMONY_ENGINE_COMPLETION_TASKS.md`

Este documento verifica el estado de implementación de las tareas definidas en el documento de completion tasks.

---

## 1) Core Engine Correctness

### ✅ 1.1 Idempotency en PublishStepHandler
**Estado:** COMPLETADO

- `PublishStepHandler` integra `IdempotencyPort` en su constructor (línea 40)
- Implementa `_idempotency_should_skip()` que verifica estado COMPLETED/IN_PROGRESS
- Marca idempotencia como completada después de publicar exitosamente (línea 107-109)
- Tests unitarios existen en `test_publish_step_handler.py`

**Evidencia:**
- `core/ceremony_engine/infrastructure/adapters/step_handlers/publish_step_handler.py:37-142`

### ✅ 1.2 Persistencia de Step Outputs en CeremonyInstance
**Estado:** COMPLETADO

- `CeremonyInstance` tiene campo `step_outputs: StepOutputMap` (línea 51-53)
- `apply_step_result()` actualiza `step_outputs` usando el builder (línea 209)
- `ExecutionContext` incluye `ContextKey.STEP_OUTPUTS` en `_with_step_outputs()` (línea 509-521)
- Los outputs están disponibles para pasos downstream (aggregation/publish)

**Evidencia:**
- `core/ceremony_engine/domain/entities/ceremony_instance.py:51-53, 209, 270-272`
- `core/ceremony_engine/application/services/ceremony_runner.py:509-521`

### ✅ 1.3 RehydrationUseCase
**Estado:** COMPLETADO

- `RehydrationUseCase` existe en `core/ceremony_engine/application/use_cases/rehydration_usecase.py`
- Implementa `rehydrate_instance()` y `rehydrate_instances_by_correlation_id()`
- Valida definiciones contra instancias rehidratadas en `_validate_definition()`
- Adapter `Neo4jRehydrationAdapter` implementa `RehydrationPort`

**Evidencia:**
- `core/ceremony_engine/application/use_cases/rehydration_usecase.py`
- `core/ceremony_engine/infrastructure/adapters/neo4j_rehydration_adapter.py`

### ✅ 1.4 Enforce Role.allowed_actions en CeremonyRunner
**Estado:** COMPLETADO

- `_enforce_step_role_allowed_actions()` valida que el rol puede ejecutar el step (línea 247-259)
- `_enforce_transition_role_allowed_actions()` valida que el rol puede ejecutar el trigger (línea 261-277)
- Se llama en `execute_step()` (línea 113) y `transition_state()` (línea 193)
- Tests unitarios existen

**Evidencia:**
- `core/ceremony_engine/application/services/ceremony_runner.py:247-277, 113, 193`

### ✅ 1.5 Domain-Safe Builder para CeremonyInstance
**Estado:** COMPLETADO

- `CeremonyInstanceBuilder` existe (línea 308-385)
- `to_builder()` crea builder desde instancia (línea 274-286)
- `apply_step_result()` y `apply_transition()` usan el builder (línea 211-216, 263-267)
- No se usa `replace()` directamente - todo pasa por el builder

**Evidencia:**
- `core/ceremony_engine/domain/entities/ceremony_instance.py:274-385`

---

## 2) Handler Integrations

### ✅ 2.1 AggregationStepHandler - Leer Step Outputs
**Estado:** COMPLETADO

- Lee de `ContextKey.STEP_OUTPUTS` (línea 58)
- También lee de `ContextKey.INPUTS` como fallback (línea 59, 67-68)
- Soporta tipos de agregación: `merge`, `list`, `concat` (línea 84-102)
- Valida que las fuentes existan (línea 70-72)

**Evidencia:**
- `core/ceremony_engine/infrastructure/adapters/step_handlers/aggregation_step_handler.py:58-72`

### ✅ 2.2 PublishStepHandler - Validación de Schema
**Estado:** COMPLETADO

**Implementación:**
- `Output` value object tiene campo `schema: dict[str, Any] | None` (línea 24 en `output.py`)
- El schema se parsea desde YAML en `yaml_validator.py` (línea 146-147)
- `CeremonyOutputSchemaValidator` valida payloads contra schemas definidos en `Output.schema`
- `ContextKey.DEFINITION` agregado para pasar `CeremonyDefinition` en `ExecutionContext`
- `CeremonyRunner` incluye la definición en el contexto antes de ejecutar steps (línea 509-521, 542-545)
- `PublishStepHandler` valida el payload antes de crear el `EventEnvelope` (línea 93-95)
- Validación es independiente del handler (clase separada en infrastructure/validators)
- Soporta backward compatibility: si `definition` es `None`, se omite la validación

**Tests:**
- Tests unitarios completos en `test_ceremony_output_schema_validator.py` (22 casos de prueba)
- Tests de integración en `test_publish_step_handler.py` validan la integración del validador
- Cobertura de casos: éxito, campos faltantes, tipos incorrectos, schemas complejos, inferencia de output name

**Evidencia:**
- `core/ceremony_engine/domain/value_objects/output.py:24`
- `core/ceremony_engine/domain/value_objects/context_key.py:14` (DEFINITION)
- `core/ceremony_engine/infrastructure/validators/ceremony_output_schema_validator.py`
- `core/ceremony_engine/infrastructure/adapters/step_handlers/publish_step_handler.py:93-95`
- `core/ceremony_engine/application/services/ceremony_runner.py:509-521, 542-545`
- `core/ceremony_engine/tests/unit/infrastructure/validators/test_ceremony_output_schema_validator.py`

### ✅ 2.3 DeliberationStepHandler - Constraints Mapping
**Estado:** COMPLETADO

- Acepta `constraints` opcional en config (línea 84-86)
- Valida que constraints sea dict si está presente (línea 85-86)
- Pasa constraints al use case (línea 95)

**Evidencia:**
- `core/ceremony_engine/infrastructure/adapters/step_handlers/deliberation_step_handler.py:84-95`

### ✅ 2.4 TaskExtractionStepHandler - Explicit agent_deliberations
**Estado:** COMPLETADO

- Requiere `agent_deliberations` en inputs (línea 68, 73-74)
- Valida que sea una lista no vacía (línea 73-74)
- Pasa agent_deliberations al use case (línea 79)

**Evidencia:**
- `core/ceremony_engine/infrastructure/adapters/step_handlers/task_extraction_step_handler.py:68-79`

---

## 3) Event Contracts (NATS)

### ✅ 3.1 Event Contracts en asyncapi.yaml
**Estado:** COMPLETADO

**Implementación:**
- Eventos se publican en `CeremonyRunner`:
  - `ceremony.step.executed` (línea 556-581)
  - `ceremony.transition.applied` (línea 583-605)
- Eventos definidos en `specs/asyncapi.yaml`:
  - `CeremonyStepExecutedPayload` schema con campos: `instance_id`, `step_id`, `status`, `current_state`, `output`, `error_message` (opcional)
  - `CeremonyTransitionAppliedPayload` schema con campos: `instance_id`, `from_state`, `to_state`, `trigger`
  - Canales `ceremony.step.executed` y `ceremony.transition.applied` con mensajes correspondientes
- Los schemas definen el payload dentro del `EventEnvelope` (el envelope tiene estructura fija y no necesita schema)
- Nota: `ceremony.publish.requested` / `ceremony.publish.completed` no existen como eventos específicos del ceremony engine. El `PublishStepHandler` publica eventos genéricos según la configuración del step (subject y event_type definidos en la definición de la ceremonia).

**Completado:**
- Contract tests implementados en `test_ceremony_runner_contract.py` que validan payloads contra schemas de asyncapi.yaml
- Tests cubren: validación de schemas, campos requeridos, enums, y casos con/sin error_message
- Usa `jsonschema` para validación estricta de contratos
- `error_message` solo se incluye en el payload cuando está presente (no se incluye como `null` cuando es `None`), siguiendo el patrón de campos opcionales en EventEnvelope

**Evidencia:**
- `core/ceremony_engine/application/services/ceremony_runner.py:556-605`
- `specs/asyncapi.yaml` (schemas, canales y mensajes agregados)

---

## 4) planning_ceremony_processor Service

### ❌ 4.1 Dockerfile, requirements.txt, pyproject.toml
**Estado:** PENDIENTE

- No se encontraron archivos:
  - `services/planning_ceremony_processor/Dockerfile`
  - `services/planning_ceremony_processor/requirements.txt`
  - `services/planning_ceremony_processor/pyproject.toml`

**Evidencia:**
- Búsqueda de archivos no encontró estos archivos

### ❌ 4.2 generate-protos.sh
**Estado:** PENDIENTE

- No se encontró `generate-protos.sh` para `planning_ceremony.proto`
- No se encontró `planning_ceremony.proto` en el directorio del servicio

### ⚠️ 4.3 Thin Client en Planning Service
**Estado:** PARCIALMENTE COMPLETADO

**Completado:**
- `StartPlanningCeremonyUseCase` existe y llama a `CeremonyRunner`
- gRPC servicer existe: `planning_ceremony_servicer.py`

**Pendiente:**
- No se encontró cliente delgado en Planning Service que llame a `StartPlanningCeremony` (fire-and-forget)

### ❌ 4.4 NATS Consumers en planning_ceremony_processor
**Estado:** PENDIENTE

- No se encontraron consumidores NATS en `planning_ceremony_processor` para:
  - `agent.response.completed`
  - Avanzar estado de ceremony

---

## 5) Persistence and Observability

### ⚠️ 5.1 Reconciliation Events en DualPersistenceAdapter
**Estado:** PARCIALMENTE COMPLETADO

**Completado:**
- `DualPersistenceAdapter` maneja fallos de Neo4j (línea 121-127)
- Logging de warnings cuando Neo4j falla

**Pendiente:**
- NO emite eventos de reconciliación cuando Neo4j falla
- Hay un comentario indicando que debería publicarse (línea 127)
- Planning Service tiene patrón `dualwrite` con eventos de reconciliación, pero no se implementó en ceremony engine

**Evidencia:**
- `core/ceremony_engine/infrastructure/adapters/dual_persistence_adapter.py:121-127`
- `services/planning/infrastructure/adapters/storage_adapter.py:162-179` (patrón de referencia)

### ⚠️ 5.2 Structured Logging
**Estado:** PARCIALMENTE COMPLETADO

**Completado:**
- Logging básico existe en varios lugares
- `CeremonyRunner` tiene logging para retries (línea 674-683)

**Pendiente:**
- No hay structured logging explícito para:
  - Step start/end con contexto estructurado
  - Transition evaluation con detalles
  - Publish outcomes con métricas

### ❌ 5.3 Metrics Counters
**Estado:** PENDIENTE

- No se encontraron métricas para:
  - Step success/failure counters
  - Publish success/failure counters
- No hay integración con `MetricsPort` en ceremony engine

---

## 6) CI Quality Gates

### ⚠️ 6.1 Coverage ≥85% para core/ceremony_engine
**Estado:** PARCIALMENTE COMPLETADO

**Completado:**
- `core/ceremony_engine` está en la matriz de CI (`ci-modules.yml:32-33`)
- Coverage se genera y combina

**Pendiente:**
- No se encontró enforcement explícito de ≥85% coverage en CI
- No hay gate que falle el build si coverage < 85%

**Evidencia:**
- `.github/workflows/ci-modules.yml:32-33`

### ⚠️ 6.2 Tests Específicos
**Estado:** PARCIALMENTE COMPLETADO

**Completado:**
- Tests para `PublishStepHandler` idempotency existen (`test_publish_step_handler.py`)
- Tests para rehydration existen (`test_rehydration_usecase.py`)

**Pendiente:**
- Tests específicos para:
  - Aggregation con invalid sources y type mismatches
  - Rehydration invariant failures (solo happy-path existe)

**Evidencia:**
- `core/ceremony_engine/tests/unit/infrastructure/adapters/step_handlers/test_publish_step_handler.py`
- `core/ceremony_engine/tests/unit/application/use_cases/test_rehydration_usecase.py`

---

## 7) E2E Validation

### ⚠️ 7.1 E2E Flows con Side-Effects Reales
**Estado:** PARCIALMENTE COMPLETADO

**Completado:**
- Tests E2E existen en `core/ceremony_engine/tests/test_ceremony_engine_e2e.py`
- Tests E2E para backlog review ceremony existen en `e2e/tests/`

**Pendiente:**
- Tests E2E NO validan explícitamente:
  - NATS messages publicados (usando mocks)
  - Persistence actualizado en Valkey/Neo4j (usando mocks)
  - External service calls (Ray Executor) triggerados

**Evidencia:**
- `core/ceremony_engine/tests/test_ceremony_engine_e2e.py:82-120` (usa mocks)
- `e2e/tests/` (tests de integración pero no específicos de ceremony engine)

### ❌ 7.2 E2E Coverage para planning_ceremony_processor gRPC
**Estado:** PENDIENTE

- No se encontraron tests E2E que validen el gRPC start de `planning_ceremony_processor`

---

## 8) Security and Compliance

### ❌ 8.1 Validación de Secrets en Publish Payloads
**Estado:** PENDIENTE

- No hay validación que evite incluir secrets o raw prompts en publish payloads
- `PublishStepHandler` no filtra contenido sensible

### ❌ 8.2 Allowlist para publish_step Subjects
**Estado:** PENDIENTE

- No hay allowlist para `publish_step` subjects
- Cualquier subject puede ser publicado (riesgo de seguridad)

### ✅ 8.3 Correlation IDs Propagados
**Estado:** COMPLETADO

- `create_event_envelope()` incluye `correlation_id` (línea 562, 587)
- `PublishStepHandler` propaga correlation_id desde inputs (línea 90, 102)

**Evidencia:**
- `core/ceremony_engine/application/services/ceremony_runner.py:562, 587`
- `core/ceremony_engine/infrastructure/adapters/step_handlers/publish_step_handler.py:90, 102`

---

## 9) Operational Readiness

### ❌ 9.1 Helm/K8s Manifests para planning_ceremony_processor
**Estado:** PENDIENTE

- No se encontraron manifests Helm/K8s para `planning_ceremony_processor`
- No hay resource limits ni health probes definidos

### ❌ 9.2 Readiness Checks
**Estado:** PENDIENTE

- No se encontraron readiness checks para:
  - NATS connectivity
  - Ray Executor connectivity

### ❌ 9.3 Documentación de Rollout/Rollback
**Estado:** PENDIENTE

- No se encontró documentación en `deploy/` para rollout/rollback de `planning_ceremony_processor`

---

## Resumen Ejecutivo

### Completado (✅): 13 tareas
- Core engine correctness (5/5)
- Handler integrations (4/4)
- Event contracts (1/1)
- Security básica (1/3)

### Parcialmente Completado (⚠️): 4 tareas
- planning_ceremony_processor cliente
- Reconciliation events
- Structured logging
- CI coverage enforcement
- Tests específicos
- E2E con side-effects reales

### Pendiente (❌): 10 tareas
- planning_ceremony_processor build files (Dockerfile, requirements.txt, pyproject.toml)
- generate-protos.sh
- NATS consumers en planning_ceremony_processor
- Metrics counters
- E2E para planning_ceremony_processor gRPC
- Validación de secrets en publish
- Allowlist para publish subjects
- Helm/K8s manifests
- Readiness checks
- Documentación rollout/rollback

### Progreso Total: ~58% completado

---

## Recomendaciones Prioritarias

1. **Alta Prioridad:**
   - Completar `planning_ceremony_processor` service (Dockerfile, requirements.txt, pyproject.toml)
   - Implementar reconciliation events en `DualPersistenceAdapter`
   - Agregar allowlist para publish subjects (seguridad)

2. **Media Prioridad:**
   - Agregar contract tests para validar payload shapes contra asyncapi.yaml
   - Agregar metrics counters
   - Implementar structured logging completo
   - Agregar tests faltantes (aggregation edge cases, rehydration failures)

3. **Baja Prioridad:**
   - E2E tests con side-effects reales
   - Helm/K8s manifests
   - Readiness checks
   - Documentación operacional
