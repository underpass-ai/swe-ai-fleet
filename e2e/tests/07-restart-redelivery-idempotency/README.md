# E2E Test: Restart & Redelivery Idempotency (B0.5)

This test validates idempotency during restart and redelivery scenarios.

## Test Purpose

Validates that duplicate message processing does not create duplicate tasks:
- **Duplicate publish**: Same event published twice with same `idempotency_key`
- **Restart simulation**: Event redelivered after BRP restart
- **Assertion**: 0 duplicate tasks created

## Test Scenarios

### Scenario 1: Duplicate Publish
1. Publish `agent.response.completed.task-extraction` event with **EventEnvelope** (event_type, payload, idempotency_key, correlation_id, etc.) and task extraction results
2. Wait for tasks to be created in Planning Service
3. Publish the same event again (same `idempotency_key`)
4. Verify no duplicate tasks are created

### Scenario 2: Restart Simulation
- Same as Scenario 1, but simulates BRP restart by:
  - Using same `idempotency_key` (idempotency state persists in Valkey)
  - Using different `correlation_id` (simulates redelivery)

## Prerequisites

- Planning Service deployed
- Backlog Review Processor deployed
- NATS JetStream accessible
- Valkey accessible (for idempotency state)
- **Test data:** When `TEST_STORY_ID` is the placeholder `ST-001`, the test **discovers** a story from Planning using `TEST_PROJECT_NAME` and `TEST_EPIC_TITLE` (same as test 05/06). So **run test 02 (create-test-data) before test 07** in the pipeline; the test will find the first story in that project/epic. You can still set `TEST_STORY_ID` and `TEST_CEREMONY_ID` to override (e.g. for standalone runs).

## Usage

### Build and Deploy

**Important:** When you run the E2E suite with `--skip-build` (`./run-e2e-tests.sh --skip-build`), the runner does **not** rebuild images. The Job is still deployed (and pods pull the image from the registry); the cluster uses whatever image is already built/pushed. To run the discovery fix (story/ceremony discovery), either:

1. **Rebuild and push test 07 from the project root**, then run the suite with `--skip-build`:
   ```bash
   make e2e-build-push-test TEST=07-restart-redelivery-idempotency
   ./e2e/run-e2e-tests.sh --skip-build
   ```
2. Or run the full suite **without** `--skip-build` once so all images (including 07) are built and pushed before deploy.

```bash
# From test directory: build image
make build

# Push to registry
make push

# Deploy job
make deploy

# Check status
make status

# View logs
make logs

# Delete job
make delete
```

### Environment Variables

- `PLANNING_SERVICE_URL`: Planning Service gRPC URL (default: `planning.swe-ai-fleet.svc.cluster.local:50054`)
- `NATS_URL`: NATS URL (default: `nats://nats.swe-ai-fleet.svc.cluster.local:4222`)
- **Discovery (same as test 05/06):** `TEST_PROJECT_NAME` (default: `Test de swe fleet`), `TEST_EPIC_TITLE` (default: `Autenticacion`), `TEST_CREATED_BY` (default: `e2e-test@system.local`). When `TEST_STORY_ID` is the placeholder `ST-001`, the test discovers the first story in that project/epic.
- **Overrides:** `TEST_STORY_ID` (default: `ST-001` — triggers discovery when left as-is), `TEST_CEREMONY_ID` (default: `BRC-TEST-001` — test discovers a ceremony containing the story or uses a synthetic ID).
- `TASK_TIMEOUT`: Timeout for task creation (default: `120` seconds)
- `POLL_INTERVAL`: Polling interval (default: `5` seconds)

## Test Flow

1. **Setup**: Connect to Planning Service and NATS
2. **Discovery** (when placeholders): If `TEST_STORY_ID` is `ST-001`, discover first story from project/epic; optionally discover a ceremony containing that story, or use synthetic ceremony ID.
3. **Initial State**: Get current task count for test story
4. **First Publish**: Publish event with task extraction results
5. **Wait**: Wait for tasks to be created (verify processing)
6. **Duplicate Publish**: Publish same event again (same `idempotency_key`)
7. **Validate**: Verify task count hasn't increased (no duplicates)

## Expected Results

- ✅ First publish creates expected tasks
- ✅ Duplicate publish creates 0 additional tasks
- ✅ Idempotency prevents duplicate processing

## Event format (contract)

Events must comply with **EventEnvelope** and **canonical task extraction payload** (TaskExtractionResultConsumer):

**Subject:** `agent.response.completed.task-extraction`

**Envelope (top-level):** `event_type`, `payload`, `idempotency_key`, `correlation_id`, `timestamp`, `producer`, `metadata`

**Payload (inner):**
- `task_id` (str, required)
- `story_id` (str, required)
- `ceremony_id` (str, required)
- `tasks` (list, required) — each item: `title` (str, required), `description`, `estimated_hours`, `deliberation_indices` (list)

The test asserts these required keys before publishing so that contract violations fail fast.

## Failure Modes

- ❌ Duplicate publish creates additional tasks → **IDEMPOTENCY VIOLATION**
- ❌ Tasks not created after first publish → **Processing failure** (check envelope format and subject)
- ❌ Timeout waiting for tasks → **Service unavailable or slow**

## Related Stories

- **B0.2**: IdempotencyPort (Valkey) + middleware
- **B0.3**: Planning gRPC command idempotency
- **B0.4.1**: TaskExtractionResultConsumer idempotent

## Architecture

The test validates the complete idempotency chain:
1. **Event Level**: `idempotency_key` in EventEnvelope prevents reprocessing
2. **Command Level**: `request_id` in Planning Service prevents duplicate task creation
3. **State Persistence**: Valkey stores idempotency state across restarts
