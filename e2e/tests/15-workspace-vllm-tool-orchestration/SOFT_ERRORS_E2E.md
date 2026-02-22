# Test 15 - Soft Errors Contemplados (E2E)

## Contexto
El test `15-workspace-vllm-tool-orchestration` ejecuta cobertura amplia sobre el catálogo de tools.
En entornos gobernados y/o degradados hay fallos esperables que **no** deben romper el objetivo principal del test.

## Soft errors aceptados actualmente

1. `kafka.produce`, `rabbit.publish`, `nats.publish`, `redis.set`, `redis.del`
- Condición: perfil `read_only`.
- Contrato esperado:
  - `invocation_status=failed`
  - `error.code=policy_denied`
  - `error.message` contiene `read_only`
- Acción del test: registrar warning y continuar.

2. `nats.request`
- Condición: no hay responder activo para el subject.
- Contrato esperado:
  - `invocation_status=failed`
  - `error.code=execution_failed`
  - `error.message` contiene `no responders available`
- Acción del test: registrar warning y continuar.

3. `git.*` (modo degradado sin repo disponible)
- Condición: sesión sin repo Git utilizable (o pérdida de contexto de repo).
- Contrato esperado:
  - `invocation_status=failed`
  - `error.code` en `git_repo_error|execution_failed`
  - `error.message` contiene `not a git repository` (o equivalente)
- Acción del test: activar `git_repo_ready=False`, registrar warning y continuar.

## Soft errors NO aceptados

- Cualquier error que no cumpla contrato exacto (code + mensaje esperado) en los casos anteriores.
- Cualquier fallo de herramientas fuera de la lista de soft errors.

## Criterios de validación E2E (evidence)

En `EVIDENCE_JSON`:

1. Deben existir invocaciones fallidas para los casos esperados con su contrato correcto.
2. No debe existir `error_message` final por esos casos.
3. El estado final del test debe ser `passed`.

## Recomendación para hardening de test

Agregar aserciones explícitas por soft error en un step dedicado (ej. `soft_error_contracts`) para:
- evitar regresiones silenciosas,
- separar claramente fallos funcionales reales de denegaciones de policy esperadas.
