# US-002 - Alinear contrato Task Derivation <-> Planning (gRPC)

## Relacionada con
- `SYN-002` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Historia
Como servicio `task_derivation`,  
quiero consumir un endpoint gRPC realmente disponible para `GetPlanContext/CreateTasks/ListStoryTasks/SaveTaskDependencies`,  
para evitar errores `UNIMPLEMENTED` al hablar con Planning.

## Alcance
- Decidir contrato final:
  - Opción A (recomendada): Implementar `TaskDerivationPlanningService` en Planning.
  - Opción B: Eliminar ese contrato y migrar adapter a RPCs existentes de `PlanningService`.
- Actualizar adapter, server de Planning y tests según la opción elegida.

## ADR corto (decisión)
- **Fecha:** 2026-02-08
- **Decisión:** **Opción A**
- **Motivo:** Mantener estable el contrato consumido por `task_derivation` y eliminar `UNIMPLEMENTED` sin forzar migración de clientes a `PlanningService`.
- **Consecuencia:** Planning expone dos servicios gRPC en el mismo servidor:
  - `fleet.planning.v2.PlanningService`
  - `fleet.task_derivation.v1.TaskDerivationPlanningService`

## Contrato definitivo implementado
- Servicio implementado en Planning:
  - `GetPlanContext`
  - `CreateTasks`
  - `ListStoryTasks`
  - `SaveTaskDependencies`
- Orquestación asíncrona habilitada en Planning:
  - `PlanApprovedConsumer` (subject `planning.plan.approved`) arranca en `services/planning/server.py`.
  - `DeriveTasksFromPlanUseCase` publica `task.derivation.requested`.
- Registro en servidor:
  - `add_PlanningServiceServicer_to_server(...)`
  - `add_TaskDerivationPlanningServiceServicer_to_server(...)`
- Ajustes de stubs:
  - `services/planning/generate-protos.sh` ahora genera `task_derivation_pb2*`.
  - `services/planning/Dockerfile` ahora genera/copía stubs de `task_derivation.proto`.

## Cobertura agregada
- Unit tests del nuevo servicer:
  - `services/planning/tests/unit/infrastructure/grpc/test_task_derivation_planning_servicer.py`
- Test de integración roundtrip (4 RPCs):
  - `services/planning/tests/integration/test_task_derivation_planning_service_roundtrip.py`
- Test E2E en raíz del proyecto (contrato + flujo asíncrono real):
  - `e2e/tests/13-task-derivation-planning-service-grpc/test_task_derivation_planning_service_grpc.py`
  - Valida `planning.plan.approved -> task derivation -> tareas DEVELOPMENT` además del contrato gRPC.

## Criterios de aceptación
1. Las 4 operaciones del adapter ejecutan contra un endpoint implementado.
2. No hay `UNIMPLEMENTED` en integración Task Derivation ↔ Planning.
3. Tests unitarios y al menos un test de integración cubren roundtrip básico.
4. Existe validación E2E del trigger asíncrono de derivación de tareas (vía evento `planning.plan.approved`).
5. Documentación técnica actualizada con el contrato definitivo.

## Tareas técnicas
1. Definir ADR corto de elección A/B.
2. Implementar servicer o migrar adapter según decisión.
3. Ajustar generación de stubs/protos implicados.
4. Añadir pruebas de integración de contrato.

## Riesgos
- Romper consumidores si se migra contrato sin fase de compatibilidad.

## Dependencias
- Puede depender de cambios de proto y regeneración de stubs en CI.
