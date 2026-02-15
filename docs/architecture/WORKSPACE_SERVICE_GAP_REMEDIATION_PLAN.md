# Workspace Service Gap Remediation Plan (Feb 2026)

## 1. Objetivo

Cerrar los gaps funcionales y de seguridad del `workspace service` para soportar flujo SWE end-to-end: edición + git + validación + delivery + observabilidad + pruebas de performance, con gobernanza fuerte por policy.

## 2. Baseline validado en código

Resumen de lo que hoy existe y qué no:

- Git expuesto: `git.status`, `git.diff`, `git.apply_patch` solamente.
  - Evidencia: `services/workspace/internal/adapters/tools/catalog_defaults.go:503`, `services/workspace/internal/adapters/tools/catalog_defaults.go:522`, `services/workspace/internal/adapters/tools/catalog_defaults.go:544`
  - Evidencia handlers: `services/workspace/internal/adapters/tools/git_tools.go:14`
- FS expuesto: `fs.list`, `fs.read_file`, `fs.write_file`, `fs.patch`, `fs.search`.
  - Evidencia: `services/workspace/internal/adapters/tools/catalog_defaults.go:12`
- Mensajería actual:
  - NATS: `nats.request`, `nats.subscribe_pull`
  - Kafka: `kafka.consume`, `kafka.topic_metadata`
  - Rabbit: `rabbit.consume`, `rabbit.queue_info`
  - Evidencia: `services/workspace/internal/adapters/tools/catalog_defaults.go:160`, `services/workspace/internal/adapters/tools/catalog_defaults.go:206`, `services/workspace/internal/adapters/tools/catalog_defaults.go:252`
- K8s actual: solo lectura (`k8s.get_*`), sin apply/restart/rollout.
  - Evidencia: `services/workspace/internal/adapters/tools/catalog_defaults.go:1084`
- `api.benchmark` / k6 no existe.
  - Evidencia: búsqueda sin coincidencias en `services/workspace` para `api.benchmark` y `k6`.
- Profiles tienen `read_only`, pero `redis.set`/`redis.del` no lo validan.
  - Evidencia profile: `services/workspace/internal/adapters/tools/connection_tools.go:21`
  - Evidencia set/del: `services/workspace/internal/adapters/tools/redis_tools.go:555`, `services/workspace/internal/adapters/tools/redis_tools.go:671`
- Offset Kafka en runtime: solo `earliest|latest`.
  - Evidencia schema: `services/workspace/internal/adapters/tools/catalog_defaults.go:208`
  - Evidencia parser: `services/workspace/internal/adapters/tools/kafka_tools.go:465`
- Tools K8s se registran siempre aunque backend no sea kubernetes.
  - Evidencia backend init: `services/workspace/cmd/workspace/main.go:45`
  - Evidencia registro handlers K8s: `services/workspace/cmd/workspace/main.go:118`
  - Evidencia fallo por cliente nil: `services/workspace/internal/adapters/tools/k8s_tools.go:590`
- Runner image por defecto en K8s: `alpine:3.20`.
  - Evidencia: `services/workspace/internal/adapters/workspace/kubernetes_manager.go:24`

## 3. Gaps adicionales detectados (no menores)

- `NamespaceFields` y `RegistryFields` están en el modelo de capability pero no hay enforcement en `StaticPolicy`.
  - Evidencia metadata: `services/workspace/internal/domain/capability.go:85`
  - Evidencia authorize (no chequea namespace/registry): `services/workspace/internal/adapters/policy/static_policy.go:20`
  - Impacto: `k8s.*` e `image.push` no tienen allowlist server-side de namespace/registry aunque el catálogo lo declare.
- `ListTools` autoriza con `Approved: true`, lo cual es correcto para discovery, pero no filtra capacidades incompatibles con runtime.
  - Evidencia: `services/workspace/internal/app/service.go:97`

## 3.1 Hallazgos de calidad en E2E (review suite 14-33)

