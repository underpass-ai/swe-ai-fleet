# US-003 - Resolver contrato huérfano de WorkspaceService

## Relacionada con
- `SYN-003` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Historia
Como equipo de plataforma,  
quiero que `WorkspaceService` esté implementado o formalmente deprecado,  
para evitar contratos proto sin endpoint real.

## Alcance
- Decidir implementar `ScoreWorkspace` o eliminar/deprecar contrato.
- Alinear proto, código y documentación.

## Criterios de aceptación
1. Existe implementación registrada del RPC o deprecación documentada y aplicada.
2. No quedan referencias ambiguas en código/documentación.
3. Pipeline de generación de stubs no produce artefactos huérfanos.

## Tareas técnicas
1. Revisar consumidores/clientes potenciales de `WorkspaceService`.
2. Ejecutar opción elegida (implementación o deprecación).
3. Añadir prueba mínima de disponibilidad/ausencia intencional.

## Riesgos
- Si se elimina contrato sin auditoría de dependencias, puede romper integraciones futuras.
