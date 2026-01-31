# E2E Test: Advance Ceremony on Agent Completed

Validates that `planning_ceremony_processor` receives and processes `agent.response.completed` events via `AgentResponseCompletedConsumer`.

## Overview

This test verifies the end-to-end flow implemented in this session:

1. **Start ceremony via gRPC**: Obtains `instance_id` and `correlation_id`.
2. **Publish agent.response.completed**: Sends an EventEnvelope to NATS subject `agent.response.completed` (stream `AGENT_RESPONSES`) with that `correlation_id` and a `task_id` in the payload.
3. **Wait for consumer**: Gives `AgentResponseCompletedConsumer` time to poll, parse, and ack the message.
4. **Verify instance still exists**: Rehydrates the ceremony instance to confirm it was not removed and the consumer did not crash.
5. **Verify consumer subscription**: Confirms the durable consumer exists on `AGENT_RESPONSES`.

## Test Flow

- Same infrastructure as test 11 (NATS, Neo4j, Valkey, gRPC).
- Event payload follows `parse_required_envelope` contract: `event_type`, `payload` (with `task_id`), `idempotency_key`, `correlation_id`, `timestamp`, `producer`, `metadata`.

## Prerequisites

- `planning_ceremony_processor` deployed and running.
- NATS JetStream with `AGENT_RESPONSES` stream.
- Valkey and Neo4j available.
- Ceremony definitions in `config/ceremonies/` (e.g. `e2e_multi_step`).

## Building

```bash
cd e2e/tests/12-advance-ceremony-on-agent-completed
make build
make build-push
```

## Deployment

```bash
make deploy
make status
make logs
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLANNING_CEREMONY_PROCESSOR_URL` | gRPC endpoint | `planning-ceremony-processor.swe-ai-fleet.svc.cluster.local:50057` |
| `NATS_URL` | NATS connection URL | `nats://nats.swe-ai-fleet.svc.cluster.local:4222` |
| `NEO4J_URI` | Neo4j bolt URI | `bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687` |
| `NEO4J_USER` / `NEO4J_PASSWORD` | From `neo4j-auth` secret | — |
| `VALKEY_HOST` / `VALKEY_PORT` | Valkey | `valkey.swe-ai-fleet.svc.cluster.local:6379` |
| `CEREMONY_NAME` | Ceremony definition | `e2e_multi_step` |
| `CEREMONIES_DIR` | Path to YAML | `/app/config/ceremonies` |

## Related

- **Test 11**: Full flow (start ceremony, steps, persistence, rehydration, consumer subscription).
- **AgentResponseCompletedConsumer**: `services/planning_ceremony_processor/infrastructure/consumers/agent_response_completed_consumer.py`.

## References

- [Ceremony Engine](../../../../core/ceremony_engine/README.md)
- [E2E Test Runner](../../../run-e2e-tests.sh)
