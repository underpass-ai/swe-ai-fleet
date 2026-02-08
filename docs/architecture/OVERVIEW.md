# System Architecture Overview

SWE AI Fleet is a multi-service platform for planning, context-driven deliberation, and execution orchestration.

## Architectural Style

- Service-oriented architecture with bounded contexts in `core/`
- Synchronous RPC via gRPC
- Asynchronous integration via NATS JetStream
- Persistent state in Neo4j and Valkey/Redis
- Distributed execution on Ray workers

## Main Planes

Product and planning plane:

- `services/planning-ui` (Astro SSR frontend)
- `services/planning` (Project/Epic/Story/Task and ceremonies)

Context and orchestration plane:

- `services/context`
- `services/orchestrator`
- `services/workflow`

Ceremony and processing plane:

- `services/planning_ceremony_processor`
- `services/backlog_review_processor`
- `services/task_derivation`

Execution plane:

- `services/ray_executor`
- `core/ray_jobs` payload executed in Ray workers
- `services/agent_executor` (Go skeleton, routing/store foundations only)

Data and messaging plane:

- Neo4j
- Valkey/Redis
- NATS JetStream

## Typical Runtime Patterns

Planning-driven async processing:

1. Planning service emits events.
2. Processors consume events and trigger deliberation or extraction.
3. Ray execution publishes agent responses.
4. Planning/Context/Orchestrator consumers update state and emit follow-up events.

Context-driven execution:

1. Services query Context for role-specific rehydration.
2. Orchestrator/Ray execution uses constrained context instead of full-repo prompts.
3. Result events flow back through NATS for persistence and next transitions.

## Notes on Current Implementation State

- `services/agent_executor` is intentionally partial and does not expose gRPC/NATS yet.
- `services/orchestrator` includes RPCs marked `UNIMPLEMENTED` in server code.
- `services/planning-ui` includes a known `501` stub for task-derivation ceremony start.
