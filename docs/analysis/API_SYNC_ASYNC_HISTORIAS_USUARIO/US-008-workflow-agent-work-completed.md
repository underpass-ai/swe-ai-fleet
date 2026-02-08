# US-008 - Definir y asegurar productor de `agent.work.completed`

## Relacionada con
- `ASY-005` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Historia
Como servicio Workflow,  
quiero tener un productor explícito de `agent.work.completed` (o migrar a subject existente),  
para que el flujo de avance de estado no quede inactivo.

## Alcance
- Identificar origen canónico del evento de trabajo completado.
- Implementar publisher o migrar consumer a subject realmente producido.
- Alinear documentación y tests.

## Criterios de aceptación
1. Existe al menos un publisher productivo de `agent.work.completed` o el consumer usa un subject vigente.
2. Workflow recibe y procesa eventos en entorno local/integración.
3. Tests cubren el flujo completo de entrada a `ExecuteWorkflowActionUseCase`.

## Tareas técnicas
1. Diseñar contrato de payload y envelope del evento.
2. Implementar publisher en servicio responsable.
3. Ajustar `AgentWorkCompletedConsumer` si cambia el subject.
4. Actualizar AsyncAPI.

## Riesgos
- Duplicación de eventos si conviven dos subjects durante migración.
