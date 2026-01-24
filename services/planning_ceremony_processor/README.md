# Planning Ceremony Processor

gRPC service that starts ceremony executions (fire-and-forget). Integrates the ceremony engine with NATS, Valkey, and the Ray executor.

## Development

```bash
# From project root
make test-module MODULE=services/planning_ceremony_processor
```

## Configuration

Environment variables: `NATS_URL`, `RAY_EXECUTOR_URL`, `VLLM_URL`, `VLLM_MODEL`, `CEREMONIES_DIR`, `VALKEY_HOST`, `VALKEY_PORT`, `VALKEY_DB`, `PLANNING_CEREMONY_GRPC_ADDR`.
