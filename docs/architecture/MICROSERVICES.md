# Microservices Reference

This document reflects the services currently present in `services/`.

## Service Inventory

| Service | Type | Interface | Default Port | Notes |
|---|---|---|---|---|
| `planning` | gRPC + NATS | `fleet.planning.v2.PlanningService` | `50054` | Core planning hierarchy and ceremony APIs |
| `context` | gRPC + NATS | `fleet.context.v1.ContextService` | `50054` | Rehydration, updates, graph projections |
| `orchestrator` | gRPC + NATS | `fleet.orchestrator.v1.OrchestratorService` | `50055` | Councils, deliberation, orchestration |
| `workflow` | gRPC + NATS | `fleet.workflow.v1.WorkflowOrchestrationService` | `50056` | Task FSM and validation flow |
| `ray_executor` | gRPC (+ optional NATS publishing) | `fleet.ray_executor.v1.RayExecutorService` | `50056` | Submits and tracks Ray deliberations |
| `planning_ceremony_processor` | gRPC + NATS consumer | `fleet.planning_ceremony.v1.PlanningCeremonyProcessor` | `50057` | Ceremony-engine execution entrypoint |
| `backlog_review_processor` | Event worker | NATS subjects | n/a | Aggregates deliberations and creates tasks |
| `task_derivation` | Event worker | NATS subjects | n/a | Derives tasks from plans via Ray |
| `planning-ui` | Web SSR | HTTP routes + gRPC clients | framework-managed | Astro frontend for planning and ceremonies |
| `workspace` | HTTP tool runtime | REST JSON endpoints | `50053` | Sandboxed execution sessions, capability catalog, policy-enforced tools |
| `agent_executor` | Go skeleton | none yet | n/a | Backend selector and Redis tracking implemented; transport pending |

## Key Asynchronous Subjects

Planning and ceremony:

- `planning.story.created`
- `planning.story.transitioned`
- `planning.plan.approved`
- `planning.backlog_review.deliberations.complete`
- `planning.backlog_review.tasks.complete`
- `planning.dualwrite.reconcile.requested`

Agent responses:

- `agent.response.completed`
- `agent.response.failed`
- `agent.response.progress`
- `agent.response.completed.backlog-review.role`
- `agent.response.completed.task-extraction`

Context and workflow:

- `context.events.updated` (event type `context.updated`)
- `workflow.state.changed`
- `workflow.task.assigned`

## Service-Level Documentation

For exact RPC, env vars, and consumers, use each service README under `services/*/README.md`.