- Asserts de gobernanza demasiado laxos en tests de allowlist:
  - `e2e/tests/21-workspace-profiles-governance/test_workspace_profiles_governance.py:224`
  - `e2e/tests/22-workspace-queues-readonly/test_workspace_queues_readonly.py:206`
  - `e2e/tests/23-workspace-db-governed/test_workspace_db_governed.py:212`
  - Impacto: el test puede quedar en verde aunque la invocación falle por error runtime no relacionado a policy.
- Contradicción con contrato `read_only`:
  - el perfil `dev.redis` está definido como `ReadOnly: true` en `services/workspace/internal/adapters/tools/connection_tools.go:206`
  - pero E2E DB gobernada espera que `redis.set`/`redis.del` no estén bloqueados por policy en:
    - `e2e/tests/23-workspace-db-governed/test_workspace_db_governed.py:393`
    - `e2e/tests/23-workspace-db-governed/test_workspace_db_governed.py:401`
  - Impacto: al corregir enforcement hard de `read_only`, el E2E actual rompe por diseño.
- E2E de orquestación (15) tolera demasiados soft-fails sin umbral:
  - `e2e/tests/15-workspace-vllm-tool-orchestration/test_workspace_vllm_tool_orchestration.py:831`
  - `e2e/tests/15-workspace-vllm-tool-orchestration/test_workspace_vllm_tool_orchestration.py:864`
  - Impacto: regresiones múltiples en tools pueden pasar sin bloquear el pipeline.
- E2E de security/image permite fallback sintético en vez de ejecución real:
  - `e2e/tests/25-workspace-security-container-license/test_workspace_security_container_license.py:294`
  - `e2e/tests/27-workspace-image-build/test_workspace_image_build.py:300`
  - `e2e/tests/28-workspace-image-push/test_workspace_image_push.py:289`
  - Impacto: cobertura funcional parcial (no asegura disponibilidad real de scanner/builder/push).
- Cobertura E2E aún no valida los gaps P0/P1 nuevos:
  - Git lifecycle completo (`checkout/log/show/branch/commit/push/fetch/pull`)
  - FS ops reales (`mkdir/move/copy/delete/stat`)
  - produce/publish en colas
  - k8s delivery (`apply/rollout/restart`)
  - `api.benchmark` (k6)

## 3.2 Hallazgos de ejecución real E2E (2026-02-15, run desde 14)

Resultado consolidado:

- `14`: PASS
- `15`: PASS (tras ampliar mapping de tools nuevas en el test y corregir falso negativo del runner)
- `16`: PASS
- `17`: PASS
- `18`: PASS
- `19`: PASS
- `20`: PASS
- `21`: PASS
- `22`: PASS
- `23`: FAIL real
- `24`: PASS
- `25`: PASS
- `26`: PASS
- `27`: PASS
- `28`: PASS
- `29`: PASS
- `30`: PASS
- `31`: PASS
- `32`: PASS
- `33`: PASS

Hallazgo crítico (histórico, mitigado y validado):

- `23-workspace-db-governed` presentaba fallo por resolución DNS del endpoint Mongo:
  - error: `lookup mongodb.swe-ai-fleet.svc.cluster.local on 10.96.0.10:53: no such host`
  - evidencia en invocación `mongo.find` (`execution_failed`) en logs E2E 23.
  - impacto: invalida la verificación allowlist positiva para Mongo en el test gobernado.
  - estado (2026-02-15): mitigado en código E2E mediante endpoints explícitos y stack efímero dedicado, y validado con rerun dirigido de `21/22/23` (jobs en `Complete`).

Hallazgos de runner E2E observados durante la ejecución:

- El matcher de fallo en logs (`Test.*failed`) producía falsos negativos en tests con líneas como `node.test status=failed`.
- El loop del runner no incluía `30-33` aunque existían en `TEST_CONFIGS`.
- Reaplicar un Job fallido con `kubectl apply` reutiliza estado/logs viejos (`configured`) y provoca resultados stale.

