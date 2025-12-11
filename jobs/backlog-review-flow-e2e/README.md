# Backlog Review Flow E2E Test

This Kubernetes Job runs an end-to-end test for the complete Backlog Review Flow as described in `docs/architecture/BACKLOG_REVIEW_FLOW_NO_STYLES.md`.

## Overview

The test verifies the complete flow from ceremony creation through task generation:

1. **Create Backlog Review Ceremony** - Creates a ceremony with test story
2. **Verify Persistence** - Confirms ceremony is saved in Neo4j and Valkey
3. **Start Ceremony** - Initiates the review process
4. **Wait for Deliberations** - Monitors for completion of all role deliberations
5. **Verify Tasks Created** - Confirms tasks were extracted and saved

## Features

- **Kubernetes Logs Integration**: Automatically retrieves and displays logs from relevant services during test execution
- **Real Service Verification**: Uses actual gRPC services, Neo4j, and Valkey
- **Automatic Status Monitoring**: Polls ceremony status and shows progress
- **Debug-Friendly**: Shows service logs when waiting for async operations

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

```bash
# Deploy the job
make deploy

# Watch job status
make status

# View logs in real-time
make logs
```

## Manual Deployment

```bash
# Apply job manifest
kubectl apply -f jobs/backlog-review-flow-e2e/job.yaml

# Watch job
kubectl get job -n swe-ai-fleet backlog-review-flow-e2e -w

# View logs
kubectl logs -n swe-ai-fleet -l app=backlog-review-flow-e2e -f
```

## Prerequisites

The test can work in two modes:

### Mode 1: Use Existing Story (Recommended for CI/CD)
1. **Have an existing Story ID** in the system
2. **Set `TEST_STORY_ID`** environment variable to that story ID
3. The story must exist in Neo4j and be accessible via Planning Service

### Mode 2: Create New Hierarchy (Default)
1. Leave `TEST_STORY_ID` empty (or unset)
2. The test will automatically create:
   - A new Project
   - A new Epic within the project
   - A new Story within the epic
3. Then proceed with the backlog review flow test

## Environment Variables

The job uses the following environment variables (set in `job.yaml`):

| Variable | Description | Default |
|----------|-------------|---------|
| `PLANNING_SERVICE_URL` | Planning Service gRPC endpoint | `planning.swe-ai-fleet.svc.cluster.local:50054` |
| `CONTEXT_SERVICE_URL` | Context Service gRPC endpoint | `context.swe-ai-fleet.svc.cluster.local:50054` |
| `RAY_EXECUTOR_URL` | Ray Executor gRPC endpoint | `ray-executor.swe-ai-fleet.svc.cluster.local:50056` |
| `NEO4J_URI` | Neo4j Bolt connection URI | `bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687` |
| `NEO4J_USERNAME` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | From secret `neo4j-auth` |
| `VALKEY_HOST` | Valkey host | `valkey.swe-ai-fleet.svc.cluster.local` |
| `VALKEY_PORT` | Valkey port | `6379` |
| `KUBERNETES_NAMESPACE` | Namespace for log access | `swe-ai-fleet` |
| `TEST_STORY_ID` | Story ID for test (optional - if empty, creates new hierarchy) | - |
| `TEST_PROJECT_NAME` | Project name (optional - auto-generated if empty) | Auto-generated |
| `TEST_EPIC_TITLE` | Epic title (optional - auto-generated if empty) | Auto-generated |
| `TEST_STORY_TITLE` | Story title (optional - auto-generated if empty) | Auto-generated |
| `TEST_STORY_BRIEF` | Story description (optional - has default if empty) | Default description |
| `TEST_PROJECT_ID` | Project ID for test | `PROJECT-E2E-001` |
| `TEST_CREATED_BY` | User creating the ceremony | `e2e-test@system.local` |

## Service Logs

The test automatically retrieves and displays logs from relevant services:

- **Planning Service**: Shows ceremony creation and status updates
- **Backlog Review Processor**: Shows deliberation processing and task extraction
- **Context Service**: Shows deliberation and task persistence
- **Ray Executor**: Shows job submission and execution

Logs are displayed:
- Periodically during wait operations (every 60 seconds)
- When operations complete successfully
- When timeouts occur (for debugging)

## RBAC Requirements

The job requires a ServiceAccount with permissions to:
- List pods in the namespace
- Read pod logs

These are configured in `job.yaml` via:
- ServiceAccount: `e2e-test-runner`
- Role: `e2e-test-runner` (pods, pods/log)
- RoleBinding: `e2e-test-runner`

## Troubleshooting

### Job Fails to Start

```bash
# Check job events
kubectl describe job -n swe-ai-fleet backlog-review-flow-e2e

# Check pod events
kubectl get pods -n swe-ai-fleet -l app=backlog-review-flow-e2e
kubectl describe pod -n swe-ai-fleet -l app=backlog-review-flow-e2e
```

### Service Connection Issues

```bash
# Verify services are running
kubectl get svc -n swe-ai-fleet

# Check Planning Service
kubectl logs -n swe-ai-fleet -l app=planning --tail=50

# Check Backlog Review Processor
kubectl logs -n swe-ai-fleet -l app=backlog-review-processor --tail=50
```

### Permission Issues

```bash
# Verify ServiceAccount exists
kubectl get serviceaccount -n swe-ai-fleet e2e-test-runner

# Verify Role and RoleBinding
kubectl get role -n swe-ai-fleet e2e-test-runner
kubectl get rolebinding -n swe-ai-fleet e2e-test-runner
```

### Test Timeout

The test has a default timeout of 300 seconds (5 minutes) for each async operation. If the test times out:

1. Check service logs (automatically displayed)
2. Verify all services are healthy
3. Check NATS connectivity
4. Verify Ray cluster is operational

## Cleanup

```bash
# Delete job (keeps ServiceAccount, Role, RoleBinding)
make clean

# Delete everything
make delete
```

## Test Output

The test provides colored output showing:
- ✓ Success messages (green)
- ✗ Error messages (red)
- ⚠ Warning messages (yellow)
- ℹ Info messages (yellow)
- Step headers (blue)

Example output:
```
================================================================================
Step 1: Create Backlog Review Ceremony
================================================================================

✓ Ceremony created: BRC-TEST-1234567890
ℹ Status: DRAFT
ℹ Stories: ['STORY-E2E-1234567890']
```

## Architecture

The test follows Hexagonal Architecture principles:
- **Ports**: gRPC stubs for service communication
- **Adapters**: Kubernetes client for log access
- **Domain Logic**: Test flow orchestration

No mocks are used - the test interacts with real services in the Kubernetes cluster.




