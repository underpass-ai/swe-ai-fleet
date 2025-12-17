## RFC: Agent Executor (Go) — Reemplazo/Alternativa a Ray Executor

- **Status**: Draft
- **Owner**: TBD
- **Target**: nuevo microservicio `services/agent_executor` (Go)
- **Motivación**: reducir complejidad operativa (Ray/KubeRay) manteniendo ejecución paralela de agentes.
- **Arquitectura**: **Full DDD + Hexagonal** (ports & adapters, dominio puro).
- **API-first**: los contratos (gRPC + eventos) se definen primero en `specs/` y el código se implementa para cumplirlos (compatibilidad y versionado explícitos).

---

## 0) Principios (no negociables): Full DDD + API-first

### 0.1 Full DDD (y Hexagonal) como “nuevo elemento core”

`agent-executor` se concibe como un **bounded context** con:\n
- **Domain**: entidades/value objects/invariantes (sin dependencias de infra)\n
- **Application**: use cases (orquestación, sin detalles técnicos)\n
- **Ports**: interfaces explícitas hacia infra (NATS, vLLM HTTP, Redis/Valkey, K8s Job runner)\n
- **Adapters**: implementaciones tecnológicas (gRPC server, NATS publisher, Redis store, Kubernetes client, etc.)\n
\n
Invariante arquitectónica: **ningún detalle de infraestructura entra en Domain/Application**.

### 0.2 API-first (source of truth + disciplina de compatibilidad)

El sistema ya tiene contratos “API-first” y el `agent-executor` debe elevar ese estándar:\n
- **gRPC**: `specs/fleet/ray_executor/v1/ray_executor.proto` es source of truth para la API síncrona.\n
- **Eventos**: `specs/asyncapi.yaml` es source of truth para payloads `agent.response.*` y correlación.\n
\n
Reglas:\n
- Los cambios funcionales empiezan por **actualizar specs**, luego se implementa el servicio.\n
- No se commitea código generado (stubs). Se genera en build/CI.\n
- Breaking changes ⇒ versionado explícito (`v2`) y coexistencia durante migración.

---

## 1) Premisas verificadas en este repo

1) En el estado actual, **Ray no está aportando “GPU distribution” al job de agentes**: los agentes ejecutados en Ray terminan llamando a **vLLM vía HTTP**; la GPU está principalmente en el serving de vLLM.

2) El resto del sistema depende de Ray a través de una frontera estable:

- gRPC: `specs/fleet/ray_executor/v1/ray_executor.proto` (`RayExecutorService`)
- NATS: eventos `agent.response.*` consumidos por `orchestrator`, `task_derivation`, `planning`, `backlog_review_processor`.

Esto permite crear un **executor alternativo** sin reescribir `orchestrator`/`task_derivation`: basta con cambiar el endpoint.

---

## 2) Objetivo

Construir un **Agent Executor** que ejecute deliberaciones (fan-out por agente) en paralelo, **sin Ray**, manteniendo:

- **Compatibilidad de API**: implementar el mismo gRPC `RayExecutorService` (drop-in).
- **Compatibilidad de eventos**: publicar resultados en los mismos subjects y con payload compatible.
- **Operabilidad**: métricas/tracing/logs y resiliencia (retries, timeouts, deduplicación).
- **Requisitos de GPU por agente**: soportar escenarios donde un “agent run” requiera **2 GPUs** (o más) de forma explícita y verificable.

---

## 3) Stack elegido: Go

### Por qué Go (recomendación)

- **Excelente fit para servicios infra**: gRPC + HTTP + NATS, alta concurrencia, bajo overhead.
- **Binario único**: despliegue simple, menos superficie de dependencias que Python.
- **Observabilidad madura**: OpenTelemetry, métricas, profiling.
- **Alineación con la arquitectura declarada**: el overview del proyecto ya contempla Go en el Control Plane.

### Alternativas consideradas

- **Rust**: mayor seguridad de memoria y rendimiento, pero el coste de iteración y ecosistema gRPC/NATS/OTel suele ser mayor para un servicio “plumbing”.
- **Python**: menor coste inicial, pero la motivación principal aquí es precisamente reducir el “todo Python” y mejorar operabilidad/latencia/jitter.

---

## 4) Contrato de compatibilidad (Source of truth)

### 4.1 gRPC

Implementar **exactamente** `service RayExecutorService` de `specs/fleet/ray_executor/v1/ray_executor.proto`:

- `ExecuteDeliberation`
- `ExecuteBacklogReviewDeliberation`
- `GetDeliberationStatus`
- `GetStatus`
- `GetActiveJobs`

**Nota crítica**: `ExecuteDeliberationResponse.task_id` es REQUIRED para backlog review y hay validaciones explícitas en Python.

### 4.2 Eventos NATS

