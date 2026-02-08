# US-001 - Deprecar RPCs legacy no usadas en Orchestrator

## Relacionada con
- `SYN-001` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Decisión (validada)
Tras revisar el flujo real de backlog review, **no es necesario implementar**
`DeliberateForBacklogReview` ni `GetDeliberationResult`.

El flujo actual funciona así:
1. Planning envía deliberaciones de backlog review directamente a Ray Executor.
2. Ray publica resultados por NATS.
3. `backlog_review_processor` consume, acumula, dispara extracción de tareas y publica progreso.

Por tanto, estos RPCs en Orchestrator son contrato legacy no consumido en runtime interno.

## Evidencia técnica
- RPCs declaradas en proto:
  - `specs/fleet/orchestrator/v1/orchestrator.proto:18`
  - `specs/fleet/orchestrator/v1/orchestrator.proto:27`
- Servicer sin implementación explícita de esos métodos:
  - `services/orchestrator/server.py:82`
  - `services/orchestrator/server.py:160`
  - `services/orchestrator/server.py:285`
  - `services/orchestrator/server.py:569`
- README del propio servicio ya las marca como no implementadas:
  - `services/orchestrator/README.md:29`
- Flujo real backlog review en Planning usa Ray Executor (no Orchestrator):
  - `services/planning/server.py:469`
  - `services/planning/server.py:499`
  - `services/planning/application/usecases/start_backlog_review_ceremony_usecase.py:389`
- Flujo asíncrono real en `backlog_review_processor`:
  - `services/backlog_review_processor/infrastructure/consumers/backlog_review_result_consumer.py:69`
  - `services/backlog_review_processor/application/usecases/accumulate_deliberations_usecase.py:229`
  - `services/backlog_review_processor/infrastructure/consumers/deliberations_complete_consumer.py:72`
  - `services/backlog_review_processor/infrastructure/consumers/task_extraction_result_consumer.py:98`
  - `services/backlog_review_processor/infrastructure/consumers/task_extraction_result_consumer.py:623`

## Historia (reformulada)
Como owner de contratos gRPC,  
quiero deprecar/eliminar RPCs legacy no usadas de `OrchestratorService`,  
para evitar expectativas falsas de integración y reducir deuda de contrato.

## Alcance
- No implementar `DeliberateForBacklogReview` ni `GetDeliberationResult`.
- Alinear proto, README y docs de arquitectura con el flujo real (`Planning -> Ray Executor -> NATS -> backlog_review_processor`).
- Limpiar artefactos legacy en Planning vinculados a `OrchestratorPort` para backlog review (si no tienen uso).

## Criterios de aceptación
1. Existe decisión documentada de deprecación con evidencia de no uso interno.
2. README y documentación de arquitectura no presentan esos RPCs como camino vigente.
3. Se define estrategia de compatibilidad:
   - Opción A: mantener temporalmente en proto como deprecated.
   - Opción B: eliminar en versión mayor del contrato.
4. No se rompe el flujo actual de backlog review (Planning + backlog_review_processor).

## Tareas técnicas sugeridas
1. Marcar ambos RPCs como deprecated en `orchestrator.proto` (fase transitoria) o planificar su remoción versionada.
2. Actualizar `services/orchestrator/README.md` y docs de arquitectura.
3. Ejecutar búsqueda de uso en `services/` y `core/` para confirmar cero call-sites antes de remover.
4. Revisar limpieza de `OrchestratorPort`/mappers legacy en Planning si siguen sin consumidores.

## Riesgos
- Posibles consumidores externos fuera de este repositorio.
- Cambios de proto sin versionado pueden romper clientes no inventariados.

## Mitigación
- Comunicar deprecación con fecha de retiro.
- Mantener ventana de transición y verificación de telemetría/uso antes de eliminar.
