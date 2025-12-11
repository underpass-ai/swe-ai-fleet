# Backlog Review Flow E2E Test Data Cleanup

This Kubernetes Job cleans up test data created during Backlog Review Flow E2E tests.

## Overview

The cleanup job can operate in two modes:

1. **Specific Resource Cleanup**: Clean specific resources by ID (ceremony, story, epic, project)
2. **Bulk E2E Cleanup**: Clean all E2E test data matching common patterns

## Features

- **Ceremony Cancellation**: Cancels ceremonies via gRPC before deletion
- **Neo4j Cleanup**: Removes nodes and relationships from Neo4j
- **Valkey Cleanup**: Removes cached data from Valkey
- **Safe Operation**: Verifies existence before deletion
- **Pattern Matching**: Can clean all E2E test data by pattern

## Prerequisites

- Kubernetes cluster with services deployed
- Access to `swe-ai-fleet` namespace
- Docker/Podman for building images
- kubectl configured

## Building

```bash
# Build image locally
make build

# Build and push to registry
make build-push
```

## Deployment

### Initial Setup

```bash
# Deploy the base job (without running it)
make deploy
```

### Cleanup Specific Ceremony

```bash
# Cleanup a specific ceremony
make cleanup-ceremony CEREMONY_ID=BRC-12345

# Or manually set environment variable
kubectl set env job/backlog-review-flow-cleanup CLEANUP_CEREMONY_ID=BRC-12345 -n swe-ai-fleet
kubectl create job --from=job/backlog-review-flow-cleanup cleanup-ceremony-12345 -n swe-ai-fleet
```

### Cleanup All E2E Test Data

```bash
# Cleanup all E2E test data
make cleanup-all
```

### Manual Deployment

```bash
# Apply job manifest
kubectl apply -f jobs/backlog-review-flow-cleanup/job.yaml

# Create a job instance with specific cleanup target
kubectl create job cleanup-ceremony-12345 \
  --from=job/backlog-review-flow-cleanup \
  -n swe-ai-fleet

# Set environment variables
kubectl set env job/cleanup-ceremony-12345 \
  CLEANUP_CEREMONY_ID=BRC-12345 \
  -n swe-ai-fleet

# Watch job
kubectl get job -n swe-ai-fleet cleanup-ceremony-12345 -w

# View logs
kubectl logs -n swe-ai-fleet -l app=backlog-review-flow-cleanup -f
```

## Environment Variables