## 3.3 Infra efímera para tests de persistencia y colas (implementado)

Se implementó un stack efímero de dependencias para pruebas E2E de persistencia/colas, con ciclo `up/down/status` y teardown al final del runner.

- Recursos incluidos en namespace `swe-ai-fleet`:
  - MongoDB, Postgres, NATS, RabbitMQ, Kafka + jobs de bootstrap/seed.
  - Evidencia: `e2e/auxiliary/ephemeral-deps.yaml`
- Script operativo:
  - `up`, `down`, `status`, waits de rollout y jobs.
  - Evidencia: `e2e/auxiliary/ephemeral-deps.sh`
- Integración con runner:
  - provisioning automático para tests `21|22|23`
  - teardown automático al finalizar ejecución.
  - Evidencia: `e2e/run-e2e-tests.sh:208`, `e2e/run-e2e-tests.sh:221`, `e2e/run-e2e-tests.sh:242`, `e2e/run-e2e-tests.sh:854`, `e2e/run-e2e-tests.sh:1082`
- Endpoints E2E gobernados ahora son configurables por env y apuntan al stack efímero por defecto:
  - Evidencia: `e2e/tests/21-workspace-profiles-governance/test_workspace_profiles_governance.py`
  - Evidencia: `e2e/tests/22-workspace-queues-readonly/test_workspace_queues_readonly.py`
  - Evidencia: `e2e/tests/23-workspace-db-governed/test_workspace_db_governed.py`
  - Evidencia jobs: `e2e/tests/21-workspace-profiles-governance/job.yaml`, `e2e/tests/22-workspace-queues-readonly/job.yaml`, `e2e/tests/23-workspace-db-governed/job.yaml`
- Fix de fiabilidad aplicado:
  - bootstrap Kafka usaba `kafka-topics.sh` (no disponible en imagen `cp-kafka`), cambiado a `kafka-topics`.
  - Evidencia: `e2e/auxiliary/ephemeral-deps.yaml:326`

## 4. Plan de ejecución priorizado

## 4.1 P0 (bloqueantes)

### WS-GAP-001: Git lifecycle completo

Agregar tools:

- `git.checkout`
- `git.log`
- `git.show`
- `git.branch_list`
- `git.commit` (approval obligatorio)
- `git.push` (approval + allowlist remotes)
- `git.fetch` (approval + allowlist remotes)
- `git.pull` (approval + allowlist remotes)

Cambios:

- `services/workspace/internal/adapters/tools/git_tools.go`: nuevos handlers.
- `services/workspace/internal/adapters/tools/catalog_defaults.go`: capacidades, schemas, risk/approval.
- `services/workspace/cmd/workspace/main.go`: registrar handlers.
- `services/workspace/internal/adapters/policy/static_policy.go`: allowlist de remotes/refs (nuevos metadata keys).

Nuevos metadata keys (sesión):

- `allowed_git_remotes` (ej: `origin,upstream`)
- `allowed_git_ref_prefixes` (ej: `refs/heads/,refs/tags/release-`)

DoD:

- Se puede cambiar rama, inspeccionar historial, comitear y push/fetch/pull bajo policy.
- `git.push/fetch/pull` deniegan remoto fuera de allowlist.
- Tests unitarios y de integración verdes.

---

### WS-GAP-002: FS de workspace real

Agregar tools:

- `fs.mkdir`
- `fs.move`
- `fs.copy`
- `fs.delete` (approval obligatorio)
- `fs.stat`
- opcional V1.1: `fs.tree` (puede resolverse por `fs.list recursive=true`)

Cambios:

- `services/workspace/internal/adapters/tools/fs_tools.go`: local + runtime kubernetes.
- `services/workspace/internal/adapters/tools/catalog_defaults.go`: capabilities/schemas/policy path fields.
- `services/workspace/cmd/workspace/main.go`: registrar handlers.

