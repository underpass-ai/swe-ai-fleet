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
- **Test story must exist in Planning Service:** the story identified by `TEST_STORY_ID` (default `ST-001`) must exist. The test checks this before publishing and fails fast with a clear message if missing. **Run test 02 (create-test-data) before test 07** to create stories, or set `TEST_STORY_ID` to an existing story ID.

## Usage

### Build and Deploy

```bash
# Build image
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
- `TEST_STORY_ID`: Story ID to use for testing (default: `ST-001`)
- `TEST_CEREMONY_ID`: Ceremony ID to use for testing (default: `BRC-TEST-001`)
- `TASK_TIMEOUT`: Timeout for task creation (default: `120` seconds)
- `POLL_INTERVAL`: Polling interval (default: `5` seconds)

## Test Flow

1. **Setup**: Connect to Planning Service and NATS
2. **Initial State**: Get current task count for test story
3. **First Publish**: Publish event with task extraction results
4. **Wait**: Wait for tasks to be created (verify processing)
5. **Duplicate Publish**: Publish same event again (same `idempotency_key`)
6. **Validate**: Verify task count hasn't increased (no duplicates)

## Expected Results

- ✅ First publish creates expected tasks
- ✅ Duplicate publish creates 0 additional tasks
- ✅ Idempotency prevents duplicate processing

## Event format

Events must use **EventEnvelope** (required by Backlog Review Processor consumers):
- `event_type`, `payload`, `idempotency_key`, `correlation_id`, `timestamp`, `producer`, `metadata`
- Subject: `agent.response.completed.task-extraction` (TaskExtractionResultConsumer subscription)

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
