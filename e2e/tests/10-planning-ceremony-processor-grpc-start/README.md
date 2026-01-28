# E2E Test: Planning Ceremony Processor gRPC Start Validation

This E2E test validates that the `planning_ceremony_processor` gRPC server starts correctly and is accessible.

## Overview

This test verifies:
- **gRPC server is accessible** via Kubernetes internal DNS
- **gRPC channel connects** successfully
- **gRPC methods respond** correctly (StartPlanningCeremony)
- **Response format** is valid (contains instance_id)

Unlike unit tests that mock the gRPC server, this test connects to the actual deployed service and validates real gRPC communication.

## Test Flow

1. **Connect to gRPC server**: Establishes connection to `planning-ceremony-processor:50057`
2. **Verify server accessible**: Calls `StartPlanningCeremony` and verifies response
3. **Verify response format**: Validates response contains required fields (instance_id)

## Prerequisites

- `planning_ceremony_processor` service deployed and running
- gRPC server listening on port 50057
- Ceremony definitions available in `config/ceremonies/`
- Kubernetes namespace `swe-ai-fleet` with proper DNS

## Test Data

- Uses `dummy_ceremony.yaml` by default (configurable via `CEREMONY_NAME` env var)
- Generates unique `correlation_id` based on timestamp

## Building

```bash
cd e2e/tests/10-planning-ceremony-processor-grpc-start
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
| `CEREMONY_NAME` | Ceremony definition name | No | `dummy_ceremony` |

## Troubleshooting

### Test fails with "gRPC server unavailable"

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

### Test fails with "gRPC channel not ready within timeout"

**Cause**: Service is starting up or network issues.

**Solution**:
- Wait for service to be fully ready (check readiness probe)
- Verify DNS resolution: `kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup planning-ceremony-processor.swe-ai-fleet.svc.cluster.local`
- Check service endpoints: `kubectl get endpoints -n swe-ai-fleet planning-ceremony-processor`

### Test fails with "Response missing instance_id"

**Cause**: Service error or invalid ceremony definition.

**Solution**:
- Check service logs for errors
- Verify ceremony definition exists: `kubectl exec -it -n swe-ai-fleet deployment/planning-ceremony-processor -- ls /app/config/ceremonies/`
- Verify ceremony YAML is valid

## Related Tests

- `09-ceremony-engine-real-side-effects`: Validates side-effects after ceremony start
- `08-ceremony-engine-e2e`: Basic ceremony execution (uses mocks)

## References

- [Planning Ceremony Processor README](../../../../services/planning_ceremony_processor/README.md)
- [E2E Test Procedure](../../../PROCEDURE.md)
