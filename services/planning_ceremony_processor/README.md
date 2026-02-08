# Planning Ceremony Processor Service

gRPC + NATS service that executes ceremony-engine definitions for planning ceremonies.

## gRPC API

- Proto: `specs/fleet/planning_ceremony/v1/planning_ceremony.proto`
- Service: `PlanningCeremonyProcessor`
- Implemented RPC: `StartPlanningCeremony`
- Default bind: `PLANNING_CEREMONY_GRPC_ADDR=0.0.0.0:50057`

## Runtime Composition

`services/planning_ceremony_processor/server.py` wires:

- `CeremonyDefinitionAdapter`
- `RayExecutorAdapter`
- `DualPersistenceAdapter`
- `ValkeyIdempotencyAdapter`
- `StepHandlerRegistry` and `CeremonyRunner` from `core.ceremony_engine`
- Use cases:
  - `StartPlanningCeremonyUseCase`
  - `AdvanceCeremonyOnAgentCompletedUseCase`

## NATS Integration

Consumed subject:

- `agent.response.completed`

Consumer details:

- Stream: `AGENT_RESPONSES`
- Durable: `planning-ceremony-processor-agent-response-completed-v1`

Purpose:

- Advance ceremony state when step-level agent responses are completed.

## Configuration

From `services/planning_ceremony_processor/infrastructure/adapters/environment_config_adapter.py`:

- `NATS_URL` (default: `nats://nats:4222`)
- `RAY_EXECUTOR_URL` (default: `ray-executor:50056`)
- `VLLM_URL` (default: `http://vllm-server:8000`)
- `VLLM_MODEL` (default: `meta-llama/Llama-3.1-8B-Instruct`)
- `CEREMONIES_DIR` (default: `/app/config/ceremonies`)
- `VALKEY_HOST` (default: `valkey`)
- `VALKEY_PORT` (default: `6379`)
- `VALKEY_DB` (default: `0`)
- `PLANNING_CEREMONY_GRPC_ADDR` (default: `0.0.0.0:50057`)

## Run

```bash
python services/planning_ceremony_processor/server.py
```

## Tests

```bash
make test-module MODULE=services/planning_ceremony_processor
```
