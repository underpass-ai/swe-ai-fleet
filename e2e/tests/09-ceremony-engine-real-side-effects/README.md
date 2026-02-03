# E2E Test: Ceremony Engine Real Side-Effects Validation

This E2E test validates that ceremony engine operations produce real side-effects in the deployed Kubernetes environment.

## Overview

This test verifies that when a ceremony is executed:
- **NATS messages** are published to real NATS JetStream
- **Persistence updates** are written to real Valkey and Neo4j
- **External service calls** (Ray Executor via gRPC) are triggered

Unlike unit tests that use mocks, this test connects to actual services deployed in Kubernetes and validates real side-effects.

## Test Flow

1. **Start ceremony via gRPC**: Calls `planning_ceremony_processor` gRPC service to start a ceremony
2. **Verify NATS messages**: Subscribes to NATS JetStream and verifies `ceremony.step.executed` messages are published
3. **Verify Valkey persistence**: Queries Valkey to verify the ceremony instance was persisted
4. **Verify Neo4j persistence**: Queries Neo4j to verify the ceremony instance node was created

## Prerequisites

- `planning_ceremony_processor` service deployed and running
- NATS JetStream available and accessible
- Valkey (Redis-compatible) available and accessible
- Neo4j available and accessible
- Ceremony definitions available in `config/ceremonies/`
- Kubernetes namespace `swe-ai-fleet` with proper secrets/configmaps

## Test Data

- Uses `dummy_ceremony.yaml` by default (configurable via `CEREMONY_NAME` env var)
- Generates unique `correlation_id` based on timestamp
- Creates ceremony instance via gRPC call

## Building

```bash
cd e2e/tests/09-ceremony-engine-real-side-effects
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
| `CEREMONY_NAME` | Ceremony definition name | No | `dummy_ceremony` |
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

### Test fails with "No NATS messages found"

**Cause**: Messages published asynchronously or ceremony didn't execute steps.

**Solution**:
- Increase wait time in test (currently 2 seconds)
- Verify ceremony definition has steps that publish events
- Check NATS JetStream streams exist

## Related Tests

- `08-ceremony-engine-e2e`: Basic ceremony execution (uses mocks)
- `04-start-backlog-review-ceremony`: Backlog review ceremony E2E

## References

- [Ceremony Engine Documentation](../../../../core/ceremony_engine/README.md)
- [E2E Test Procedure](../../../PROCEDURE.md)
