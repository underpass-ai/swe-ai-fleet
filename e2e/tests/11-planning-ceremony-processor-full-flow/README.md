# E2E Test: Planning Ceremony Processor Full Flow Validation

This E2E test validates the complete flow of `planning_ceremony_processor` using the ceremony engine in a deployed Kubernetes environment.

## Overview

This test verifies the end-to-end flow of the `planning_ceremony_processor` service:

1. **Start ceremony via gRPC**: Calls `planning_ceremony_processor` gRPC service to start a ceremony
2. **Execute steps**: Validates that ceremony steps are executed correctly
3. **Verify NATS messages**: Subscribes to NATS JetStream and verifies `ceremony.step.executed` messages are published
4. **Verify Valkey persistence**: Queries Valkey to verify the ceremony instance was persisted
5. **Verify Neo4j persistence**: Queries Neo4j to verify the ceremony instance node was created
6. **Verify rehydration**: Rehydrates the ceremony instance and validates it matches the current definition
7. **Verify consumer subscription**: Verifies that `AgentResponseCompletedConsumer` subscription exists

Unlike unit tests that use mocks, this test connects to actual services deployed in Kubernetes and validates real side-effects.

## Test Flow

1. **Start ceremony via gRPC**: Calls `StartPlanningCeremony` with all required fields
2. **Wait for execution**: Waits for ceremony steps to execute
3. **Verify NATS messages**: Checks that `ceremony.step.executed` messages are published to JetStream
4. **Verify Valkey persistence**: Queries Valkey to verify instance persistence
5. **Verify Neo4j persistence**: Queries Neo4j to verify instance node creation
6. **Verify rehydration**: Rehydrates instance and validates against current definition
7. **Verify consumer subscription**: Checks that `AgentResponseCompletedConsumer` subscription exists

## Prerequisites

- `planning_ceremony_processor` service deployed and running
- NATS JetStream available and accessible
- Valkey (Redis-compatible) available and accessible
- Neo4j available and accessible
- Ceremony definitions available in `config/ceremonies/`
- Kubernetes namespace `swe-ai-fleet` with proper secrets/configmaps

## Test Data

- Uses `e2e_multi_step.yaml` by default (configurable via `CEREMONY_NAME` env var)
- This ceremony includes:
  - **Deliberation step** (`deliberate`): Multi-agent deliberation with ARCHITECT, QA, and DEVOPS roles
  - **Task extraction step** (`extract_tasks`): Extracts tasks from deliberation results
  - **Publish step** (`publish_results`): Publishes ceremony completion event
- Generates unique `correlation_id` based on timestamp
- Creates ceremony instance via gRPC call
- Starts with `deliberate` step (first step in DELIBERATING state)

## Building

```bash
cd e2e/tests/11-planning-ceremony-processor-full-flow
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

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `PLANNING_CEREMONY_PROCESSOR_URL` | gRPC endpoint | No | `planning-ceremony-processor.swe-ai-fleet.svc.cluster.local:50057` |
| `NATS_URL` | NATS connection URL | No | `nats://nats.swe-ai-fleet.svc.cluster.local:4222` |
| `NEO4J_URI` | Neo4j bolt URI | No | `bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687` |
| `NEO4J_USER` | Neo4j username | No | From `neo4j-auth` secret |
| `NEO4J_PASSWORD` | Neo4j password | No | From `neo4j-auth` secret |
| `VALKEY_HOST` | Valkey hostname | No | `valkey.swe-ai-fleet.svc.cluster.local` |
| `VALKEY_PORT` | Valkey port | No | `6379` |
| `CEREMONY_NAME` | Ceremony definition name | No | `e2e_multi_step` |
| `CEREMONIES_DIR` | Path to ceremony YAML files | No | `/app/config/ceremonies` |

## Troubleshooting

### Test fails with "Connection refused" to planning_ceremony_processor

**Cause**: Service not deployed or not accessible.

**Solution**:
```bash
# Verify service is deployed
kubectl get svc -n swe-ai-fleet planning-ceremony-processor

# Verify pods are running
kubectl get pods -n swe-ai-fleet -l app=planning-ceremony-processor

# Check service logs
kubectl logs -n swe-ai-fleet -l app=planning-ceremony-processor
```

### Test fails with "Instance not found in Valkey"

**Cause**: Persistence adapter not saving to Valkey, or instance_id mismatch.

**Solution**:
- Verify `planning_ceremony_processor` is using `DualPersistenceAdapter` with Valkey configured
- Check test logs for actual `instance_id` generated
- Verify Valkey is accessible from test pod

### Test fails with "Instance not found in Neo4j"

**Cause**: Neo4j persistence failed or instance not created.

**Solution**:
- Verify Neo4j is accessible
- Check `planning_ceremony_processor` logs for Neo4j errors
- Verify `DualPersistenceAdapter` is configured with Neo4j

### Test fails with "Rehydration validation failed"

**Cause**: Instance definition doesn't match current definition.

**Solution**:
- Verify ceremony definition hasn't changed since instance was created
- Check test logs for specific validation errors
- Verify `RehydrationUseCase` is correctly validating definitions

### Test fails with "Consumer subscription not found"

**Cause**: Consumer subscription not created yet or stream doesn't exist.

**Solution**:
- This is a warning, not a failure - consumer will be created on first message
- Verify `AGENT_RESPONSES` stream exists
- Check `planning_ceremony_processor` logs for consumer initialization

## Related Tests

- `09-ceremony-engine-real-side-effects`: Basic ceremony execution side-effects
- `10-planning-ceremony-processor-grpc-start`: gRPC server startup validation

## References

- [Ceremony Engine Documentation](../../../../core/ceremony_engine/README.md)
- [E2E Test Procedure](../../../PROCEDURE.md)
