# E2E Test: Task Derivation <-> Planning (Contract + Async vLLM Flow)

This E2E test validates the real contract between Task Derivation and Planning through:
- `fleet.task_derivation.v1.TaskDerivationPlanningService`
- `planning.swe-ai-fleet.svc.cluster.local:50054`
- NATS event trigger `planning.plan.approved`

## What It Verifies

1. `GetPlanContext` returns seeded plan context.
2. `CreateTasks` persists tasks in Planning.
3. `ListStoryTasks` returns those tasks for the story.
4. `SaveTaskDependencies` persists dependency edges.
5. Dependency edge is verified directly in Neo4j.
6. `planning.plan.approved` is published with EventEnvelope.
7. Planning consumer + Task Derivation consumer are active in JetStream.
8. Async derivation pipeline persists `DEVELOPMENT` tasks for the approved plan.

## Prerequisites

- Planning service deployed and reachable.
- Task Derivation service deployed and reachable.
- Ray Executor + vLLM available for async derivation.
- NATS JetStream reachable from cluster.
- Valkey reachable from cluster.
- Neo4j reachable from cluster.
- Secret `neo4j-auth` available in namespace `swe-ai-fleet`.

## Build

```bash
cd e2e/tests/13-task-derivation-planning-service-grpc
make build
make build-push
```

## Deploy

```bash
make deploy
make status
make logs
```

## Environment Variables

In Kubernetes, `job.yaml` injects service URLs from ConfigMap `service-urls` and Neo4j credentials from Secret `neo4j-auth`.

| Variable | Required | Default |
|---|---|---|
| `PLANNING_SERVICE_URL` | No | from `service-urls.PLANNING_URL` |
| `VALKEY_HOST` | No | from `service-urls.VALKEY_HOST` |
| `VALKEY_PORT` | No | from `service-urls.VALKEY_PORT` |
| `NATS_URL` | No | from `service-urls.NATS_URL` |
| `NEO4J_URI` | No | from `service-urls.NEO4J_URI` |
| `NEO4J_USER` | Yes (from secret) | n/a |
| `NEO4J_PASSWORD` | Yes (from secret) | n/a |
| `TEST_CREATED_BY` | No | `e2e-task-derivation@system.local` |
| `DERIVATION_TIMEOUT_SECONDS` | No | `420` |
| `DERIVATION_POLL_INTERVAL_SECONDS` | No | `10` |
| `PRESERVE_TEST_DATA` | No | `false` |

## Notes

- The test creates temporary project/epic/story data through Planning gRPC.
- It seeds temporary plan snapshots directly in Valkey for `GetPlanContext` and async trigger.
- Async flow is triggered by publishing `planning.plan.approved` with EventEnvelope (same event consumed after `ApproveReviewPlan`).
- Cleanup is best-effort and can be skipped with `PRESERVE_TEST_DATA=true`.