El executor debe seguir publicando resultados en los subjects que el resto consume (actualmente `agent.response.*`).

**Requisito de compatibilidad**: preservar campos usados downstream, especialmente `story_id` y el `task_id` original en metadata cuando aplique (p.ej. ceremonias de backlog review).

---

## 5) Modelo de ejecución propuesto

### 5.1 Diseño hexagonal (Go)

- **Domain**: entidades/VOs para Deliberation, AgentConfig, Constraints, Status.
- **Application**: use cases:
  - `ExecuteDeliberationUseCase` (fan-out y tracking)
  - `GetDeliberationStatusUseCase`
  - `GetActiveJobsUseCase`
  - `GetStatsUseCase`
- **Ports**:
  - `LLMClientPort` (vLLM/OpenAI-like)
  - `MessagingPort` (NATS JetStream)
  - `ClockPort`
  - `DeliberationStorePort` (in-memory + opcional persistencia)
- **Adapters**:
  - gRPC server (implementa proto)
  - NATS JetStream publisher
  - vLLM HTTP client
  - store (memoria; opcional Valkey/Redis para durability)

### 5.2 Scheduling y concurrencia

- El executor corre como **Deployment** sin GPU.
- Concurrencia controlada por:
  - worker pool / semaphore (max inflight requests a vLLM)
  - timeouts por request y deadline por deliberación

---

## 5.5 Requisito: “un agente puede ocupar 2 GPUs”

### 5.5.1 Disagree-first: por qué esto NO se cumple automáticamente

- Si el “agente” **solo hace HTTP a un vLLM compartido**, no existe una noción estándar de “reservar 2 GPUs por request”. vLLM decide batching/scheduling internamente.
- Con **GPU Operator + time-slicing**, el recurso `nvidia.com/gpu` puede representar **slices** (tiempo compartido) y no GPUs físicas. Pedir `2` puede significar “dos cuotas” del mismo dispositivo, no 2 GPUs dedicadas.

Conclusión: para que “2 GPUs por agente” sea real, el sistema debe asignar el agente a un **backend que esté configurado y aprovisionado** con 2 GPUs.

### 5.5.2 Cómo lo soportamos sin romper el proto v1

El proto v1 no tiene un campo explícito de recursos. Para compatibilidad:\n
- Usar `TaskConstraints.metadata` o `BacklogReviewTaskConstraints.metadata` con una clave estable, por ejemplo:\n
  - `metadata[\"gpu_count\"] = \"2\"`\n
  - `metadata[\"gpu_class\"] = \"tp2\"` (opcional, si se quiere enrutar por “perfil”) \n
\n
Esto permite que `agent-executor` aplique routing/policies sin cambiar clientes existentes. Si se quiere formalizar, se crea `ray_executor.v2` en el futuro con un `ResourceRequirements`.

### 5.5.3 Modelo recomendado: pool de vLLM por “GPU class” + routing

Operativamente, lo más realista (y rápido) es mantener **varios deployments de vLLM**:\n
- `vllm-tp1` (1 GPU)\n
- `vllm-tp2` (2 GPUs)\n
- `vllm-tp4` (4 GPUs)\n
\n
Cada deployment:\n
- solicita recursos K8s `nvidia.com/gpu: N`\n
- configura `VLLM_TENSOR_PARALLEL_SIZE=N` y `CUDA_VISIBLE_DEVICES` acorde\n
\n
El `agent-executor`:\n
- lee `gpu_count` desde metadata\n
- enruta el request al endpoint vLLM de esa clase\n
- limita concurrencia por clase para no saturar\n
\n
Esto es compatible con time-slicing, pero **si necesitas 2 GPUs físicas simultáneas**, debes:\n
- desactivar time-slicing para esos dispositivos/nodes o\n
- usar MIG con perfiles que garanticen aislamiento (dependiendo del hardware) o\n
- dedicar nodos/labels para “non-sliced GPU workloads”.

### 5.5.4 Alternativa (más cara): vLLM on-demand por deliberación

Para garantizar asignación rígida por job:\n
- `agent-executor` crea un Job/Pod vLLM con `nvidia.com/gpu: 2`, espera readiness, ejecuta, y destruye.\n
\n
Downside: cold start + load model (muy costoso) → solo viable si cache/weights/local NVMe y SLA lo permiten.

---

## 5.6 Requisito: “1 agente grande + muchos agentes pequeños” (exprimir vLLM en 4 GPUs)

### 5.6.1 Disagree-first: por qué Ray no lo cubre automáticamente aquí

Ray te cubre la asignación de recursos **solo** si el workload GPU corre “dentro” de Ray (p.ej., actors con `num_gpus` que ejecutan inference local).

