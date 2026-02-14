# Workspace Catalog Completion Plan (V6)

## 1) Objetivo

Completar el catálogo del `workspace` service para un runtime SWE serio, seguro y gobernable, cerrando gaps en:

- conectividad por `profiles`,
- colas y bases de datos con guardrails,
- supply chain/security,
- imagen + operaciones K8s sandboxed,
- artefactos/observabilidad como tools,
- herramientas de resumen/análisis para eficiencia del agente.

## 2) Principios no negociables

- Sin `exec` genérico.
- Todo tool tipado con `InputSchema` y `OutputSchema`.
- Policy server-side por metadata declarativa (no heurística).
- `read-only` por defecto; escrituras con aprobación/rol.
- Límites duros: timeout, max bytes, max messages/rows.
- Scope estricto: workspace, profile, namespace, subject/topic/key-prefix.

## 3) Estado actual vs gaps

| Dominio | Estado | Gap principal |
|---|---|---|
| FS/Git/Repo/Toolchains | Sólido | Mantener consistencia y cobertura e2e |
| Profiles de conectividad | Faltante | No existe capa `conn.*` |
| Colas (NATS/Kafka/Rabbit) | Faltante | Sin tools ni guardrails por subject/topic/queue |
| DBs (Redis/Mongo) | Faltante | Sin lectura/escritura gobernada |
| Security/Supply chain | Parcial | Falta SCA, SBOM, scan de contenedor |
| Image tools | Faltante | Falta `image.build/inspect/push` en catálogo actual |
| K8s runtime tools | Faltante | Falta `k8s.get_*` y `k8s.apply_manifest` sandboxed |
| Artifact tools | Parcial | Falta API uniforme `artifact.*` en catálogo |
| SWE summaries | Parcial | Falta `test_failures_summary`, `stacktrace_summary`, etc. |

## 4) Roadmap por fases

### Fase 0 (P0): Foundation de conectividad gobernada

**Tools**

- `conn.list_profiles`
- `conn.describe_profile`

**Cambios de policy/capability**

- `ProfileFields` declarativos por capability.
- Validación de profile allowlisted por tenant/rol.

**Criterio de salida**

- No existe tool de colas/DB sin `profile`.
- E2E de denegación por profile no permitido.

### Fase 1 (P0): Colas en modo lectura segura

**Tools**

- `nats.request`
- `nats.subscribe_pull` (o `nats.js.consumer_pull` si JetStream)
- `kafka.consume`
- `kafka.topic_metadata`
- `rabbit.consume`
- `rabbit.queue_info`

**Guardrails**

- Allowlist de subject/topic/queue.
- `max_messages`, `max_bytes`, `max_wait_ms`.
- Sin publish/produce por defecto.

**Criterio de salida**

- Lectura limitada y determinista en NATS/Kafka/Rabbit.
- Policy denies probado para subject/topic/queue fuera de scope.

### Fase 2 (P0): DB read-only y escrituras gobernadas mínimas

**Tools**

- `redis.get`, `redis.mget`, `redis.scan`, `redis.ttl`, `redis.exists`
- `mongo.find`, `mongo.aggregate` (con `limit` duro)

**Escrituras controladas**

- `redis.set` solo prefijos allowlisted + TTL obligatorio.
- `redis.del` solo prefijos allowlisted + approval explícito.

**Criterio de salida**

- Límite de cardinalidad y payload aplicado.
- Denegaciones por prefijo/approval cubiertas en e2e.

### Fase 3 (P1): Security y supply chain real

**Tools**

- `security.scan_dependencies`
- `sbom.generate`
- `security.scan_container`
- `security.license_check` (si aplica política legal)

**Criterio de salida**

- Salidas estructuradas con severidades.
- Integración con `ci.run_pipeline` como quality gates opcionales.

### Fase 4 (P1): Imagen/K8s/Artifacts

**Tools**

