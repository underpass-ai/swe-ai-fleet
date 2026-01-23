## E0 Ceremony Engine — Detailed Analysis (Text)

### 1) Scope and method
This document consolidates the analysis of E0 (ceremony engine) and its cohesion
with the rest of the application. The review covers:
- Domain, application, and infrastructure layers for `core/ceremony_engine`
- DSL YAML validation and mapping
- Step handlers and runner behavior
- E2E readiness and alignment with existing E2E conventions
- Unit test coverage expectations (>=85%)

Limitations:
- The review is based on repository inspection plus local unit test execution.
- No live infrastructure validation was performed (no NATS/Neo4j/Valkey runtime).
- Git history analysis is based on `git.log` extracted in this workspace; it is
  not a live `git log` query against a remote.

Evidence updates (new):
- Unit tests for `core/ceremony_engine` executed via `make test-module` with
  **305 passed**.
- Coverage report shows **TOTAL 93.43%** (above 85% requirement).
- E2E tests inside `core/ceremony_engine/tests/test_ceremony_engine_e2e.py`
  pass as part of the module test run.
- Idempotency is integrated into `CeremonyRunner` with explicit tests.
- Primitive step identifiers and step status maps were replaced with DDD
  Value Objects (`StepId`, `StepStatusEntry`, `StepStatusMap`) and updated
  across domain, application, infrastructure, and tests.
- LLM invocation is now mediated by an application use case
  (`GenerateLlmTextUseCase`) and consumed by ceremony step handlers.
- `CeremonyRunner` now requires `MessagingPort` and emits event envelopes for
  step execution and transition application.

---

### 2) Architecture alignment (DDD + Hexagonal)
#### 2.1 Domain layer compliance
Strengths:
- Domain entities and value objects are immutable (`@dataclass(frozen=True)`).
- Validation is done in `__post_init__` with fail-fast semantics.
- Domain rules (e.g., states, transitions, guards) are enforced in the aggregate.
  Examples:
  - `CeremonyDefinition` validates initial/terminal states, guard references,
    and role action references.
  - `StepResult` enforces terminal status usage only.
  - `CeremonyInstance` owns transition execution and step result application
    (tell, don't ask).

Risks / Gaps:
- `StepId` enforces strict snake_case. Existing YAML or external inputs that
  use other formats will now fail fast (good for invariants, but may break
  backward compatibility).
- `StepResult` disallows `PENDING` and `IN_PROGRESS`, but `HumanGateStepHandler`
  returns `WAITING_FOR_HUMAN`, which is allowed. However, the runner interprets
  any non-success as failure for transitions, which may stall transitions unless
  the caller triggers `transition_state` explicitly.
- `CeremonyInstance` now enforces idempotency key invariants: keys must be a
  `frozenset` of non-empty strings. Retention/cleanup policies remain undefined.

Implications:
- Human gate flows require explicit orchestration by the caller and are not
  fully modeled as a state machine in the runner.
 - The domain has no explicit constraints on idempotency key lifecycle, which
  could allow unbounded growth or inconsistent dedupe semantics.
 - Step identifiers must be normalized at the DSL boundary to avoid runtime
  failures after validation hardening.

#### 2.2 Application layer (ports & services)
Strengths:
- Ports are defined in the application layer and adapters implement them.
- `CeremonyRunner` orchestrates flow via ports and domain logic.
 - Fail-fast validation is enforced in the runner at step/transition boundaries.
 - **IdempotencyPort is now integrated** for step and transition execution
   (skip on COMPLETED/IN_PROGRESS, mark COMPLETED on success).
 - Default timeouts and retry policy access are now delegated to the aggregate
   (tell, don't ask).
 - LLM access is wrapped in an application use case (`GenerateLlmTextUseCase`)
   and injected into step handlers (DDD/Hexagonal compliance).
 - Event publishing is now mandatory and uses `EventEnvelope` for
   `ceremony.step.executed` and `ceremony.transition.applied`.

Risks / Gaps:
- The runner does not apply any lifecycle management for `WAITING_FOR_HUMAN`
   states (timeouts, reminders, or automatic retries).

Implications:
- Idempotency behavior is not enforced at the ceremony engine boundary.
- Human gate steps are effectively “paused” without a domain-level wake-up or
  event-driven continuation model.

#### 2.2.1 Runner behavior (step-by-step)
The `CeremonyRunner.execute_step` method follows this order:
1) Find step by `step_id`.
2) Validate step executable (state matches, status executable, not terminal).
3) Resolve timeout (step-specific or default; validate against step_max).
4) Resolve retry policy (step-specific or default policy).
5) Idempotency gate: check status, mark IN_PROGRESS (optional).
6) Execute handler with retry and timeout logic.
7) Update instance `step_status`.
8) If result is success, mark idempotency COMPLETED and evaluate transitions.
9) Persist instance if a persistence port is provided.

