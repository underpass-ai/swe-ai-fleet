# Planning Service

Primary planning domain service for Project, Epic, Story, Task, backlog review, and planning ceremony gateway.

## gRPC API

- Proto: `specs/fleet/planning/v2/planning.proto`
- Default port: `GRPC_PORT=50054`

Implemented groups:

- Project: `CreateProject`, `GetProject`, `ListProjects`, `DeleteProject`
- Epic: `CreateEpic`, `GetEpic`, `ListEpics`, `DeleteEpic`
- Story: `CreateStory`, `GetStory`, `ListStories`, `TransitionStory`, `DeleteStory`
- Decision: `ApproveDecision`, `RejectDecision`
- Task: `CreateTask`, `GetTask`, `ListTasks`
- Backlog review ceremony:
  - `CreateBacklogReviewCeremony`, `GetBacklogReviewCeremony`, `ListBacklogReviewCeremonies`
  - `AddStoriesToReview`, `RemoveStoryFromReview`, `AddAgentDeliberation`
  - `StartBacklogReviewCeremony`, `ApproveReviewPlan`, `RejectReviewPlan`
  - `CompleteBacklogReviewCeremony`, `CancelBacklogReviewCeremony`
- Planning ceremony gateway: `StartPlanningCeremony`

`StartPlanningCeremony` behavior:

- Forwards to Planning Ceremony Processor when `PLANNING_CEREMONY_PROCESSOR_URL` is configured.
- Returns `FAILED_PRECONDITION` when processor URL is not configured.

## NATS Integration

Published subjects (`planning.domain.value_objects.NATSSubject`):

- `planning.story.created`
- `planning.story.transitioned`
- `planning.story.tasks_not_ready`
- `planning.decision.approved`
- `planning.decision.rejected`
- `planning.plan.approved`
- `planning.task.created`
- `planning.tasks.derived`
- `planning.backlog_review.ceremony.started`
- `planning.backlog_review.ceremony.completed`
- `planning.backlog_review.story.reviewed`
- `planning.backlog_review.deliberations.complete`
- `planning.backlog_review.tasks.complete`

Consumed subjects (service-started workers):

- `agent.response.completed` (`TaskDerivationResultConsumer`, filters `task_id` prefixed with `derive-`)
- `planning.backlog_review.deliberations.complete`
- `planning.backlog_review.tasks.complete`
- `planning.dualwrite.reconcile.requested`

## Key Integrations

- Neo4j + Valkey storage (`StorageAdapter`, dual-write ledger and reconciliation)
- Ray Executor adapter (`RAY_EXECUTOR_URL`)
- Context Service adapter (`CONTEXT_SERVICE_URL`)
- Optional Planning Ceremony Processor adapter (`PLANNING_CEREMONY_PROCESSOR_URL`)

## Configuration

From `services/planning/infrastructure/adapters/environment_config_adapter.py`:

- `GRPC_PORT` (default: `50054`)
- `NATS_URL` (default: `nats://nats:4222`)
- `NEO4J_URI` (default: `bolt://neo4j:7687`)
- `NEO4J_USER` (default: `neo4j`)
- `NEO4J_PASSWORD` (default in code: `password`, override for real environments)
- `NEO4J_DATABASE` (optional)
- `VALKEY_HOST` (default: `valkey`)
- `VALKEY_PORT` (default: `6379`)
- `VALKEY_DB` (default: `0`)
- `RAY_EXECUTOR_URL` (default: `ray-executor:50055`)
- `CONTEXT_SERVICE_URL` (default: `context:50054`)
- `VLLM_URL` (default: `http://vllm:8000`)
- `VLLM_MODEL` (default: `Qwen/Qwen2.5-7B-Instruct`)
- `TASK_DERIVATION_CONFIG_PATH` (default: `config/task_derivation.yaml`)
- `PLANNING_CEREMONY_PROCESSOR_URL` (optional)

## Run

```bash
python services/planning/server.py
```

## Tests

```bash
make test-module MODULE=services/planning
```