Guardrails:

- Paths siempre por `resolvePath`.
- `fs.delete` con `RiskMedium/High` + `RequiresApproval=true`.
- Límite de cantidad en operaciones multi-archivo.

DoD:

- Operaciones soportadas en runtime local y kubernetes.
- No hay path traversal.
- Tests de policy y handlers con casos deny.

---

### WS-GAP-003: Enforce hard de `read_only` en profiles

Problema actual:

- `read_only=true` se devuelve en perfil pero no bloquea writes en redis.

Cambios:

- `services/workspace/internal/adapters/tools/redis_tools.go`: bloquear `redis.set` y `redis.del` cuando `profile.ReadOnly`.
- Reutilizar el mismo guard en futuros write tools (`nats.publish`, `kafka.produce`, `rabbit.publish`).
- Mensaje de error recomendado: `policy_denied` con razón `profile is read_only`.

DoD:

- No existe write permitido sobre profile read-only aunque el caller ponga `approved=true`.
- Tests nuevos en `services/workspace/internal/adapters/tools/redis_tools_test.go`.

---

### WS-GAP-004: Mensajería con operaciones de escritura

Agregar tools:

- `nats.publish`
- `kafka.produce`
- `rabbit.publish`

Cambios:

- Nuevos handlers en `services/workspace/internal/adapters/tools/`.
- Capacidades en `catalog_defaults.go` con `RequiresApproval=true` en V1.
- Registro en `main.go`.

Guardrails:

- Siempre `profile_id`.
- `subject/topic/queue` allowlist por policy + profile scopes.
- `max_bytes`, `timeout_ms`.
- Enforce `read_only` profile.

DoD:

- Se pueden inyectar eventos controlados para reproducir incidentes.
- Denegación correcta por scope y por `read_only`.

---

### WS-GAP-005: Runtime-aware catalog para K8s tools

Problema actual:

- En backend local, `k8s.*` puede aparecer (roles cluster) y fallar al invocar por `kubernetes client is not configured`.

Cambios recomendados (hacer ambos):

1. Filtro en `ListTools` según runtime:
   - si `session.Runtime.Kind != kubernetes`, excluir `ScopeCluster` o al menos `k8s.*`.
2. Guard en `InvokeTool` pre-ejecución para error de policy más claro (`policy_denied`) en vez de fallo de ejecución.

Archivos:

- `services/workspace/internal/app/service.go`
- opcionalmente `services/workspace/internal/adapters/policy/static_policy.go`

DoD:

- En backend local, `k8s.*` no se lista.
- Invocación directa de `k8s.*` fuera de runtime kubernetes devuelve deny consistente.

Estado (2026-02-15):

- Implementado en `services/workspace/internal/app/service.go`:
  - filtro runtime-aware en `ListTools` para capacidades `ScopeCluster`.
  - guard pre-policy en `InvokeTool` que devuelve `policy_denied` con mensaje explícito de runtime.
- Validado con tests unitarios en `services/workspace/internal/app/service_unit_test.go`:
  - ocultamiento de tools cluster en runtime no-kubernetes.
  - deny consistente en invocación directa de tool cluster fuera de runtime kubernetes.

---

### WS-GAP-006: Policy enforcement de `NamespaceFields` y `RegistryFields`

Problema actual:

- El modelo lo declara, la policy no lo evalúa.

Cambios:

- `services/workspace/internal/adapters/policy/static_policy.go`
  - agregar `argsAllowedByNamespacePolicy(...)`
  - agregar `argsAllowedByRegistryPolicy(...)`
  - metadata keys sugeridos:
    - `allowed_k8s_namespaces`
    - `allowed_image_registries`

DoD:

- `k8s.*` deniega namespace fuera de allowlist.
- `image.push` deniega registry fuera de allowlist.
- Tests nuevos en `services/workspace/internal/adapters/policy/static_policy_extra_test.go`.

