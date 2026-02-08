# Ray Executor Service

gRPC gateway between control-plane services and Ray workers.

## gRPC API

- Proto: `specs/fleet/ray_executor/v1/ray_executor.proto`
- Default port: `GRPC_PORT=50056`

Implemented RPCs:

- `ExecuteDeliberation`
- `ExecuteBacklogReviewDeliberation`
- `GetDeliberationStatus`
- `GetStatus`
- `GetActiveJobs`

## Runtime Behavior

`services/ray_executor/server.py`:

- Connects to Ray (`ray.init`) with runtime environment.
- Optionally connects to NATS.
- Wires use cases and gRPC servicer.
- Starts periodic polling for active deliberations.

NATS behavior:

- Controlled by `ENABLE_NATS` (default `true`).
- If NATS connection fails, startup continues and service remains available without publishing.

## NATS Publishing

When NATS is available:

- Publishes deliberation results to `orchestration.deliberation.completed`.
- Can publish streaming helper events under `vllm.streaming.*`.

## Configuration

From `services/ray_executor/config.py`:

- `GRPC_PORT` (default: `50056`)
- `RAY_ADDRESS` (default: `ray://ray-gpu-head-svc.ray.svc.cluster.local:10001`)
- `NATS_URL` (default: `nats://nats.swe-ai-fleet.svc.cluster.local:4222`)
- `ENABLE_NATS` (default: `true`)

## Run

```bash
python services/ray_executor/server.py
```

## Tests

```bash
make test-module MODULE=services/ray_executor
```
