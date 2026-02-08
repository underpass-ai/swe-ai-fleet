# US-005 - Unificar subject de context.updated

## Relacionada con
- `ASY-001` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Historia
Como consumidor de eventos de contexto,
quiero que publisher y consumidores usen el mismo subject,
para que los eventos `context.updated` se entreguen correctamente.

## Alcance
- Elegir subject canónico (`context.updated` recomendado).
- Alinear publisher de Context, consumidores y tests.
- Actualizar AsyncAPI.

## Criterios de aceptación
1. Un evento publicado por Context es recibido por `OrchestratorContextConsumer`.
2. No quedan subjects divergentes (`context.events.updated` vs `context.updated`) en código productivo.
3. Tests de publisher/consumer cubren la ruta.

## Tareas técnicas
1. Cambiar subject de publicación en `NatsMessagingAdapter` de Context.
2. Ajustar fixtures/tests de contexto y orquestador.
3. Validar stream y durables existentes en NATS.
4. Actualizar contrato AsyncAPI.

## Riesgos
- Consumidores legacy que dependan del subject anterior. --> (Esto no es un riesgo ya que el proyecto esta en base super alpha y no es interesante tener consumidores legacy)
