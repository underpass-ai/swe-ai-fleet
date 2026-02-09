# Task Derivation Service

Event-driven worker that decomposes approved plans into tasks.

## Service Type

- No public gRPC server
- NATS worker with outbound gRPC clients

## Processing Flow

1. Consume `task.derivation.requested`.
2. Fetch plan data from Planning service.
3. Fetch context from Context service.
4. Build derivation prompt from YAML config.
5. Submit derivation to Ray Executor.
6. Consume `agent.response.completed` results.
7. Parse tasks, create them in Planning, publish completion/failure events.

## NATS Contracts

Consumed subjects:

- `task.derivation.requested` (stream `task_derivation`, durable `task-derivation-request-consumer`)
- `agent.response.completed` (stream `AGENT_RESPONSES`, durable `task-derivation-result-consumer`)

Published subjects:

- `task.derivation.completed`
- `task.derivation.failed`

## Configuration

From `services/task_derivation/server.py`:

- `NATS_URL` (default: `nats://nats.swe-ai-fleet.svc.cluster.local:4222`)
- `PLANNING_SERVICE_ADDRESS` (default: `planning.swe-ai-fleet.svc.cluster.local:50054`)
- `CONTEXT_SERVICE_ADDRESS` (default: `context.swe-ai-fleet.svc.cluster.local:50054`)
- `RAY_EXECUTOR_ADDRESS` (default: `ray-executor.swe-ai-fleet.svc.cluster.local:50056`)
- `VLLM_URL` (default: `http://vllm-server-service.swe-ai-fleet.svc.cluster.local:8000`)
- `VLLM_MODEL` (default: `Qwen/Qwen2.5-7B-Instruct`)
- `TASK_DERIVATION_CONFIG` (default: `/app/config/task_derivation.yaml`)

`TASK_DERIVATION_CONFIG` must exist and include at least `prompt_template`.

In Kubernetes, `deploy/k8s/30-microservices/task-derivation.yaml` resolves
service URLs from ConfigMap `service-urls` (`NATS_URL`, `PLANNING_URL`,
`CONTEXT_URL`, `RAY_EXECUTOR_ADDRESS`, `VLLM_URL`, `VLLM_MODEL`).

## Run

```bash
python services/task_derivation/server.py
```

## Tests

```bash
make test-module MODULE=services/task_derivation
```
