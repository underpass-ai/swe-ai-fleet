# Auditoría API Síncrona y Asíncrona

Fecha: 2026-02-08  
Rama de trabajo: `audit/api-sync-async-review`

## Alcance revisado
- Contratos gRPC (`specs/fleet/**/*.proto`) y sus implementaciones servidor.
- Mensajería asíncrona (subjects, envelopes, consumidores, streams).
- Coherencia de contrato documentado (`specs/asyncapi.yaml`) vs comportamiento real.

## Hallazgos de API síncrona

### SYN-001 (Media) - RPCs legacy declaradas en Orchestrator sin uso interno
- Descripción:
  - El contrato declara `DeliberateForBacklogReview` y `GetDeliberationResult`, pero el servicer concreto no las sobreescribe.
  - Validación adicional del flujo backlog review confirma que el camino vigente es `Planning -> Ray Executor -> NATS -> backlog_review_processor`, sin llamadas internas a esos RPCs.
  - En la práctica son contrato legacy no consumido internamente (aunque su invocación directa seguiría devolviendo `UNIMPLEMENTED`).
- Evidencia:
  - `specs/fleet/orchestrator/v1/orchestrator.proto:18`
  - `specs/fleet/orchestrator/v1/orchestrator.proto:27`
  - `services/orchestrator/server.py:82`
  - `services/orchestrator/server.py:160`
  - `services/orchestrator/server.py:285`
  - `services/orchestrator/server.py:569`
  - `services/planning/server.py:469`
  - `services/planning/application/usecases/start_backlog_review_ceremony_usecase.py:389`
  - `services/backlog_review_processor/infrastructure/consumers/backlog_review_result_consumer.py:69`
- Impacto:
  - Deuda de contrato y confusión para integradores.
  - Riesgo de error `UNIMPLEMENTED` sólo para clientes que intenten usar explícitamente esos RPCs.

### SYN-002 (Alta) - Contrato `TaskDerivationPlanningService` huérfano en runtime
- Descripción:
  - Task Derivation usa un stub gRPC `TaskDerivationPlanningService` apuntando por defecto al servicio Planning.
  - No se encontró un servicer registrado para ese contrato en el server de Planning.
- Evidencia:
  - `specs/fleet/task_derivation/v1/task_derivation.proto:10`
  - `services/task_derivation/infrastructure/adapters/planning_service_adapter.py:61`
  - `services/task_derivation/server.py:145`
  - `services/planning/server.py:132`
  - `services/planning/server.py:666`
- Impacto:
  - Llamadas `GetPlanContext/CreateTasks/ListStoryTasks/SaveTaskDependencies` pueden fallar con `UNIMPLEMENTED`.

### SYN-003 (Media) - `WorkspaceService` definido sin implementación localizada
- Descripción:
  - Existe contrato proto de Workspace, pero no se localizó servicer/stub usage en servicios activos.
- Evidencia:
  - `specs/fleet/workspace/v1/workspace.proto:7`
  - Búsqueda sin resultados en `services/` para `WorkspaceServiceServicer` / `add_WorkspaceServiceServicer_to_server`.
- Impacto:
  - Riesgo de contrato muerto y confusión para integradores.

### SYN-004 (Alta) - Bug potencial en `GetActiveJobs`: `Timestamp` sin import
- Descripción:
  - El método construye `Timestamp()` pero no hay import correspondiente en el módulo.
- Evidencia:
  - `services/ray_executor/grpc_servicer.py:346`
  - `services/ray_executor/grpc_servicer.py:1`
- Impacto:
  - `NameError` en tiempo de ejecución al invocar `GetActiveJobs`.

### SYN-005 (Media) - Duplicidad y divergencia de proto de Workflow
- Descripción:
  - Conviven `specs/workflow.proto` y `specs/fleet/workflow/v1/workflow.proto` con diferencias sustanciales.
- Evidencia:
  - `specs/workflow.proto`
  - `specs/fleet/workflow/v1/workflow.proto`
- Impacto:
  - Riesgo de generación de stubs sobre archivo incorrecto y deriva de contrato.

## Hallazgos de API asíncrona

### ASY-001 (Crítica) - Desalineación de subject en `context.updated`
- Descripción:
  - El publisher emite en `context.events.updated` pero consumidores y AsyncAPI esperan `context.updated`.
- Evidencia:
  - `services/context/infrastructure/adapters/nats_messaging_adapter.py:159`
  - `services/context/infrastructure/adapters/nats_messaging_adapter.py:168`
  - `services/orchestrator/infrastructure/handlers/context_consumer.py:59`
  - `specs/asyncapi.yaml:36`
- Impacto:
  - Eventos de actualización de contexto no llegan al consumidor esperado.

### ASY-002 (Crítica) - `agent.response.failed` se publica sin `EventEnvelope`
- Descripción:
  - `publish_success` usa envelope, pero `publish_failure` publica JSON plano.
  - El consumidor del orquestador exige envelope y descarta mensajes inválidos.