En vuestro proyecto actual, los jobs Ray:\n
- corren Python CPU-side\n
- llaman por HTTP a un **vLLM externo** (deployment separado)\n
\n
Por eso, aunque Ray escalase actores, **no está “multiplexando” modelos ni GPUs**: esa decisión está en vLLM/K8s.

### 5.6.2 Modelo operativo recomendado (K8s-first)

Para mezclar un agente “grande” (necesita 2–4 GPUs) con muchos “pequeños” (1 GPU o slices), la estrategia más robusta es un **pool de backends vLLM**:\n
\n
- **Backend BIG**: 1 instancia vLLM con `tensor_parallel_size=4` (o 2) para el modelo grande.\n
- **Backend SMALL**: varias instancias vLLM con modelos pequeños, cada una fijada a 1 GPU (o slices), para maximizar throughput.\n
\n
El executor (Ray o Agent Executor Go) hace **routing**:\n
- lee `vllm_model` del request\n
- lee requisitos desde `constraints.metadata` (p.ej. `gpu_count`, `backend_tier=big|small`)\n
- selecciona el endpoint vLLM adecuado (BIG vs SMALL pool)\n
\n
Esto permite:\n
- reservar la capacidad del modelo grande sin que los pequeños lo ahoguen\n
- mantener latencias estables\n
- controlar prioridades (p.ej. backlog review vs ejecución crítica)\n

### 5.6.3 Implicaciones de GPU Operator + time-slicing

Con time-slicing puedes “colocar” múltiples instancias pequeñas en la misma GPU física, pero:\n
- compiten por memoria (VRAM) y ancho de banda\n
- puedes degradar p99 si el batching se descontrola\n
\n
Por eso el pool debe definirse por **perfil**:\n
- SMALL: util y batch limits conservadores\n
- BIG: util más alta, TP ajustado, y aislamiento (idealmente sin time-slicing si el modelo es muy grande)\n

### 5.6.4 Qué cambia en el RFC (y qué no)

- No cambiamos el proto v1.\n
- Formalizamos routing por `metadata` y por `vllm_model`.\n
- Añadimos la noción de “backend pools” como parte del diseño del executor.

---

## 5.7 Tool execution: ejecución de herramientas en contenedores (repo clone, tests, deploy e2e)

### 5.7.1 Principio (separación de planos)

- **vLLM**: sirve inferencia (GPU). No debe clonar repos ni ejecutar herramientas.
- **Tool execution**: se ejecuta en un **workspace container** aislado (CPU/mem/almacenamiento), con permisos y red controlados.

Esto permite “exprimir vLLM” (serving) sin mezclarlo con “SWE workloads” (git/test/build/deploy).

### 5.7.2 Modelo recomendado: K8s Jobs/Pods efímeros para tools

El `agent-executor` (o un subcomponente “workspace-runner”) crea un Job/Pod efímero por ejecución con:\n
- imagen de herramientas (git, python/go/node, make, etc.)\n
- volumen workspace efímero (`emptyDir`) o PVC si quieres cache\n
- límites estrictos (cpu/mem/ephemeral-storage)\n
- TTLSecondsAfterFinished y timeouts por step\n
- logs publicados a NATS (p.ej. `workspace.logs.{job_id}`)\n
\n
Si necesitas **deploy a Kubernetes** para un e2e:\n
- ejecutar en un **namespace de pruebas** dedicado\n
- usar un **ServiceAccount** específico con RBAC mínimo (solo ese namespace)\n
- aplicar NetworkPolicies (egress restringido)\n
\n
Esto es compatible con tu requisito: “el contenedor puede clonar repo, ejecutar tests, y desplegar a K8s para e2e”.

### 5.7.3 Implicación sobre request/payload

El proto gRPC v1 del executor no tiene un `workspace_spec` completo, así que para no romper compatibilidad:\n
- transportar specs mínimas en `constraints.metadata`, por ejemplo:\n
  - `metadata[\"workspace_mode\"] = \"k8s_job\"`\n
  - `metadata[\"repo\"] = \"owner/name\"`\n
  - `metadata[\"ref\"] = \"<branch|sha>\"`\n
  - `metadata[\"allowed_tools\"] = \"git,pytest,go-test,kubectl\"`\n
\n
A medio plazo, formalizar esto en **v2** (proto) para evitar “stringly-typed metadata”.

### 5.3 Deliberation ID y idempotencia

- Generar `deliberation_id` determinista u opaco (UUID) pero con:
  - **dedup** por `(task_id, agent_id)` si se reintenta la misma petición
- NATS publish con:
  - header `Nats-Msg-Id` (si se usa JetStream dedup)
  - `correlation_id` consistente

### 5.4 Resultados

- Publicar por agente a NATS:
  - `agent.response.completed` o `agent.response.failed`
- `GetDeliberationStatus`:
  - Si single-agent: devolver `DeliberationResult`
  - Si multi-agent: mantener compatibilidad actual (best result) o extender en v2 (no romper proto v1).

