# SWE AI Fleet Documentation

Central index for project documentation.

## Documentation Map

Architecture and system reference:

- `docs/architecture/OVERVIEW.md`
- `docs/architecture/MICROSERVICES.md`
- `docs/architecture/CORE_CONTEXTS.md`

Getting started and operations:

- `docs/getting-started/README.md`
- `docs/QUICK_START.md`
- `docs/MODULAR_ARCHITECTURE.md`
- `docs/TESTING_ARCHITECTURE.md`

Normative guides:

- `docs/normative/HEXAGONAL_ARCHITECTURE.md`
- `docs/normative/HUMAN_IN_THE_LOOP.md`
- `specs/API_FIRST_STRATEGY.md`

API contracts:

- `specs/` (protobuf and async contracts)

## Code Documentation Coverage

Each first-level deployable service and core context has a local `README.md`.

Core contexts (`core/`):

- `core/agents_and_tools/README.md`
- `core/ceremony_engine/README.md`
- `core/context/README.md`
- `core/memory/README.md`
- `core/orchestrator/README.md`
- `core/ray_jobs/README.md`
- `core/reports/README.md`
- `core/shared/README.md`

Services (`services/`):

- `services/agent_executor/README.md`
- `services/backlog_review_processor/README.md`
- `services/context/README.md`
- `services/orchestrator/README.md`
- `services/planning/README.md`
- `services/planning_ceremony_processor/README.md`
- `services/planning-ui/README.md`
- `services/ray_executor/README.md`
- `services/task_derivation/README.md`
- `services/workflow/README.md`

## Related Paths

- Deployment: `deploy/`
- Scripts: `scripts/`
- Protobuf and contracts: `specs/`
- Contribution workflow: `CONTRIBUTING.md`