Estado (2026-02-15):

- Implementado en `services/workspace/internal/adapters/policy/static_policy.go`:
  - enforcement de `NamespaceFields` via `allowed_k8s_namespaces`.
  - enforcement de `RegistryFields` via `allowed_image_registries` (incluye extracción de registry desde `image_ref`).
- Validado por unit tests en `services/workspace/internal/adapters/policy/static_policy_extra_test.go`.
- Validado en E2E:
  - `28-workspace-image-push`: deny `policy_denied` para registry fuera de allowlist + caso allow dentro de allowlist.
  - `29-workspace-k8s-read-minimal`: deny `policy_denied` para namespace fuera de allowlist + casos read permitidos en namespace autorizado.

---

### WS-GAP-007: Offset Kafka consistente con schema/expectativa

Problema actual:

- input sugiere control de offset, pero runtime solo soporta `earliest|latest`.

Cambios V1:

- Cambiar contrato de entrada de `kafka.consume` a:
  - `offset_mode: earliest|latest|absolute|timestamp`
  - `offset` (int64) cuando `absolute`
  - `timestamp_ms` cuando `timestamp`
- Actualizar implementación de lectura para cada modo.

Archivos:

- `services/workspace/internal/adapters/tools/catalog_defaults.go`
- `services/workspace/internal/adapters/tools/kafka_tools.go`

DoD:

- Se puede reconsumir desde offset exacto y desde timestamp.
- Tests unitarios con cada modo.

---

### WS-GAP-019: Salud de endpoints de connection profiles en entorno E2E

Problema actual:

- `23-workspace-db-governed` falla por DNS de Mongo (`mongodb.swe-ai-fleet.svc.cluster.local` no resuelve).
- En `22-workspace-queues-readonly` aparecen también fallos DNS de `kafka`/`rabbitmq` (no bloqueantes para ese test, pero indican drift de entorno/perfiles).

Cambios:

- Alinear `connection_profile_endpoints_json` y/o perfiles por defecto con los Services reales desplegados en namespace.
- Agregar preflight opcional en E2E para verificar resolvibilidad de endpoints críticos antes de asserts funcionales.
- Agregar validación de endpoint en bootstrap de sesión de tests gobernados (fail fast con mensaje de infraestructura).

DoD:

- E2E 23 valida camino allowlist de Mongo sin fallos de DNS.
- Drift de endpoints se detecta al inicio con error explícito de infraestructura, no como falso fallo de policy.

Estado (2026-02-15):

- Mitigación principal implementada con stack efímero y endpoints E2E explícitos.
- Cierre validado: rerun dirigido de E2E `21/22/23` con evidencia `PASS` (jobs `Complete` en Kubernetes).

---

### WS-GAP-008: `api.benchmark` (k6) V1

Implementar tool nuevo:

- `api.benchmark`

Input V1:

- `profile_id` (obligatorio)
- `request.method`, `request.path`, `request.headers`, `request.body`
- `mode: constant_vus|arrival_rate` (default `constant_vus`)
- `load.duration_ms`, `load.vus`, `load.rps`
- `thresholds` opcional (`p95_ms`, `error_rate`, `checks_rate`)

Output V1:

- `latency_ms`: `min/avg/p50/p95/p99/max`
- `rps_observed`
- `requests`, `failed_requests`, `error_rate`
- `thresholds.passed`, `thresholds.violations[]`
- `artifacts`: refs a `summary.json`, `k6.js`, `k6.stdout.log`

Guardrails obligatorios:

- target resuelto solo por `profile_id`
- validación de `request.path` por allowlist del profile
- límites duros:
  - `duration_ms <= 60000`
  - `vus <= 50`
  - `rps <= 200`
  - body <= 32KB
  - header bytes acotados + denylist (`Authorization`, `Cookie`, `Set-Cookie`)
- redacción de secretos en logs/artifacts

Implementación:

