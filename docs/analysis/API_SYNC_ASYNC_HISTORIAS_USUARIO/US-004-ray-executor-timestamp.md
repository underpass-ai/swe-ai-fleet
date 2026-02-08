# US-004 - Corregir bug de Timestamp en GetActiveJobs

## Relacionada con
- `SYN-004` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Historia
Como consumidor de `RayExecutorService.GetActiveJobs`,  
quiero recibir la respuesta sin errores de runtime,  
para consultar trabajos activos de forma estable.

## Alcance
- Importar correctamente `Timestamp` y validar serialización de `start_time`.
- Añadir test unitario del método `GetActiveJobs`.

## Criterios de aceptación
1. `GetActiveJobs` no produce `NameError` por `Timestamp`.
2. El campo `start_time` llega correctamente en `JobInfo`.
3. Existe test unitario que falla sin el fix y pasa con el fix.

## Tareas técnicas
1. Añadir import `from google.protobuf.timestamp_pb2 import Timestamp`.
2. Ejecutar/crear test de `grpc_servicer` para `GetActiveJobs`.
3. Verificar lint y tipado del módulo.

## Riesgos
- Nulos o formatos inesperados en `start_time_seconds` provenientes del use case.
