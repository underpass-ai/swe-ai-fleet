# US-006 - Estandarizar `agent.response.failed` con EventEnvelope

## Relacionada con
- `ASY-002` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Historia
Como consumidor de fallos de agentes,
quiero que `agent.response.failed` use el mismo `EventEnvelope` que el resto de eventos,
para procesar errores sin pérdidas silenciosas.

## Alcance
- Cambiar `publish_failure` para publicar envelope.
- Mantener campos de negocio necesarios (`error`, `error_type`, `task_id`, etc.).
- Ajustar tests y consumidores si aplica.

## Criterios de aceptación
1. `agent.response.failed` llega con campos mínimos de `EventEnvelope` válidos.
2. `OrchestratorAgentResponseConsumer` procesa mensaje sin descartarlo por formato.
3. Pruebas unitarias de publisher y consumer reflejan nuevo contrato.

## Tareas técnicas
1. En `NATSResultPublisher.publish_failure`, envolver payload con `create_event_envelope`.
2. Actualizar tests de `core/ray_jobs/tests/unit/infrastructure/adapters/test_nats_result_publisher.py`.
3. Añadir prueba en consumidor de orquestador para caso de fallo con envelope.

## Riesgos
- Cambios en consumidores externos que hoy parseen JSON plano.  (Requiere de la lista de los consumidores externos)