- nuevo handler en `services/workspace/internal/adapters/tools/benchmark_tools.go`
- capability en `catalog_defaults.go`
- alta en `main.go`
- ejecución:
  - generar `/workspace/.bench/k6.js`
  - correr `k6 run --summary-export=/workspace/.bench/summary.json ...`
  - parsear summary
  - adjuntar artifacts

Dependencia de runtime:

- runner image debe incluir `k6`.

DoD:

- Happy-path benchmark retorna métricas estructuradas.
- deny por path no allowlisted.
- deny por límites excedidos.

## 4.2 P1 (operación controlada)

### WS-GAP-009: K8s delivery tools

Agregar:

- `k8s.apply_manifest` (approval + allowlist namespace + kinds permitidos)
- `k8s.rollout_status`
- `k8s.restart_deployment` (approval)

No incluir en V1:

- `k8s.exec` (alto riesgo)
- `k8s.port_forward` (riesgo alto de egress lateral)

DoD:

- Deploy/restart con policy estricta y audit.
- Deny cluster-scoped resources.

---

### WS-GAP-010: Container runtime ops

Agregar:

- `container.ps`
- `container.logs`
- `container.run` (approval)
- `container.exec` (approval)

Guardrails:

- runtime allowlist (`buildah/podman/docker/nerdctl`) configurable.
- comandos permitidos en `exec` con allowlist.

## 4.3 P2 (escalabilidad y robustez)

### WS-GAP-011: Runner images por bundle de toolchain

Acciones:

- definir imágenes por perfil de repo (`go/node/python/rust/secops`)
- selección automática via `repo.detect_toolchain`
- fallback a imagen “fat” para PoC

Archivos objetivo:

- `services/workspace/internal/adapters/workspace/kubernetes_manager.go`
- configuración de despliegue Helm/manifests

---

### WS-GAP-012: Invariantes operativas

- rate limit por sesión/principal en `InvokeTool`
- cuota por output/artifacts por invocación
- redacción en audit logger y outputs sensibles

Archivos:

- `services/workspace/internal/app/service.go`
- `services/workspace/internal/adapters/audit/logger_audit.go`
- helpers de redaction en `internal/adapters/tools`

---

### WS-GAP-013: Actualización de documentación operativa

- `services/workspace/README.md` hoy no refleja catálogo real.
- actualizar tabla completa de tools + approvals + risk + policy metadata.

---

## 4.4 P0.5 (fiabilidad de la suite E2E existente)

### WS-GAP-014: Endurecer aserciones de gobernanza en E2E 21/22/23

Cambios:

- Reemplazar validaciones tipo `not policy_denied` por contrato explícito:
  - `invocation.status == succeeded` cuando el caso es allowlist positivo
  - `error.code` exacto para casos de deny/approval
- Mantener trazabilidad de `http_status` + `invocation.status` + `error.code`.

DoD:

- Un fallo runtime no-policy en casos allowlist hace fallar E2E.
- Reducción de falsos positivos en governance suite.

---

### WS-GAP-015: Alinear E2E DB gobernada con `read_only` hard

Cambios:

- Actualizar `23-workspace-db-governed` para que:
  - `dev.redis` (read-only) espere denegación en `redis.set`/`redis.del`
  - los casos de write exitoso usen perfil writable explícito de test (ej: `dev.redis_rw`) o fixture equivalente.

DoD:

- E2E valida el contrato final: `approval` no sobreescribe `read_only`.
- No hay contradicción entre plan WS-GAP-003 y assertions E2E.

---

### WS-GAP-016: Modo estricto no sintético en E2E 25/27/28

Cambios:

- Agregar flag de test (ej: `STRICT_RUNTIME=true`) para exigir ejecución real:
  - `security.scan_container`: scanner real (sin `heuristic-*`)
  - `image.build`: sin builder `synthetic`
  - `image.push`: sin `simulated=true`
- Mantener modo permissive para dev local, pero CI principal debe correr en modo estricto.