Critical observations:
- Transition evaluation is automatic after successful step completion; it does
  not wait for explicit triggers unless `transition_state()` is called.
- Only the first passing transition is applied; multiple valid transitions are
  not disambiguated.
- On `WAITING_FOR_HUMAN`, no automatic retry or resume occurs.

#### 2.3 Infrastructure layer (adapters and mappers)
Strengths:
- YAML parsing and validation live in infrastructure, not the domain.
- Mappers are explicit and avoid reflection/dynamic mutation.
- Adapters follow port interfaces.
 - Event envelope serialization is standardized in `core/shared/events`.
 - **Mappers and persistence adapters now have explicit unit tests**, raising
   coverage above 85%.

Risks / Gaps:
- Backlog review is still handled by `services/backlog_review_processor` and
  does **not** use the ceremony engine yet.
- The new `planning_ceremony_processor` uses fire-and-forget gRPC to start
  ceremonies, but step handlers only **submit** async deliberation/task-extraction
  jobs and do not consume resulting events.
- Dual persistence adapter tolerates Neo4j failures without reconciliation or
  compensating events.
- Rehydration port exists but is not integrated in the runner or a use case.
 - The YAML validator supplies defaults (e.g., description, timeouts), allowing
  minimal definitions without explicit intent.

Implications:
- The engine is functionally incomplete for real ceremony execution.
- Dual-write consistency is not self-healing or observable through events.
 - The DSL can be “valid” without being operationally safe.

#### 2.3.1 Step handlers (current state)
Each handler is implemented but does not yet consume results:
- **Deliberation**: submits to `SubmitDeliberationUseCase` (port-backed) and
  returns a submission envelope (`deliberation_id`, `task_id`, `status`).
- **Task extraction**: submits to `SubmitTaskExtractionUseCase` (port-backed)
  and returns a submission envelope (no mock task list).
- **Context requirements**: both steps require `ContextKey.INPUTS` with
  `story_id` and `ceremony_id`; task extraction also requires
  `agent_deliberations`.
- **Aggregation**: aggregates values from `ContextKey.INPUTS` using
  `merge`/`list`/`concat` strategies (no mock data).
- **Publish**: publishes via `MessagingPort` with a real `EventEnvelope`.
- **Human gate**: reads approval from context and returns WAITING or COMPLETED.

Impact:
- E2E tests passing against these handlers do **not** validate real integrations.
- It is possible to reach terminal state without any external side-effects.

---

### 3) DSL YAML design and validation
Strengths:
- YAML schema is validated and mapped into domain objects.
- Cross-reference validation exists in `CeremonyDefinition`.
- Guards and transitions are enforced with strict fail-fast rules.

Risks / Gaps:
- YAML validator uses defaults for missing fields (e.g., description).
  This can allow partially specified ceremonies without explicit intent.
- The DSL allows `role.allowed_actions` to reference step IDs or triggers,
  but no runtime enforcement exists in the runner.

Implications:
- DSL may accept definitions that are syntactically valid but incomplete.
- Authorization or role gates are not enforced by the engine.

#### 3.1 DSL field-by-field validation summary
The validator currently enforces:
- `version`, `name`, `states`, `transitions` are required.
- `states` must contain exactly one `initial=true`.
- Terminal states cannot have outgoing transitions.
- Transitions and steps must reference existing states.
- Guards referenced in transitions must exist.
- Roles must reference existing step IDs or trigger names.

The validator currently **does not** enforce:
- Non-empty description for all entities (description is defaulted).
- Role enforcement at runtime.
- Schema validation for outputs beyond type presence.

Implication:
- The DSL is structurally valid, but not operationally safe without higher-level
  policies or tests.

---

