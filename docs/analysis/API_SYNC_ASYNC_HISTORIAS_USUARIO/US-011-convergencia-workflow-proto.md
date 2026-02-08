# US-011 - Convergencia de `workflow.proto` duplicados

## Relacionada con
- `SYN-005` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Historia
Como mantenedor de contratos gRPC,  
quiero tener una única fuente de verdad para Workflow proto,  
para evitar deriva de contratos y generación de stubs inconsistentes.

## Alcance
- Elegir proto canónico (`specs/fleet/workflow/v1/workflow.proto` recomendado).
- Deprecar/eliminar `specs/workflow.proto` o redirigir generación a la fuente canónica.
- Actualizar scripts de generación.

## Criterios de aceptación
1. Existe una sola ruta canónica de proto de Workflow.
2. Scripts de generación usan únicamente esa ruta.
3. CI verifica ausencia de duplicidad divergente.

## Tareas técnicas
1. Revisar `scripts/generate-protos*.sh` y referencias de build.
2. Aplicar deprecación/eliminación del proto duplicado.
3. Añadir check en CI para detectar futuros duplicados divergentes.

## Riesgos
- Dependencias heredadas que aún importen el proto antiguo.