DoD:

- Pipeline principal falla si falta runtime real de scanner/builder/push.
- Se conserva camino de ejecución rápida para entornos de desarrollo.

---

### WS-GAP-017: Expansión de cobertura E2E para nuevos gaps P0/P1

Cambios:

- Agregar nuevos E2E dedicados para Git lifecycle, FS ops reales, messaging produce, Kafka replay, benchmark k6 y K8s runtime gating.

DoD:

- Cada gap funcional P0/P1 tiene al menos un E2E de contrato.
- Evidencia E2E enlazada en PR de cada capability.

---

### WS-GAP-018: Fiabilidad del runner E2E secuencial

Cambios:

- Endurecer detección de fallo por logs (evitar patrones genéricos que capturen `*.test status=failed`).
- Ejecutar suite completa `14-33` en loop principal (incluir `30-33` en run/rebuild).
- Forzar ejecución fresca por test: `delete job --ignore-not-found` antes de deploy.

DoD:

- El runner no marca fail por falsos positivos de logs de tools.
- `run-e2e-tests.sh` ejecuta `30-33` sin intervención manual.
- No hay reuse de estado/logs antiguos por jobs `configured` sobre fallos previos.

## 5. Orden sugerido de implementación (sprints)

Sprint A (P0 seguridad + consistencia):

1. WS-GAP-014 (hardening assertions governance E2E)
2. WS-GAP-018 (fiabilidad runner E2E)
3. WS-GAP-003 (`read_only` hard enforcement)
4. WS-GAP-015 (alineación E2E con `read_only`)
5. WS-GAP-019 (salud endpoints profiles en E2E)
6. WS-GAP-005 (runtime-aware K8s listing/invoke)
7. WS-GAP-006 (namespace/registry policy enforcement)
8. WS-GAP-007 (Kafka offset contract)

Sprint B (P0 funcionalidad core):

1. WS-GAP-001 (Git lifecycle)
2. WS-GAP-002 (FS real ops)
3. WS-GAP-004 (publish/produce en colas)
4. WS-GAP-017 (E2E nuevos de contrato para capacidades P0)

Sprint C (P0 performance):

1. WS-GAP-008 (`api.benchmark` k6)
2. e2e dedicados de límites/policy/artifacts
3. WS-GAP-016 (activar modo estricto no sintético en CI)

Sprint D (P1):

1. WS-GAP-009 (K8s delivery controlado)
2. WS-GAP-010 (container runtime ops)

## 6. Matriz de pruebas mínima requerida

Unit tests:

- `git_tools_test.go`: checkout/log/show/branch/commit/push/fetch/pull.
- `fs_tools_test.go`: delete/move/copy/mkdir/stat (+traversal deny).
- `redis_tools_test.go`: deny write cuando `profile.ReadOnly`.
- `kafka_tools_test.go`: offset modes.
- `static_policy_test.go` + `static_policy_extra_test.go`: namespace/registry allowlist.
- `benchmark_tools_test.go`: parser summary k6 + constraints + redaction.

Integration tests:

- `service_integration_test.go`: listing runtime-aware y approval flow.
- invocaciones con correlation-id para side effects (replay safe).

E2E nuevos sugeridos:

- `34-workspace-git-lifecycle`
- `35-workspace-fs-ops`
- `36-workspace-messaging-produce`
- `37-workspace-kafka-offset-replay`
- `38-workspace-api-benchmark-k6`
- `39-workspace-k8s-runtime-gating`
- `40-workspace-governance-strict-assertions`

## 7. Criterios de cierre global

- Catálogo soporta ciclo SWE completo sin salir del workspace service.
- Toda operación write de external/cluster está gobernada por `approval + allowlist + read_only`.
- No se listan tools incompatibles con runtime actual.
- `api.benchmark` entrega métricas estructuradas y artifacts reproducibles.
- Cobertura de tests actualizada y e2e críticos en verde.
