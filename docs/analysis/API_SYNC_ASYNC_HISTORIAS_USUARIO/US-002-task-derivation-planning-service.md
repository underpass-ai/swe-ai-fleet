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

## Criterios de aceptación
1. Las 4 operaciones del adapter ejecutan contra un endpoint implementado.
2. No hay `UNIMPLEMENTED` en integración Task Derivation ↔ Planning.
3. Tests unitarios y al menos un test de integración cubren roundtrip básico.
4. Documentación técnica actualizada con el contrato definitivo.

## Tareas técnicas
1. Definir ADR corto de elección A/B.
2. Implementar servicer o migrar adapter según decisión.
3. Ajustar generación de stubs/protos implicados.
4. Añadir pruebas de integración de contrato.

## Riesgos
- Romper consumidores si se migra contrato sin fase de compatibilidad.

## Dependencias
- Puede depender de cambios de proto y regeneración de stubs en CI.
