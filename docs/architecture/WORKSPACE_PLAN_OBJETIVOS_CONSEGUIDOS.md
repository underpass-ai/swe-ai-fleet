# Workspace v7 - Resumen de Objetivos Conseguidos

Fecha de corte: 2026-02-21

## Objetivos conseguidos (plan de produccion)

1. Cierre de riesgo critico en connection profiles (P0):
- El endpoint de perfiles dejo de depender de metadata de sesion para override arbitrario.
- Resolucion de endpoints queda server-side via `WORKSPACE_CONN_PROFILE_ENDPOINTS_JSON`.

2. Endurecimiento de `container.exec` (P0):
- Se eliminaron rutas de bypass por shell interactivo en la allowlist.
- Se reforzo el uso de modo estricto en entorno de produccion.

3. Endurecimiento de red de salida (P0):
- `workspace-networkpolicy.yaml` paso de egress abierto a allowlist explicita.
- Se incluyeron excepciones controladas para DNS, dependencias internas y API de Kubernetes.

4. Split RBAC runtime vs delivery (P1):
- Separacion operativa entre permisos de sesion/runtime y permisos de entrega K8s.
- Permisos de delivery documentados y acotados a escenarios sandbox/dev.

5. Escalado y hardening de despliegue (P1):
- HPA del servicio workspace aplicado.
- Persistencia de sesiones/invocaciones sobre Valkey para replicas > 1.

6. Cuotas operativas por sesion (P2):
- Se agrego rate limiting por ventana y limite de concurrencia por sesion:
  - `WORKSPACE_RATE_LIMIT_PER_MINUTE`
  - `WORKSPACE_MAX_CONCURRENCY_PER_SESSION`

7. Imagenes base deterministicas:
- Dockerfiles normalizados a `FROM` fully-qualified para evitar resolucion interactiva y mejorar reproducibilidad.

8. Runner images por bundle (operacion):
- Seleccion de runner por perfil allowlistado server-side:
  - `WORKSPACE_K8S_RUNNER_IMAGE_BUNDLES_JSON`
  - `WORKSPACE_K8S_RUNNER_PROFILE_METADATA_KEY`
- `runner_profile` desconocido ahora falla en creacion de sesion (no hay override arbitrario de imagen).

9. AuthN/AuthZ de produccion para API workspace:
- Nuevo modo `trusted_headers` con token compartido:
  - `WORKSPACE_AUTH_MODE=trusted_headers`
  - `WORKSPACE_AUTH_SHARED_TOKEN`
- En `trusted_headers`, `principal` del body se ignora en `POST /v1/sessions`.
- Enforzamiento de ownership para sesiones e invocaciones por `tenant_id + actor_id`.

10. Documentacion operativa actualizada:
- Runbook de produccion con pasos de hardening (network policy, RBAC split, auth mode).
- README de workspace y manifests con variables de entorno nuevas.

11. Observabilidad de metricas en produccion:
- Endpoint `/metrics` expuesto y validado en cluster.
- `workspace-servicemonitor.yaml` aplicado para scraping por `kube-prometheus-stack`.
- Reglas de alerta operativas en `workspace-prometheusrule.yaml`:
  - `WorkspaceDown`
  - `WorkspaceInvocationFailureRateHigh`
  - `WorkspaceInvocationDeniedRateHigh`
  - `WorkspaceP95InvocationLatencyHigh`

12. Observabilidad de logs en produccion:
- `promtail.yaml` desplegado como DaemonSet en `swe-ai-fleet`.
- Envio de logs a Loki validado.
- Ajuste de cardinalidad para evitar `429 Maximum active stream limit exceeded`.

13. Cuotas activadas en despliegue productivo:
- Se dejaron valores por defecto en manifiesto de `workspace`:
  - `WORKSPACE_RATE_LIMIT_PER_MINUTE=300`
  - `WORKSPACE_MAX_CONCURRENCY_PER_SESSION=16`

## Validaciones realizadas

1. Tests unitarios Go:
- `services/workspace/internal/httpapi`
- `services/workspace/internal/app`
- `services/workspace/cmd/workspace`

2. Validaciones E2E en cluster:
- Suite completa `01..41`: passed (0 failed)

3. Validacion funcional de auth (`trusted_headers`) en cluster:
- Sin token: `401 unauthorized`.
- Con token + headers: sesion creada con principal autenticado.
- Actor distinto sobre sesion ajena: `403 policy_denied`.

4. Validacion operativa en cluster (observabilidad y rollout):
- `workspace` en `Running` con imagen `v0.1.0-20260221-133119`.
- `/healthz` y `/metrics` respondiendo desde la Service.
- `promtail` DaemonSet `READY 1/1`.
- `PrometheusRule/workspace` creada y validada por operator (`prometheus-operator-validated=true`).

## Commits relevantes

- `f52bf87b` workspace: harden endpoints/runtime and split delivery RBAC
- `bdd6d62f` deploy: add workspace HPA and egress hardening manifests
- `2e1acfd6` workspace: add per-session rate and concurrency quotas
- `f406c5a2` deploy: tighten workspace egress allowlist for production
- `8bf3eceb` deploy: harden workspace RBAC split for delivery tools
- `0f4eb2f5` build: fully qualify docker base images across dockerfiles
- `ebfe093a` workspace: add allowlisted k8s runner image bundles
- `4bc26216` deploy: bump workspace image to v0.1.0-20260220-203234
- `7c5fc77d` workspace: enforce trusted-header auth and principal ownership
- `34c30720` workspace: disable synthetic container fallback in production
- `7a5ae45a` workspace: auto-generate capability catalog docs from defaults
- `8d42cb67` workspace: expose invocation metrics for prometheus
- `0d573783` workspace: add opentelemetry tracing for tool invocations
- `52c8dfe4` workspace: enforce connection profile endpoint host allowlists
- `084808d2` deploy: add workspace servicemonitor and prom-loki runbook
- `dfae0d98` deploy: add promtail log collector for loki
- `714943f1` deploy: add workspace prometheus alert rules
- `55ce9c6d` deploy: set workspace session quotas in prod manifest
