# US-007 - Sincronizar AsyncAPI con contratos reales

## Relacionada con
- `ASY-003` y `ASY-004` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Historia
Como equipo de integración,  
quiero que `specs/asyncapi.yaml` refleje el envelope y subjects reales en producción,  
para generar clientes/documentación confiables.

## Alcance
- Reemplazar `EventBase` por un schema compatible con `EventEnvelope` real.
- Añadir channels faltantes críticos:
  - `orchestration.deliberation.completed`
  - `orchestration.task.dispatched`
  - `workflow.*` principales
  - `context.update.request|response`
  - `context.rehydrate.request|response`
  - `planning.backlog_review.deliberations.complete`
  - `planning.backlog_review.tasks.complete`
- Revisar `agent.response.completed.*` (subsubjects).

## Criterios de aceptación
1. AsyncAPI valida sintácticamente.
2. Schemas de mensajes incluyen campos de `EventEnvelope` usados por runtime.
3. Subjects críticos usados en código aparecen documentados.
4. Documento de mapeo `subject -> productor -> consumidor` queda versionado.

## Tareas técnicas
1. Actualizar `specs/asyncapi.yaml`.
2. Ejecutar validador de AsyncAPI en CI o script local.
3. Añadir tabla de trazabilidad en `docs/analysis/`.

## Riesgos
- Introducir breaking changes en consumidores de contrato auto-generado.
