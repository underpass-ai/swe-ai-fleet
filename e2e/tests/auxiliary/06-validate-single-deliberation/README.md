# E2E Test: Validate Single Deliberation

This test validates that a single deliberation can be executed and processed correctly with the reasoning parser.

## Purpose

This test verifies:
1. A single deliberation can be submitted to Ray Executor
2. vLLM processes the deliberation with reasoning parser
3. Content is clean (no `<think>` tags)
4. Reasoning is separated (if available)
5. Deliberation result is published to NATS
6. BRP processes the deliberation
7. Planning Service stores the deliberation correctly

## Flow Verified

```
Ray Executor → vLLM → NATS → BRP → Planning Service
```

## Prerequisites

- Planning Service must be deployed
- Backlog Review Processor must be deployed
- Ray Executor Service must be deployed
- vLLM Service must be accessible (with reasoning parser configured)
- NATS must be accessible
- Test data must exist (run `02-create-test-data` first)

## Usage

### Build and Push Image

```bash
make build-push
```

### Deploy Test Job

```bash
make deploy
```

### Check Status

```bash
make status
```

### View Logs

```bash
make logs
```

### Delete Job

```bash
make delete
```

## Test Steps

1. **Find Test Data**: Locates project, epic, and story from test data
2. **Create Ceremony**: Creates a backlog review ceremony and adds the story
3. **Submit Deliberation**: Submits a single ARCHITECT deliberation to Ray Executor
4. **Wait for Completion**: Polls Ray Executor until deliberation completes
5. **Verify Result**: Validates that:
   - Content is clean (no `<think>` tags)
   - Reasoning is separated (if available)
   - Proposal is valid and non-empty
6. **Verify in Planning Service**: Checks that deliberation was processed by BRP and stored in Planning Service

## Environment Variables

- `PLANNING_SERVICE_URL`: Planning Service gRPC endpoint (default: `planning.swe-ai-fleet.svc.cluster.local:50054`)
- `RAY_EXECUTOR_SERVICE_URL`: Ray Executor Service gRPC endpoint (default: `ray-executor.swe-ai-fleet.svc.cluster.local:50051`)
- `VLLM_URL`: vLLM service URL (default: `http://vllm-server-service.swe-ai-fleet.svc.cluster.local:8000`)
- `VLLM_MODEL`: vLLM model name (default: `Qwen/Qwen3-0.6B`)
- `TEST_PROJECT_NAME`: Test project name (default: `Test de swe fleet`)
- `TEST_EPIC_TITLE`: Test epic title (default: `Autenticacion`)
- `DELIBERATION_TIMEOUT`: Timeout for deliberation completion in seconds (default: `300`)
- `POLL_INTERVAL`: Polling interval in seconds (default: `5`)

## Expected Results

- ✅ Deliberation submitted successfully
- ✅ Deliberation completed within timeout
- ✅ Content is clean (no `<think>` tags)
- ✅ Reasoning is separated (if reasoning parser is configured)
- ✅ Deliberation stored in Planning Service

## Troubleshooting

### Deliberation Not Completing

- Check Ray Executor logs: `kubectl logs -n swe-ai-fleet -l app=ray-executor`
- Check vLLM logs: `kubectl logs -n swe-ai-fleet -l app=vllm-server`
- Verify vLLM is accessible and reasoning parser is configured

### Content Contains `<think>` Tags

- Verify vLLM server has `--reasoning-parser qwen3` configured
- Check vLLM server logs for reasoning parser errors
- The fallback in `vllm_http_client.py` should clean the content, but this indicates the reasoning parser may not be working

### Deliberation Not Found in Planning Service

- Check BRP logs: `kubectl logs -n swe-ai-fleet -l app=backlog-review-processor`
- Verify NATS connectivity
- Check Planning Service logs: `kubectl logs -n swe-ai-fleet -l app=planning`
- The test allows this to be a warning (may need more time for processing)