The job uses the following environment variables (set in `job.yaml` or via `kubectl set env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `PLANNING_SERVICE_URL` | Planning Service gRPC endpoint | `planning.swe-ai-fleet.svc.cluster.local:50054` |
| `NEO4J_URI` | Neo4j Bolt connection URI | `bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687` |
| `NEO4J_USERNAME` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | From secret `neo4j-auth` |
| `VALKEY_HOST` | Valkey host | `valkey.swe-ai-fleet.svc.cluster.local` |
| `VALKEY_PORT` | Valkey port | `6379` |
| `CLEANUP_CEREMONY_ID` | Ceremony ID to clean | - |
| `CLEANUP_STORY_ID` | Story ID to clean | - |
| `CLEANUP_EPIC_ID` | Epic ID to clean | - |
| `CLEANUP_PROJECT_ID` | Project ID to clean | - |
| `CLEANUP_ALL_E2E` | Clean all E2E test data (`"true"` or `"false"`) | `"false"` |
| `CLEANUP_CANCELLED_BY` | User cancelling ceremonies | `e2e-cleanup@system.local` |

## Cleanup Patterns

When `CLEANUP_ALL_E2E=true`, the job cleans data matching these patterns:

### Neo4j Patterns
- **Ceremonies**: `BRC-*` or `BRC-TEST-*`
- **Stories**: `STORY-E2E-*` or `s-E2E-*`
- **Epics**: `E-E2E-*` or title contains `E2E Test Epic`
- **Projects**: `PROJECT-E2E-*` or name contains `E2E Test Project`

### Valkey Patterns
- `ceremony:BRC-*`
- `ceremony:BRC-TEST-*`
- `story:STORY-E2E-*`
- `story:s-E2E-*`
- `epic:E-E2E-*`
- `project:PROJECT-E2E-*`

## Usage Examples

### Example 1: Cleanup Specific Ceremony

```bash
# Set ceremony ID
export CEREMONY_ID=BRC-abc123

# Create cleanup job
kubectl create job cleanup-$$(echo $CEREMONY_ID | tr '[:upper:]' '[:lower:]') \
  --from=job/backlog-review-flow-cleanup \
  -n swe-ai-fleet

# Set environment variable
kubectl set env job/cleanup-$$(echo $CEREMONY_ID | tr '[:upper:]' '[:lower:]') \
  CLEANUP_CEREMONY_ID=$CEREMONY_ID \
  -n swe-ai-fleet

# View logs
kubectl logs -n swe-ai-fleet -l app=backlog-review-flow-cleanup -f
```

### Example 2: Cleanup All E2E Test Data

```bash
# Create cleanup job for all E2E data
kubectl create job cleanup-all-e2e-$$(date +%s) \
  --from=job/backlog-review-flow-cleanup \
  -n swe-ai-fleet

# Set environment variable
kubectl set env job/cleanup-all-e2e-$$(date +%s) \
  CLEANUP_ALL_E2E=true \
  -n swe-ai-fleet
```

### Example 3: Cleanup After E2E Test

```bash
# After running E2E test, get ceremony ID from logs
CEREMONY_ID=$(kubectl logs -n swe-ai-fleet -l app=backlog-review-flow-e2e | grep "Ceremony created:" | tail -1 | awk '{print $3}')

# Cleanup the ceremony
make cleanup-ceremony CEREMONY_ID=$CEREMONY_ID
```

## Troubleshooting

### Job Fails to Start

```bash
# Check job events
kubectl describe job -n swe-ai-fleet backlog-review-flow-cleanup

# Check pod events
kubectl get pods -n swe-ai-fleet -l app=backlog-review-flow-cleanup
kubectl describe pod -n swe-ai-fleet -l app=backlog-review-flow-cleanup
```

### Service Connection Issues

```bash
# Verify services are running
kubectl get svc -n swe-ai-fleet

# Check Planning Service
kubectl logs -n swe-ai-fleet -l app=planning --tail=50

# Verify Neo4j
kubectl exec -it -n swe-ai-fleet statefulset/neo4j -- cypher-shell -u neo4j -p testpassword "MATCH (n) RETURN count(n);"

# Verify Valkey
kubectl exec -it -n swe-ai-fleet statefulset/valkey -- redis-cli ping
```

### Data Not Deleted

```bash
# Check Neo4j directly
kubectl exec -it -n swe-ai-fleet statefulset/neo4j -- cypher-shell -u neo4j -p testpassword \
  "MATCH (c:BacklogReviewCeremony {id: 'BRC-12345'}) RETURN c"

# Check Valkey
kubectl exec -it -n swe-ai-fleet statefulset/valkey -- redis-cli GET "ceremony:BRC-12345"
```

## Cleanup

```bash
# Delete cleanup jobs
make clean

# Delete main job
make delete
```

## Safety

- The cleanup job **only** deletes data matching E2E test patterns
- Specific resource cleanup requires explicit IDs
- Ceremonies are cancelled via gRPC before deletion (proper state transition)
- All operations are logged for audit

## Integration with CI/CD

You can integrate cleanup into your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run E2E Test
  run: |
    make -C jobs/backlog-review-flow-e2e deploy
    # Wait for completion and get ceremony ID

- name: Cleanup Test Data
  if: always()
  run: |
    make -C jobs/backlog-review-flow-cleanup cleanup-all
```