---

## 6) Plan de adopción (sin big bang)

### Phase 0 — Congelar contratos

- Freeze de `ray_executor.proto` durante la migración.
- Capturar “golden payloads” de NATS (completed/failed) usados por consumers.

### Phase 1 — Agent Executor (Go) skeleton

- Servidor gRPC que implementa endpoints y health.
- Publishers NATS y cliente vLLM (stub al inicio).

### Phase 2 — Ejecutar `ExecuteDeliberation` (read-only / happy path)

- Implementar fan-out a vLLM.
- Publicar resultados a NATS.

### Phase 3 — Paridad completa

- Implementar backlog review path (`ExecuteBacklogReviewDeliberation`) con validaciones.
- Implementar `GetDeliberationStatus`, `GetActiveJobs`, `GetStatus`.

### Phase 4 — Dual-run + canary

- El `orchestrator` y `task_derivation` apuntan por config a uno u otro (feature flag por `EXECUTOR_ADDRESS`).
- Canary progresivo (1% → 25% → 50% → 100%).

---

## 7) Observabilidad

- **Logs**: JSON, sin loggear prompts completos (riesgo de leakage).
- **Métricas**:
  - latencia por RPC
  - inflight a vLLM
  - error rate por código
  - publish success/fail en NATS
- **Tracing**: OpenTelemetry con propagación:
  - gRPC metadata → span
  - NATS headers → span

---

## 8) Seguridad

- **Secrets**: HF token/vLLM auth (si aplica) y NATS creds vía K8s Secrets.
- **Network**: NetworkPolicies; el executor solo necesita salida a vLLM y NATS.
- **PII/Repo data**: limitar logging (no prompts completos, no context dumps).

---

## 9) Criterios de aceptación (Definition of Done)

- [ ] Implementa `RayExecutorService` (proto v1) sin breaking changes.
- [ ] Publica `agent.response.*` con payload compatible para consumers existentes.
- [ ] Tests de contrato: gRPC request/response + NATS golden payloads.
- [ ] Soporta reintentos y dedup (idempotencia) sin duplicar side-effects.
- [ ] Canary + rollback probado.

---

## 10) Trade-offs: mantener Ray vs Agent Executor Go

### Mantener Ray

- **Pros**: primitives Ray (actors, scheduling intra-job, object store) si se usan.
- **Cons**: capa operativa extra; acoplamiento Python; más difícil si queremos Go/Rust.

### Agent Executor Go (propuesto)

- **Pros**: simplificación; mejor fit multi-lenguaje; control explícito de concurrencia hacia vLLM.
- **Cons**: pierdes primitives Ray; necesitas diseñar tracking/durability (store) y retries explícitos.

---

## 11) Preguntas abiertas (para cerrar antes de implementación)

- ¿El payload `agent.response.*` está formalmente especificado? Hay AsyncAPI (`specs/asyncapi.yaml`), pero existen consumidores legacy con expectativas distintas; hay que fijar un “mínimo común” y capturar golden payloads.
- ¿Necesitamos “tool execution” dentro del executor? (En esta conversación: **sí**, vía workspace containers / K8s Jobs; ver 5.7).
- ¿El tracking de `GetDeliberationStatus` debe sobrevivir reinicios/despliegues o puede ser best-effort en memoria? **Decidido: persistente con TTL** (ver 11.1).

### 11.1 Reformulación: “durability del tracking” (qué decisión necesitamos)

El proto gRPC expone `GetDeliberationStatus` y `GetActiveJobs`. La decisión es:\n
\n
**¿Queremos que el executor pueda responder el estado de una deliberación incluso si el pod se reinicia, se reprograma o hay 2 réplicas?**\n
\n
- **Best-effort (in-memory)**: el estado vive solo en memoria.\n
  - Pros: más simple.\n
  - Contras: si reinicia, puede devolver `not_found` aunque el job siga o haya terminado; dependes solo de eventos NATS.\n
\n
- **Durable (persistente con TTL)**: el estado se guarda en Valkey/Redis (o JetStream KV) con TTL.\n
  - Pros: polling fiable; puedes escalar réplicas; reinicios no rompen status.\n
  - Contras: más plumbing (store + limpieza + idempotencia).\n
\n
Decisión (aceptada): **Durable con TTL**.\n
\n
- Persistir estado en **Valkey/Redis** (preferido por simplicidad operativa en este repo) o JetStream KV.\n
- TTL recomendado: `timeout_seconds + margen` (ej. +10–30 min) para permitir inspección post-mortem.\n
- Actualización: “heartbeat” (touch) periódico mientras el job esté en `running`.\n
- Invariante: `GetDeliberationStatus` debe responder consistentemente aunque el pod se reinicie o haya múltiples réplicas.