- `image.build`, `image.inspect`, `image.push` (opcional `image.sign`)
- `k8s.get_pods`, `k8s.get_logs`, `k8s.describe`, `k8s.apply_manifest`
- `artifact.upload`, `artifact.download`, `artifact.list`

**Guardrails K8s**

- Solo namespace sandbox por sesión/tenant.
- Deny cluster-scoped resources en `apply_manifest`.
- RBAC mínimo y validación de kinds permitidos.

**Criterio de salida**

- E2E de deploy sandbox completo sin permisos cluster-wide.

### Fase 5 (P1): Eficiencia cognitiva del agente

**Tools**

- `repo.test_failures_summary`
- `repo.stacktrace_summary`
- `repo.changed_files`
- `repo.symbol_search`
- `repo.find_references`
- `quality.gate`

**Criterio de salida**

- Menos tokens de contexto crudo en loops de reparación.
- Contrato estable para decisiones automáticas de aceptación/rechazo.

## 5) Backlog ejecutable (propuesto)

| ID | Prioridad | Entregable | Dependencia |
|---|---|---|---|
| CAT-001 | P0 | `conn.list_profiles` + `conn.describe_profile` | Ninguna |
| CAT-002 | P0 | Metadata policy: `ProfileFields`, `TopicFields`, `QueueFields`, `KeyPrefixFields` | CAT-001 |
| CAT-003 | P0 | NATS read tools + límites | CAT-002 |
| CAT-004 | P0 | Kafka read tools + límites | CAT-002 |
| CAT-005 | P0 | Rabbit read tools + límites | CAT-002 |
| CAT-006 | P0 | Redis read tools | CAT-002 |
| CAT-007 | P0 | Mongo read tools | CAT-002 |
| CAT-008 | P0 | Redis write gobernado (`set/del`) | CAT-006 |
| CAT-009 | P1 | `security.scan_dependencies` + `sbom.generate` | CAT-001 |
| CAT-010 | P1 | `security.scan_container` + `security.license_check` | CAT-009 |
| CAT-011 | P1 | `image.build/inspect/push` | CAT-001 |
| CAT-012 | P1 | `k8s.get_*` + `k8s.apply_manifest` sandbox | CAT-002 |
| CAT-013 | P1 | `artifact.upload/download/list` | CAT-001 |
| CAT-014 | P1 | `repo.test_failures_summary` + `repo.stacktrace_summary` | Ninguna |
| CAT-015 | P1 | `repo.changed_files` + symbol tools | CAT-014 |
| CAT-016 | P1 | `quality.gate` integrado en `ci.run_pipeline` | CAT-009, CAT-014 |

## 6) E2E plan mínimo para cerrar fases

| E2E ID propuesto | Objetivo |
|---|---|
| 21-workspace-profiles-governance | Allow/deny por profile y scopes declarativos |
| 22-workspace-queues-readonly | NATS/Kafka/Rabbit lectura con límites |
| 23-workspace-db-governed | Redis/Mongo read + write controlado con approval |
| 24-workspace-image-k8s-sandbox | Build de imagen + apply en namespace aislado |
| 25-workspace-security-quality-gate | SCA/SBOM/scan + `quality.gate` en pipeline |

## 7) Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Exposición accidental a prod | Profiles con scope estricto y deny-by-default |
| Saturación por consumos masivos | `max_messages`, `max_bytes`, `max_wait_ms` |
| Escrituras peligrosas en DB | Prefix allowlist + TTL + approval |
| `k8s.apply_manifest` escalable a cluster | Bloqueo de cluster-scoped + RBAC namespace-only |
| Falsos positivos de seguridad | Salida estructurada con severidad y whitelist auditable |

## 8) Definition of Done (catálogo “completo”)

- Todos los tools P0 implementados y disponibles en `DefaultCapabilities()`.
- Policy declarativa aplicada a todos los nuevos campos sensibles.
- E2E 21-23 en verde.
- Para P1: tools image/k8s/security/artifact + E2E 24-25 en verde.
- Evidencias versionadas en `e2e/evidence/` con resumen de cobertura por tool.
