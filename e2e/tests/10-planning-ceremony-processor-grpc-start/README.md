# E2E Test: Planning Ceremony Processor gRPC Start Validation

This E2E test validates that the `planning_ceremony_processor` gRPC server starts correctly and is accessible.

## Overview

This test verifies:
- **gRPC server is accessible** via Kubernetes internal DNS
- **gRPC channel connects** successfully
- **StartPlanningCeremony accepts a valid request** and returns `instance_id`
- **GetPlanningCeremonyInstance returns valid response format**

Unlike unit tests that mock the gRPC server, this test connects to the actual deployed service and validates real gRPC communication.

## Test Flow

1. **Connect to gRPC server**: Establishes connection to `planning-ceremony-processor:50057`
2. **Verify server accessible**: Calls `StartPlanningCeremony` with required fields:
   - `ceremony_id`
   - `definition_name`
   - `story_id`
   - `step_ids`
   - `requested_by`
   - required `inputs` for the selected definition
3. **Verify response format**: Calls `GetPlanningCeremonyInstance` and validates required fields

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
| `CEREMONY_NAME` | Ceremony definition name (`definition_name`) | No | `dummy_ceremony` |
| `CEREMONY_ID` | Ceremony identifier (`ceremony_id`) | No | `e2e-ceremony-<uuid>` |
| `STORY_ID` | Story identifier (`story_id`) | No | `e2e-story-<uuid>` |
| `CEREMONY_STEP_IDS` | Comma-separated step IDs | No | `process_step` |
| `CEREMONY_INPUT_DATA` | Value for required `input_data` | No | `e2e-input` |
| `REQUESTED_BY` | Caller identity (`requested_by`) | No | `e2e-planning-ceremony-processor-grpc-start` |

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

### Test fails with "INVALID_ARGUMENT - definition_name cannot be empty"

**Cause**: Request is missing required fields for `StartPlanningCeremony`.

**Solution**:
- Ensure the test image includes latest script version
- Verify env configuration (`CEREMONY_NAME`, `CEREMONY_STEP_IDS`, `REQUESTED_BY`)

## Related Tests

- `09-ceremony-engine-real-side-effects`: Validates side-effects after ceremony start
- `08-ceremony-engine-e2e`: Basic ceremony execution (uses mocks)

## References

- [Planning Ceremony Processor README](../../../../services/planning_ceremony_processor/README.md)
- [E2E Test Procedure](../../../PROCEDURE.md)
