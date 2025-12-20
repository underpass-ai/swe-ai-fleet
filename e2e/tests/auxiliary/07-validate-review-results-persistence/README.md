# E2E Test: Validate Review Results Persistence

## Purpose

This E2E test validates that review results are correctly persisted in Planning Service after agent deliberations are processed by the Backlog Review Processor.

## Flow Validated

1. **Ceremony Creation**: Creates a new backlog review ceremony with test stories
2. **Deliberation Processing**: Waits for deliberations from all 3 roles (ARCHITECT, QA, DEVOPS) for each story
3. **Review Results Persistence**: Verifies that Planning Service receives `AddAgentDeliberation` calls from BRP
4. **Review Results Verification**: Verifies that review results appear in the ceremony with all 3 roles
5. **Status Transition**: Verifies that ceremony transitions to `REVIEWING` when all stories have complete review results

## Architecture Flow

```
Ray Executor → vLLM → NATS (agent.response.completed)
                    ↓
            Backlog Review Processor
                    ↓
         AddAgentDeliberation gRPC call
                    ↓
            Planning Service
                    ↓
        Review Results persisted in ceremony
                    ↓
    DeliberationsCompleteProgressConsumer
                    ↓
    Ceremony status → REVIEWING
```

## Prerequisites

- Planning Service must be deployed
- Backlog Review Processor must be deployed
- Ray Executor Service must be deployed
- vLLM Service must be accessible
- NATS must be accessible
- Test data must exist (run `02-create-test-data` first)

## Usage

### Build and Deploy

```bash
cd e2e/tests/07-validate-review-results-persistence
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

### View Last Logs (no follow)

```bash
make logs-last
```

### Delete Job

```bash
make delete
```

## Environment Variables

- `PLANNING_SERVICE_URL`: Planning Service gRPC endpoint (default: `planning.swe-ai-fleet.svc.cluster.local:50054`)
- `TEST_CREATED_BY`: User creating the ceremony (default: `e2e-test@system.local`)
- `TEST_PROJECT_NAME`: Project name to use (default: `Test de swe fleet`)
- `TEST_EPIC_TITLE`: Epic title to use (default: `Autenticacion`)
- `REVIEW_RESULTS_TIMEOUT`: Timeout for waiting for review results in seconds (default: `600`)
- `POLL_INTERVAL`: Interval between status polls in seconds (default: `10`)

## Test Steps

1. **Find Test Data**: Locates project, epic, and stories from test data
2. **Create Ceremony**: Creates a new backlog review ceremony and adds stories
3. **Wait for Review Results**: Polls ceremony status until review results appear
4. **Verify Review Results Complete**: Verifies that all stories have review results from all 3 roles
5. **Verify Status REVIEWING**: Verifies that ceremony status is `REVIEWING`

## Expected Results

- ✅ Ceremony created successfully
- ✅ Review results appear in ceremony (at least 1 story with all 3 roles)
- ✅ All stories have complete review results (ARCHITECT, QA, DEVOPS)
- ✅ Ceremony status transitions to `REVIEWING` when all stories are complete

## Troubleshooting

### Review Results Not Appearing

- Check BRP logs for `AddAgentDeliberation` calls
- Check Planning Service logs for `AddAgentDeliberation` handler
- Verify that deliberations are being processed by BRP
- Verify that Planning Service is accessible from BRP

### Ceremony Status Not Changing to REVIEWING

- Verify that all stories have review results with all 3 roles
- Check `DeliberationsCompleteProgressConsumer` logs
- Verify that `planning.backlog_review.deliberations.complete` events are being published
- Check Planning Service logs for ceremony status updates

### Timeout Errors

- Increase `REVIEW_RESULTS_TIMEOUT` if deliberations are slow
- Check vLLM service logs for delays
- Verify that Ray Executor is processing jobs correctly