- Evidencia:
  - `core/ray_jobs/infrastructure/adapters/nats_result_publisher.py:3`
  - `core/ray_jobs/infrastructure/adapters/nats_result_publisher.py:315`
  - `core/ray_jobs/infrastructure/adapters/nats_result_publisher.py:393`
  - `services/orchestrator/infrastructure/handlers/agent_response_consumer.py:289`
  - `services/orchestrator/infrastructure/handlers/agent_response_consumer.py:292`
- Impacto:
  - Pérdida silenciosa de eventos de fallo de agentes.

### ASY-003 (Alta) - AsyncAPI no modela el `EventEnvelope` real usado en runtime
- Descripción:
  - `EventEnvelope` real exige `event_type`, `payload`, `idempotency_key`, `correlation_id`, `timestamp`, `producer`.
  - AsyncAPI define `EventBase` con `event_id`, `case_id`, `ts`.
- Evidencia:
  - `core/shared/events/event_envelope.py:35`
  - `core/shared/events/infrastructure/required_envelope_parser.py:18`
  - `specs/asyncapi.yaml:119`
  - `specs/asyncapi.yaml:121`
- Impacto:
  - Contrato documental no representa el payload real; riesgo de integración y validación incorrecta.

### ASY-004 (Alta) - AsyncAPI incompleta frente a subjects activos
- Descripción:
  - No están documentados varios subjects reales (ej. `orchestration.*`, `workflow.*`, `context.update.request`, `context.rehydrate.request`, `planning.backlog_review.deliberations.complete`, `planning.backlog_review.tasks.complete`, etc.).
- Evidencia:
  - `services/orchestrator/infrastructure/handlers/nats_handler.py:83`
  - `services/orchestrator/infrastructure/handlers/nats_handler.py:108`
  - `services/workflow/domain/value_objects/nats_subjects.py:27`
  - `services/workflow/domain/value_objects/nats_subjects.py:31`
  - `services/context/nats_handler.py:192`
  - `services/context/nats_handler.py:199`
  - `services/backlog_review_processor/domain/value_objects/nats_subject.py:17`
  - `services/backlog_review_processor/domain/value_objects/nats_subject.py:18`
- Impacto:
  - Deriva de contrato y dificultad para observabilidad, onboarding e integraciones externas.

### ASY-005 (Alta) - Consumer de `agent.work.completed` sin productor identificado
- Descripción:
  - Workflow consume `agent.work.completed`, pero no se encontró productor en código productivo.
- Evidencia:
  - `services/workflow/infrastructure/consumers/agent_work_completed_consumer.py:80`
  - `services/workflow/domain/value_objects/nats_subjects.py:27`
  - Búsqueda en `services/` y `core/` sin publishers de `agent.work.completed`.
- Impacto:
  - Flujo de workflow puede quedar inactivo sin eventos de entrada.

### ASY-006 (Media-Alta) - Patrón de `stop()` re-lanza `CancelledError` y puede cortar cleanup
- Descripción:
  - Varios consumidores cancelan tareas y re-lanzan `CancelledError` en `stop()`.
  - Algunos servidores invocan `stop()` en secuencia sin capturar esa excepción en cleanup.
- Evidencia:
  - `services/backlog_review_processor/infrastructure/consumers/backlog_review_result_consumer.py:96`
  - `services/planning/infrastructure/consumers/task_derivation_result_consumer.py:218`
  - `services/task_derivation/infrastructure/consumers/task_derivation_request_consumer.py:68`
  - `services/task_derivation/infrastructure/consumers/task_derivation_result_consumer.py:79`
  - `services/backlog_review_processor/server.py:197`
  - `services/task_derivation/server.py:119`
- Impacto:
  - Cleanup incompleto (conexiones/adapters abiertos) durante apagado.

### ASY-007 (Media) - Acoplamiento implícito de streams (`task_derivation`)
- Descripción:
  - Task Derivation consume stream `task_derivation`, pero su server no inicializa streams.
  - El stream se crea en inicialización de otro servicio y/o job de infraestructura.
- Evidencia:
  - `services/task_derivation/infrastructure/nats_subjects.py:9`
  - `services/task_derivation/server.py:216`
  - `services/context/streams_init.py:53`
  - `deploy/k8s/20-streams/nats-streams-init.yaml:136`
- Impacto:
  - Dependencia operativa implícita y arranques frágiles fuera de Kubernetes/job completo.

## Priorización sugerida
1. ASY-001
2. ASY-002
3. SYN-001
4. SYN-002
5. SYN-004
6. ASY-003
7. ASY-004
8. ASY-005
9. ASY-006
10. ASY-007
11. SYN-003
12. SYN-005

## Historias de usuario generadas a partir de esta auditoría
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-001-orchestrator-rpcs-faltantes.md`
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-002-task-derivation-planning-service.md`
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-003-workspace-service-definicion.md`
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-004-ray-executor-timestamp.md`
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-005-context-updated-subject.md`
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-006-agent-response-failed-envelope.md`
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-007-asyncapi-event-envelope-y-subjects.md`
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-008-workflow-agent-work-completed.md`
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-009-shutdown-cancelled-error.md`
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-010-stream-ownership-task-derivation.md`
- `docs/analysis/API_SYNC_ASYNC_HISTORIAS_USUARIO/US-011-convergencia-workflow-proto.md`
