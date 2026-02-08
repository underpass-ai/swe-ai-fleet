# Agent Executor Service

Go service under active implementation.

## Current Status

`services/agent_executor` currently exposes domain and infrastructure building blocks only.
The entrypoint `cmd/agent-executor/main.go` logs a skeleton startup message.
No gRPC server, NATS consumers, or Ray/vLLM orchestration is wired yet.

## Implemented Components

### Backend selector

File: `services/agent_executor/internal/executor/selector/selection.go`

- Reads metadata keys `gpu_count` and `backend_tier`.
- `gpu_count` defaults to `1`.
- Validates `gpu_count` in range `1..MaxGPUCount`.
- `backend_tier` accepts `small` or `big`.
- If tier is omitted, it is inferred (`big` when `gpu_count >= 2`, otherwise `small`).

### Redis deliberation store

File: `services/agent_executor/internal/executor/store/redis_store.go`

- `Upsert`, `Get`, `Touch`, `MarkCompleted`, `MarkFailed`, `ListActive`.
- TTL-backed record key: `{prefix}:delib:{deliberation_id}`.
- Active index set: `{prefix}:delib:active`.

## Run

```bash
go run ./cmd/agent-executor
```

## Tests

```bash
go test ./...
```

## Pending Work

- gRPC transport layer
- NATS integration
- Ray/vLLM execution orchestration