### 4) Cohesion with other modules
Current coupling points:
- `core/shared/events/event_envelope` is used by messaging adapter.
- `core/shared/idempotency` is used by Backlog Review Processor consumers
  (e.g., task extraction results).
- `planning_ceremony_processor` integrates the engine via fire-and-forget gRPC
  and uses ceremony runner + step handlers.
- Backlog review remains outside the engine (`services/backlog_review_processor`).

Risks / Gaps:
- E0 is only partially wired: `planning_ceremony_processor` starts ceremonies,
  but result consumption still happens outside the engine.
- E2E tests under `e2e/tests` reference Planning/BRP flows, not E0.

Implications:
- There is no end-to-end validation of E0 behavior across services.
- The engine does not yet enforce cross-service contracts.

#### 4.1 Service-level idempotency map (current state)
This map clarifies existing idempotency mechanisms across services:

1) **Backlog Review Processor**
   - Uses `IdempotencyPort` to dedupe NATS events.
   - Example: `TaskExtractionResultConsumer` checks and marks idempotency keys.

2) **Planning**
   - Uses a **command log** pattern via `CommandLogPort` and
     `idempotent_grpc_handler` to dedupe gRPC requests by `request_id`.
   - This is idempotency, but not via `IdempotencyPort`.

3) **Other services**
   - References to idempotency exist in tests or helper code, but a consistent
     cross-service contract is not enforced (e.g., envelope-level idempotency
     vs command-level idempotency).

Implication:
- Idempotency exists, but the **strategy varies by service**, which increases
  integration risk and weakens system-wide guarantees.

---

### 5) E2E readiness
Status:
- E2E tests in `e2e/tests` target Planning/BRP flows.
- A dedicated E2E runner for the ceremony engine was added separately to align
  with the existing E2E pattern (Dockerfile + job + Makefile).

Risks / Gaps:
- Existing E2E tests have multiple stages that are “assumed” rather than
  validated against real infrastructure signals (Ray, vLLM, NATS).
- No standard E2E contract verification for engine events exists.
 - E2E for E0 validates step execution and guard transitions, but does not yet
  validate persistence or NATS publishing.

Implications:
- E2E signal is weaker than it appears. It validates sequencing but not actual
  side-effects or message delivery semantics.

Evidence update:
- Local E2E tests under `core/ceremony_engine/tests/test_ceremony_engine_e2e.py`
  now pass after fixing ceremony path resolution and role casing.

#### 5.1 E2E alignment with existing conventions
The E0 E2E test is aligned with the repository E2E conventions:
- `Dockerfile` builds a self-contained runner image.
- `job.yaml` executes in Kubernetes with standard labels.
- `Makefile` provides build/push/deploy/logs targets.
This allows E0 to be executed by `e2e/run-e2e-tests.sh` alongside existing tests.

---

### 6) Unit test coverage (target >85%)
Observations:
- Unit tests exist for domain objects, runner, adapters, and YAML validation.
 - Coverage report generated by `make test-module` shows **TOTAL 91.70%**.

Risks / Gaps:
- No coverage guarantees are enforced in CI for `core/ceremony_engine` only.
- The new E2E runner is not unit-tested (expected for E2E scripts).

Implications:
- The >85% requirement is **met** locally; CI should enforce the same threshold.

#### 6.1 Suggested coverage gate
To enforce coverage for E0:
- Run `pytest --cov=core.ceremony_engine --cov-report=xml` in CI.
- Fail pipeline if total coverage < 85%.
- Store coverage artifacts to avoid regressions.

---

### 7) Gap detection (system-wide, re-analysis perspective)
The following gaps represent cross-cutting issues that can affect E0 and the
broader application:

1) **Idempotency boundaries**
   - Multiple idempotency strategies coexist (event envelope, command log,
     consumer-level dedupe). There is no unifying contract at the platform level.
   - Risk: duplicate side-effects at service boundaries and inconsistent dedupe.

2) **Rehydration strategy**
   - Rehydration port exists but is not part of the execution flow.
   - Risk: state recovery is theoretical and not exercised in runtime flows.

3) **Event envelope consistency**
   - Envelope contract exists, but E0 runner still does not publish events.
   - Risk: inconsistent event formats across services when E0 is integrated.

4) **Dual-write reconciliation**
   - Neo4j failures are swallowed without compensating events or repair jobs.
   - Risk: graph divergence and partial observability.

