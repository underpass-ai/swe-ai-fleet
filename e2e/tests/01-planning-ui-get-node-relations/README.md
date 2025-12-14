# E2E Test: Planning UI → Get Node Relations

This E2E test verifies that Planning UI can successfully call Context Service's `GetGraphRelationships` gRPC method to retrieve node relationships from Neo4j.

## Overview

The test simulates the flow:
1. **Planning UI** receives a request for node relationships
2. **Planning UI** calls **Context Service** `GetGraphRelationships` via gRPC
3. **Context Service** queries Neo4j for the node and its relationships
4. **Context Service** returns graph relationships to Planning UI

## Prerequisites

- Kubernetes cluster with services deployed
- Context Service deployed and accessible at `context.swe-ai-fleet.svc.cluster.local:50054`
- Neo4j deployed and accessible
- A valid node ID in Neo4j (project_id, epic_id, story_id, or task_id)
- Docker/Podman for building images
- kubectl configured

## Test Data

The test requires a valid node ID in Neo4j. You can:

1. **Use an existing node ID**: Set `TEST_NODE_ID` environment variable
2. **Create test data**: Use Planning Service to create a Project → Epic → Story → Task hierarchy

### Finding a Node ID

You can query Neo4j to find existing nodes:

```cypher
# Find a project
MATCH (p:Project) RETURN p.id LIMIT 1

# Find a story
MATCH (s:Story) RETURN s.id LIMIT 1

# Find a task
MATCH (t:Task) RETURN t.id LIMIT 1
```

## Building

```bash
# Build image locally
make build

# Build and push to registry
make build-push
```

## Deployment

### Option 1: Using Makefile

```bash
# Deploy the job
make deploy

# Watch job status
make status

# View logs in real-time
make logs

# Delete job when done
make delete
```

### Option 2: Manual Deployment

1. **Edit job.yaml** to set `TEST_NODE_ID`:

```yaml
env:
  - name: TEST_NODE_ID
    value: "story-123"  # Set your node ID here
```

2. **Deploy the job**:

```bash
kubectl apply -f e2e/tests/01-planning-ui-get-node-relations/job.yaml
```

3. **Watch job progress**:

```bash
kubectl get job -n swe-ai-fleet e2e-planning-ui-get-node-relations -w
```

4. **View logs**:

```bash
kubectl logs -n swe-ai-fleet -l app=e2e-planning-ui-get-node-relations -f
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `CONTEXT_SERVICE_URL` | Context Service gRPC endpoint | No | `context.swe-ai-fleet.svc.cluster.local:50054` |
| `TEST_NODE_ID` | Node ID to test (project_id, epic_id, story_id, or task_id) | **Yes** | - |
| `TEST_NODE_TYPE` | Node type (Project, Epic, Story, Task) | No | `Story` |
| `TEST_DEPTH` | Traversal depth (1-3) | No | `2` |

## Test Verification

The test verifies:

- ✅ gRPC call succeeds
- ✅ Response contains node data
- ✅ Response contains neighbors (if any)
- ✅ Response contains relationships (if any)
- ✅ All relationships connect to existing nodes
- ✅ Response structure is valid

## Expected Output

On success:

```
🚀 Planning UI → Get Node Relations E2E Test
================================================================================

Configuration:
  Context Service: context.swe-ai-fleet.svc.cluster.local:50054

Test Data:
  Node ID:   story-123
  Node Type: Story
  Depth:     2

Step 1: Planning UI calls GetGraphRelationships
================================================================================

✓ GetGraphRelationships call succeeded
✓ Node found: story-123
  Type:  Story
  Title: My Test Story
  Labels: Story, Entity
✓ Found 3 neighbor node(s)
✓ Found 5 relationship(s)
✓ All relationships connect to existing nodes

================================================================================
✅ E2E test PASSED
================================================================================
```

## Troubleshooting

### Job Failed

```bash
# Check job status
kubectl describe job -n swe-ai-fleet e2e-planning-ui-get-node-relations

# Check pod logs
kubectl logs -n swe-ai-fleet -l app=e2e-planning-ui-get-node-relations

# Check pod events
kubectl describe pod -n swe-ai-fleet -l app=e2e-planning-ui-get-node-relations
```

### Node Not Found

If you see `Node not found in Neo4j`:

1. Verify the node ID exists in Neo4j
2. Check that the node type matches `TEST_NODE_TYPE`
3. Ensure Neo4j is accessible from the test pod

### Service Connection Issues

```bash
# Verify Context Service is running
kubectl get svc -n swe-ai-fleet context

# Check Context Service logs
kubectl logs -n swe-ai-fleet -l app=context --tail=50

# Test gRPC connectivity from a pod
kubectl run -it --rm debug --image=grpcurl/grpcurl --restart=Never -- \
  -plaintext context.swe-ai-fleet.svc.cluster.local:50054 list
```

### Image Pull Errors

```bash
# Verify image exists in registry
podman images | grep e2e-planning-ui-get-node-relations

# Rebuild and push
make build-push
```

## Local Development

To run the test locally (requires services accessible via localhost):

```bash
# Set required environment variables
export TEST_NODE_ID=story-123
export TEST_NODE_TYPE=Story
export TEST_DEPTH=2

# Run test
make run-local TEST_NODE_ID=story-123
```

Or using Docker/Podman directly:

```bash
podman run --rm \
  --network host \
  -e CONTEXT_SERVICE_URL=localhost:50054 \
  -e TEST_NODE_ID=story-123 \
  -e TEST_NODE_TYPE=Story \
  -e TEST_DEPTH=2 \
  registry.underpassai.com/swe-ai-fleet/e2e-planning-ui-get-node-relations:v1.0.0
```

## Related Documentation

- [E2E Test Procedure Guide](../../PROCEDURE.md) - Detailed guide for creating new E2E tests
- [Backlog Review Flow](../../../services/backlog_review_processor/BACKLOG_REVIEW_FLOW_NO_STYLES.md) - Architecture flow diagram

