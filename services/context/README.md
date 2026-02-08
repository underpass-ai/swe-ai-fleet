# Context Service

gRPC + NATS service that assembles role-aware context and projects planning/orchestration events into the context graph.

## gRPC API

- Proto: `specs/fleet/context/v1/context.proto`
- Default port: `GRPC_PORT=50054`

Implemented RPCs:

- `GetContext`
- `UpdateContext`
- `RehydrateSession`
- `ValidateScope`
- `CreateStory`
- `CreateTask`
- `AddProjectDecision`
- `TransitionPhase`
- `GetGraphRelationships`

## NATS Integration

NATS is required for this service.
Startup fails fast when `ENABLE_NATS=false`.

Consumed planning subjects:

- `planning.project.created`
- `planning.epic.created`
- `planning.story.created`
- `planning.task.created`
- `planning.story.transitioned`
- `planning.plan.approved`

Consumed orchestration subjects:

- `orchestration.deliberation.completed`
- `orchestration.task.dispatched`

Async request subjects:

- `context.update.request`
- `context.rehydrate.request`

Published subjects:

- `context.update.response`
- `context.rehydrate.response`
- `context.events.updated` (event type `context.updated`)

## Dependencies

- Neo4j (graph query/command)
- Redis/Valkey
- NATS JetStream

## Configuration

From `core/context/adapters/env_config_adapter.py`:

- `GRPC_PORT` (default: `50054`)
- `NEO4J_URI` (default: `bolt://neo4j:7687`)
- `NEO4J_USER` (default: `neo4j`)
- `NEO4J_PASSWORD` (required)
- `REDIS_HOST` (default: `redis`)
- `REDIS_PORT` (default: `6379`)
- `NATS_URL` (default: `nats://nats:4222`)
- `ENABLE_NATS` (default: `true`, required in practice)

## Run

```bash
python services/context/server.py
```

## Tests

```bash
make test-module MODULE=services/context
```
