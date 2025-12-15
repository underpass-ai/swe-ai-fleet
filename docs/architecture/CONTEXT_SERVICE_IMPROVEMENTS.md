## Context Service — Improvement Plan (Rehydration + RBAC)

- **Status**: Draft
- **Scope**: `services/context` + `core/context`
- **Audience**: Architecture / Platform / Service owners
- **Goal**: Make Context Service production-grade under load while preserving Decision-Centric value.

---

### 1) Baseline (what already works well)

- **Decision-centric rehydration**: Neo4j (graph decisions/relationships) + Valkey/Redis (mutable planning state) is a strong foundation.
- **Prompt-level RBAC via scopes**: `config/prompt_scopes.yaml` + `core/context/domain/scopes/PromptScopePolicy` enforces Role+Phase+Scopes and adds redaction.
- **Focused context**: `_narrow_pack_to_subtask()` in `core/context/context_assembler.py` reduces noise and improves relevance.
- **Clear interfaces**: gRPC API (`specs/fleet/context/v1/context.proto`) and NATS consumers keep boundaries explicit.

---

### 2) Key risks observed (what can break MVP reliability)

### 2.1 Token budgeting is not grounded in the actual model

- In `services/context/server.py`, `token_count` is computed with `len(context_str.split())`, which is not a stable estimator of model tokens.
- Consequence: budget enforcement becomes unreliable (cost and latency spikes, truncation surprises, inconsistent prompt sizes).

### 2.2 RBAC "defense in depth" is conceptually present but needs enforcement gates

The repo describes **RBAC in 3 layers** (plus a prompt-level scope layer):

- **L1 (Infrastructure / query-level)**: constrain what the DB returns.
- **L2 (Domain rules)**: authorization policies as explicit rules.
- **L3 (Application orchestration)**: consistently apply checks/filters and audit.

Additionally:
- **Prompt-level scopes (Role+Phase+Scopes)** are a practical "last mile" to control what the LLM sees.

Risk: if any layer degrades silently (missing configs, permissive defaults), the system can leak more context than intended.

### 2.3 Rehydration hot path p99 can explode with graph growth

- Rehydration includes graph traversal + state fetch + assembly; without explicit caching/versioning and query controls, p99 will degrade as Stories and Decisions grow.

### 2.4 Security and audit posture is not yet "hard" enough

- Scopes config loader currently falls back to empty config when missing, which can effectively disable prompt controls in production.
- Logs across the system sometimes print LLM outputs; Context should avoid logging the full prompt/context.

---

### 3) Improvement backlog (prioritized)

### P0 — Must-have for a production MVP

- **P0.1 Replace token estimation with real tokenizer-based counting**
  - **What**: compute tokens using the same tokenizer as the target model(s) used via vLLM.
  - **Where**: move token counting and budget enforcement to `core/context` domain/application (not `services/context/server.py`).
  - **Acceptance**:
    - Token count error stays within an agreed tolerance (e.g., ±5–10% depending on model) or is exact if tokenizer is available.
    - Hard cap enforced consistently per Role+Phase.

- **P0.2 Make scope config fail-fast in production**
  - **What**: if `config/prompt_scopes.yaml` is missing/invalid, service should fail to start in production mode.
  - **Why**: prompt scopes are part of RBAC last-mile; silent fallback is unsafe.
  - **Acceptance**:
    - Explicit `CONTEXT_ALLOW_EMPTY_SCOPES_CONFIG=false` default in prod.
    - Unit tests for missing/invalid config path.

- **P0.3 Observability for rehydration and policy enforcement**
  - **Metrics**:
    - `context_getcontext_latency_ms` (p50/p95/p99)
    - `context_rehydration_latency_ms`
    - `context_token_count`
    - `context_scopes_missing_total`, `context_scopes_extra_total`
    - Neo4j/Redis call latency breakdown
  - **Tracing**: propagate correlation/trace id through gRPC + NATS.
  - **Acceptance**: dashboards allow identifying whether p99 is dominated by Neo4j, Redis, or assembly.

- **P0.4 Cache strategy + invalidation**
  - **What**: cache the assembled prompt blocks or the role packs keyed by:
    - `(story_id, role, phase, context_version)`
  - **Invalidate**:
    - on `planning.*` events and `context.events.updated`
  - **Acceptance**:
    - measurable cache hit ratio under typical load
    - p99 improvement for repeated calls

### P1 — Strongly recommended (stability + security)

- **P1.1 Harden RBAC layer boundaries with explicit tests and gates**
  - **What**:
    - Tests that a role cannot access disallowed entities (row-level).
    - Tests that sensitive fields are stripped (column-level).
    - Tests that prompt scopes never include forbidden blocks.
  - **Acceptance**: contract tests that attempt escalation paths and verify denial.

- **P1.2 Query controls and graph traversal limits**
  - **What**:
    - enforce max depth (already clamped in `GetGraphRelationships`; standardize across all graph traversals)
    - add timeouts and bounded result sets
  - **Acceptance**: worst-case stories do not exceed p99 or memory ceilings.

- **P1.3 Redaction improvements**
  - **What**: expand `PromptScopePolicy.redact()` patterns and ensure redaction applies to all outbound context.
  - **Acceptance**: test suite with known secret patterns, including connection strings and bearer tokens.

### P2 — Post-MVP (performance and evolvability)

- **P2.1 Deterministic context versioning (content addressable)**
  - **What**: make context version/hash derived from stable inputs (graph revision + plan version + scope config version).
  - **Why**: makes caching and debugging reproducible.

- **P2.2 Split read/write paths operationally**
  - **What**: separate gRPC deployment profiles for read-heavy (GetContext/RehydrateSession) vs write-heavy (UpdateContext/TransitionPhase).

- **P2.3 Rust migration alignment**
  - **What**: use `docs/architecture/CONTEXT_SERVICE_RUST_MIGRATION_PLAN.md` to plan a strangler migration.
  - **Gate**: parity tests for token budgeting and RBAC.

---

### 4) RBAC: the 3-level model (plus prompt scopes)

This is the recommended framing to keep security explicit and testable:

- **Level 1 (Infrastructure / Query-level)**
  - Goal: DB never returns data the caller should not see.
  - Mechanisms: authorization adapters / parameterized queries / filters.

- **Level 2 (Domain rules)**
  - Goal: centralized, explicit authorization rules; no hidden checks in adapters.
  - Mechanisms: `RoleVisibilityPolicy`-style rules and invariants.

- **Level 3 (Application orchestration + audit)**
  - Goal: enforce checks consistently, apply row/column filtering, and audit every access.
  - Mechanisms: application service that orchestrates policy + audit logging.

- **Prompt-level scopes (Role + Phase + Scopes)**
  - Goal: even if data exists, only expose allowed blocks to the LLM.
  - Source of truth: `config/prompt_scopes.yaml`.

---

### 5) Rehydration: performance and correctness gates

- **Correctness**:
  - Same input state + same scope config ⇒ same prompt blocks and version.
- **Performance**:
  - Budget p95/p99 and enforce bounded graph traversal.
- **Resilience**:
  - Neo4j/Redis timeouts must fail fast with clear error semantics.

---

### 6) Test plan (minimum)

- **Unit tests**:
  - Token budget enforcement (over budget, exact budget, near boundary)
  - Scope validation (missing/extra scopes)
  - Redaction patterns
- **Contract tests**:
  - gRPC `GetContext`/`ValidateScope` behavior and error codes
- **Load tests (MVP gate)**:
  - p95/p99 for repeated GetContext on representative large stories

