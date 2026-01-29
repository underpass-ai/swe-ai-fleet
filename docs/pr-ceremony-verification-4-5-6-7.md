# Pull Request: Ceremony verification 4, 5, 6, 7

**Branch:** `feature/ceremony-verification-4-5-6-7`  
**Base:** `main`  
**Ref:** `docs/CEREMONY_ENGINE_STATUS_VERIFICATION.md`, `docs/CEREMONY_ENGINE_COMPLETION_TASKS.md`

---

## Summary

This PR completes ceremony engine verification items **4, 5, 6, and 7** from the status verification document:

- **4) planning_ceremony_processor service**: K8s deployment, NATS consumers (`AgentResponseCompletedConsumer`), integration with Planning service via gRPC and `StartPlanningCeremonyViaProcessorUseCase`, dual persistence and ceremony runner wiring.
- **5) Observability**: `CeremonyMetricsPort` and `LlmClientPort` added; ceremony runner and dual persistence adapter extended for metrics/LLM integration where needed.
- **6) Coverage**: Additional unit tests for `RehydrationUseCase`, `AggregationStepHandler`, `DualPersistenceAdapter`, and ceremony runner; CI continues to run `core/ceremony_engine` in the module matrix.
- **7) E2E coverage**: New E2E tests for ceremony engine and planning ceremony processor:
  - **09-ceremony-engine-real-side-effects**: Validates real side-effects (NATS messages, Valkey, Neo4j) when starting a ceremony via gRPC.
  - **10-planning-ceremony-processor-grpc-start**: Validates gRPC server accessibility and `StartPlanningCeremony` response.
  - **11-planning-ceremony-processor-full-flow**: Full flow from gRPC start through step execution, NATS, persistence, rehydration, and consumer subscription.

Additional changes:

- **Core ceremony_engine**: New ports (`CeremonyMetricsPort`, `LlmClientPort`), extended `CeremonyRunner` and `DualPersistenceAdapter`, config/streams for NATS in deploy.
- **Planning service**: New use case and handler to start backlog review ceremony via the processor; configuration and gRPC client adapter.
- **planning_ceremony_processor**: NATS consumer for `agent.response.completed`, gRPC servicer, Dockerfile, protos, K8s manifests.
- **Deploy**: `planning-ceremony-processor` Deployment/Service in `deploy/k8s/30-microservices/`, configmaps for ceremonies, `docker-compose` and scripts updates for local/E2E.
- **Makefile**: Targets for new E2E jobs (09, 10, 11).

---

## Type

- [ ] chore(hardening)
- [ ] fix
- [x] feat
- [ ] docs

---

## Tests

- [x] Unit tests added/updated (ceremony_engine: rehydration, aggregation, dual persistence, ceremony runner; planning: start ceremony via processor handler; planning_ceremony_processor: agent response consumer).
- [ ] CI green (to be confirmed after push).

---

## Notes

- **E2E tests** (09, 10, 11) require a full cluster with `planning_ceremony_processor`, NATS JetStream, Valkey, and Neo4j; see each test’s `e2e/tests/<nn>-*/README.md` for prerequisites and env vars.
- **Verification traceability**: Items 4–7 are aligned with `docs/CEREMONY_ENGINE_STATUS_VERIFICATION.md`; E2E coverage addresses the previous gap “No E2E that validate planning_ceremony_processor gRPC start” (Section 7.2).
- **Files touched**: 52 files (~3.8k insertions) across `core/ceremony_engine`, `services/planning`, `services/planning_ceremony_processor`, `e2e/tests/`, `deploy/k8s/`, `docker-compose`, and scripts.
