# US-010 - Clarificar ownership de streams NATS (Task Derivation)

## Relacionada con
- `ASY-007` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Historia
Como equipo de plataforma,  
quiero que el servicio Task Derivation tenga un mecanismo claro para garantizar sus streams,  
para evitar dependencia implícita de inicialización por otros servicios/jobs.

## Alcance
- Definir política de ownership de streams por servicio.
- Implementar `ensure_streams` local o mecanismo común compartido.
- Documentar orden de arranque y responsabilidades.

## Criterios de aceptación
1. Task Derivation puede arrancar en entorno aislado sin fallar por stream ausente.
2. La responsabilidad de creación del stream `task_derivation` queda explícita en código/documentación.
3. Tests de arranque validan precondiciones de stream.

## Tareas técnicas
1. Diseñar estrategia de bootstrap de streams (común o por servicio).
2. Implementar verificación/creación idempotente de `task_derivation`.
3. Actualizar manifiestos K8s y documentación operativa.

## Riesgos
- Duplicación de lógica de inicialización si no se centraliza adecuadamente.