5) **Real E2E validation**
   - Some E2E tests validate state transitions but not system behavior.
   - Risk: green tests with broken runtime integrations.

6) **Contract tests for DSL**
   - No golden tests validating real-world DSL with expected runtime outputs.
   - Risk: DSL evolution breaks real ceremony definitions silently.

7) **Operational observability**
   - No explicit metrics or trace instrumentation in the engine runner.
   - Risk: debugging runtime failures is difficult under load.

8) **Security and tenancy boundaries**
   - Ceremony engine inputs are config-driven, but no policy layer enforces
     authorization or tenancy context. Role-based actions exist in DSL but are
     not enforced by runtime.
   - Risk: unauthorized transitions or cross-tenant data leakage if integrated
     into multi-tenant flows.

9) **Configuration drift**
   - Multiple ceremony YAMLs can be introduced without a central registry or
     validation gate in CI. There is no mandatory schema version bump or
     compatibility gate.
   - Risk: production drift between deployed artifacts and repo definitions.

---

### 8) Recommendations (actionable)
1) Keep `IdempotencyPort` integration and extend it to messaging publish paths
   now that publish steps emit events via `MessagingPort`.
2) Add a `RehydrationUseCase` and validate rehydration flows in tests.
3) Enforce >85% coverage in CI for `core/ceremony_engine`.
4) Replace placeholder step handlers with real integrations (or explicit
   fail-fast behaviors) to avoid false confidence.
5) Add contract tests for YAML DSL (golden files + expected step execution
   outputs).
6) Add E2E coverage that verifies actual side-effects (NATS, persistence).
7) Standardize idempotency boundaries across services (envelope vs command log).
8) Add role enforcement checks in runner based on DSL `roles.allowed_actions`.
9) Add a reconciliation event or compensating process for Neo4j failures.

---

## E0 Ceremony Engine — Graphical / Schematic Format

### A) Component Map (Hexagonal)
```
                   +------------------------------+
                   |        E2E Test Runner       |
                   |  (e2e/tests/08-ceremony-...) |
                   +--------------+---------------+
                                  |
                                  v
+------------------+     +-------------------+     +------------------+
|  YAML DSL Config | --> | CeremonyDefinition| --> | CeremonyRunner   |
| config/ceremonies|     | (Domain Aggregate)|     | (Application)    |
+------------------+     +---------+---------+     +--------+---------+
                                      |                      |
                                      v                      v
                             +--------+--------+     +-------+--------+
                             | Value Objects   |     | Ports           |
                             | (State, Step...)|     | (Messaging,     |
                             +-----------------+     | Persistence...) |
                                                     +-------+--------+
                                                             |
                                                             v
                                                   +---------+---------+
                                                   | Adapters          |
                                                   | (NATS, Neo4j,     |
                                                   |  Valkey, Handlers)|
                                                   +-------------------+
```

### B) Runtime Flow (Single Ceremony)
```
Load YAML -> Validate DSL -> Build CeremonyDefinition
       -> Create CeremonyInstance (initial state)
       -> Execute Step(s)
           -> StepHandler (mock or real)
           -> StepResult
       -> Evaluate Guards -> Transition State
       -> Persist (if configured)
       -> Terminal State reached
```

### C) Gaps Matrix (Impact vs. Layer)
```
Layer          | Gap                             | Impact
--------------+----------------------------------+-----------------------
Domain        | Mutable step_status dict         | Hidden mutations
Application   | Idempotency not integrated       | Duplicate side-effects
Application   | Messaging port unused            | Events not emitted
Infrastructure| Placeholder handlers             | False-positive E2E
Infrastructure| Dual-write reconciliation absent | Graph divergence
E2E           | Assumed stages                   | Invalid green signal
```

### D) E2E Coverage (Current vs Target)
```
Current E2E:
  Planning/BRP flows  -> ✅
  Ceremony engine DSL -> ❌ (before) / ✅ (after new E2E)

Target E2E:
  DSL load + validation -> ✅
  Step handlers -> ✅
  Guard transitions -> ✅
  Persistence -> 🚧
  NATS events -> 🚧
```

---

### Notes
This documentation is intended to be a living artifact. As E0 matures and
integrations are implemented, the gap matrix and runtime flow should be updated.

```
EOF
```

