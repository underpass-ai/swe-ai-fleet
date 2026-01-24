## Ceremony Engine Completion Tasks

Purpose: define the remaining tasks required to deliver a production-ready
ceremony engine and the new `planning_ceremony_processor` integration.

### 1) Core engine correctness
- Add idempotency to publish paths: integrate `IdempotencyPort` inside
  `PublishStepHandler` and enforce idempotency on `MessagingPort.publish_event`.
- Persist step outputs in `CeremonyInstance` (domain) and surface them in the
  `ExecutionContext` for downstream steps (aggregation/publish).
- Add a `RehydrationUseCase` that restores `CeremonyInstance` from persistence
  and validates invariants against current definitions.
- Enforce `Role.allowed_actions` at runtime in `CeremonyRunner`.
- Add a domain-safe builder for `CeremonyInstance` to avoid direct `replace`
  usage and to centralize validation.

### 2) Handler integrations
- `AggregationStepHandler`: support reading step outputs (not only inputs) and
  explicit aggregation types for objects and lists.
- `PublishStepHandler`: enforce required payload schema when `Output.schema`
  is defined in the ceremony definition.
- `DeliberationStepHandler`: add optional `constraints` mapping and validate
  content against an explicit contract (no dynamic keys).
- `TaskExtractionStepHandler`: accept explicit `agent_deliberations` from context
  and validate structure (agent_id, role, proposal).

### 3) Event contracts (NATS)
- Define ceremony engine event contracts in `specs/asyncapi.yaml`:
  - `ceremony.step.executed`
  - `ceremony.transition.applied`
  - `ceremony.publish.requested` / `ceremony.publish.completed`
- Add contract tests that validate `EventEnvelope` payload shapes for these
  subjects.

### 4) planning_ceremony_processor service
- Add `Dockerfile`, `requirements.txt`, and `pyproject.toml` or align to the
  existing service build pattern.
- Add `generate-protos.sh` for `planning_ceremony.proto`.
- Add a thin client in Planning Service to call
  `StartPlanningCeremony` (fire-and-forget).
- Add NATS consumers in `planning_ceremony_processor` to consume results
  (e.g., `agent.response.completed`) and advance ceremony state.

### 5) Persistence and observability
- Emit reconciliation events when Neo4j writes fail in
  `DualPersistenceAdapter` (align with Planning’s `dualwrite` pattern).
- Add structured logging for step start/end, transition evaluation, and
  publish outcomes.
- Add metrics counters for step success/failure and publish success/failure.

### 6) CI quality gates
- Enforce ≥85% coverage for `core/ceremony_engine` in CI.
- Add tests for:
  - `PublishStepHandler` idempotency behavior
  - Aggregation with invalid sources and type mismatches
  - Rehydration happy-path and invariant failures

### 7) E2E validation
- Add E2E flows that validate real side-effects:
  - NATS messages published
  - Persistence updated in Valkey/Neo4j
  - External service calls (Ray Executor) triggered
- Ensure E2E coverage for `planning_ceremony_processor` gRPC start.

### 8) Security and compliance
- Validate that publish payloads do not include secrets or raw prompts.
- Add allowlist for `publish_step` subjects to prevent arbitrary topics.
- Ensure correlation IDs are propagated to all publish events.

### 9) Operational readiness
- Provide Helm/K8s manifests for `planning_ceremony_processor` with resource
  limits and health probes.
- Add readiness check for NATS and Ray Executor connectivity.
- Document rollout/rollback steps in `deploy/`.
