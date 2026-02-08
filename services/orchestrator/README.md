# Orchestrator Service

gRPC + NATS service that coordinates councils of agents and reacts to planning/context/agent events.

## gRPC API

- Proto: `specs/fleet/orchestrator/v1/orchestrator.proto`
- Default port: `GRPC_PORT=50055`

Implemented RPCs in `services/orchestrator/server.py`:

- `Deliberate`
- `Orchestrate`
- `GetStatus`
- `RegisterAgent`
- `CreateCouncil`
- `ListCouncils`
- `DeleteCouncil`

RPCs explicitly returning `UNIMPLEMENTED`:

- `StreamDeliberation`
- `UnregisterAgent`
- `ProcessPlanningEvent`
- `DeriveSubtasks`
- `GetTaskContext`
- `GetMetrics`

Proto RPCs present but not explicitly implemented in the server class:

- `DeliberateForBacklogReview`
- `GetDeliberationResult`

## Runtime Behavior

- Auto-initializes default councils if registry is empty: `DEV`, `QA`, `ARCHITECT`, `DEVOPS`, `DATA` (3 agents each).
- Uses Ray Executor adapter for async execution paths.
- Requires NATS enabled at startup (`ENABLE_NATS=true`).

## NATS Integration

Consumed subjects:

- `planning.story.transitioned`
- `planning.plan.approved`
- `agent.response.completed`
- `agent.response.failed`
- `agent.response.progress`
- `context.updated`
- `context.milestone.reached`
- `context.decision.added`

Published subjects:

- `orchestration.task.completed`
- `orchestration.task.failed`
- `orchestration.phase.changed`
- `orchestration.plan.approved`
- `orchestration.deliberation.completed`
- `orchestration.task.dispatched`

## Configuration

From `services/orchestrator/infrastructure/adapters/environment_configuration_adapter.py`:

- `GRPC_PORT` (default: `50055`)
- `NATS_URL` (default: `nats://nats:4222`)
- `ENABLE_NATS` (default: `true`, required)
- `RAY_EXECUTOR_ADDRESS` (default: `ray-executor:50056`)
- Optional runtime values used by service logic: `VLLM_URL`, `VLLM_MODEL`

## Run

```bash
python services/orchestrator/server.py
```

## Tests

```bash
make test-module MODULE=services/orchestrator
```
