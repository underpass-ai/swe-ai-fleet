# Workflow Service

gRPC + NATS service that manages task lifecycle transitions and role-based validation.

## gRPC API

- Proto: `specs/fleet/workflow/v1/workflow.proto`
- Default port: `GRPC_PORT=50056`

Implemented RPCs (`services/workflow/infrastructure/grpc_servicer.py`):

- `GetWorkflowState`
- `RequestValidation`
- `GetPendingTasks`
- `ClaimTask`
- `GetStats`

## NATS Integration

Consumed subjects:

- `agent.work.completed` (stream `AGENT_WORK`, durable `workflow-agent-work-completed-v1`)
- `planning.story.transitioned` (stream `PLANNING_EVENTS`, durable `workflow-planning-events-v1`)

Published subjects:

- `workflow.state.changed`
- `workflow.task.assigned`
- `workflow.validation.required`
- `workflow.task.completed`

## Runtime Composition

`services/workflow/server.py` wires:

- Domain FSM services (`WorkflowTransitionRules`, `WorkflowStateMachine`)
- Neo4j repository + Valkey cache decorator
- NATS messaging adapter
- Consumers: `AgentWorkCompletedConsumer` and `PlanningEventsConsumer`

## Configuration

- `GRPC_PORT` (default: `50056`)
- `NEO4J_URI` (default: `bolt://neo4j:7687`)
- `NEO4J_USER` (default: `neo4j`)
- `NEO4J_PASSWORD` (required)
- `VALKEY_HOST` (default: `valkey`)
- `VALKEY_PORT` (default: `6379`)
- `NATS_URL` (default: `nats://nats:4222`)
- `WORKFLOW_FSM_CONFIG` (default: `/app/config/workflow.fsm.yaml`, file must exist)

## Run

```bash
python services/workflow/server.py
```

## Tests

```bash
make test-module MODULE=services/workflow
```
