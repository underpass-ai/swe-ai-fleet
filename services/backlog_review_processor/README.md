# Backlog Review Processor Service

Event-driven worker that converts backlog review deliberations into Planning tasks.

## Service Type

- No public gRPC API
- NATS JetStream worker

## Runtime Flow

1. `BacklogReviewResultConsumer` consumes `agent.response.completed.backlog-review.role`.
2. `AccumulateDeliberationsUseCase` persists role deliberations in Neo4j.
3. When all required roles are present, publishes `planning.backlog_review.deliberations.complete`.
4. `DeliberationsCompleteConsumer` consumes that event and triggers task extraction through Ray Executor.
5. `TaskExtractionResultConsumer` consumes `agent.response.completed.task-extraction`, creates tasks in Planning, and publishes `planning.backlog_review.tasks.complete`.

## NATS Contracts

Consumed subjects:

- `agent.response.completed.backlog-review.role`
- `planning.backlog_review.deliberations.complete`
- `agent.response.completed.task-extraction`

Published subjects:

- `planning.backlog_review.deliberations.complete`
- `planning.backlog_review.tasks.complete`

## Dependencies

- NATS JetStream
- Planning Service (gRPC)
- Ray Executor Service (gRPC)
- Neo4j (deliberation storage)
- Valkey (persistent idempotency gate via `ValkeyIdempotencyAdapter`)

## Configuration

From `services/backlog_review_processor/infrastructure/adapters/environment_config_adapter.py`:

- `NATS_URL` (default: `nats://nats:4222`)
- `PLANNING_SERVICE_URL` (default: `planning:50054`)
- `RAY_EXECUTOR_URL` (default: `ray-executor:50056`)
- `VLLM_URL` (default: `http://vllm-server:8000/v1`)
- `VLLM_MODEL` (default: `meta-llama/Llama-3.1-8B-Instruct`)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- `VALKEY_HOST`, `VALKEY_PORT`, `VALKEY_DB`

## Run

```bash
python services/backlog_review_processor/server.py
```

## Tests

```bash
make test-module MODULE=services/backlog_review_processor
```
