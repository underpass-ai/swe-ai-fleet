# US-009 - Endurecer apagado de consumidores (CancelledError)

## Relacionada con
- `ASY-006` en `docs/analysis/API_SYNC_ASYNC_AUDIT_2026-02-08.md`

## Historia
Como operador de la plataforma,  
quiero que el apagado de servicios complete cleanup de forma determinista,  
para evitar conexiones abiertas y cierres incompletos.

## Alcance
- Normalizar contrato de `stop()` en consumidores para no romper cleanup global.
- Asegurar que los servidores capturan y manejan cancelaciones esperadas.

## Criterios de aceptación
1. Al detener servicios, no se interrumpe el cleanup por `CancelledError` esperado.
2. Cierre de NATS/adapters/storage se ejecuta siempre.
3. Tests de shutdown cubren al menos `planning`, `backlog_review_processor` y `task_derivation`.

## Tareas técnicas
1. Definir guideline: `stop()` no debe re-lanzar cancelación operativa esperada.
2. Ajustar consumidores afectados.
3. Ajustar bloques `finally`/shutdown de servidores.
4. Añadir pruebas de regresión de apagado.

## Riesgos
- Enmascarar cancelaciones no esperadas si se captura de forma demasiado amplia.
