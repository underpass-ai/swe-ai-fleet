# E2E Test: Validate Deliberations and Tasks Complete

This test validates the asynchronous steps (5-14) of the Backlog Review Flow, divided into **12 independent stages** for precise failure identification and improved observability.

## Test Flow

This test follows the **Backlog Review Flow** diagram (see `services/backlog_review_processor/BACKLOG_REVIEW_FLOW_NO_STYLES.md`).

The test validates the complete flow in 12 stages:

### Stage 0: Preparation
- Finds or creates a backlog review ceremony
- Ensures ceremony is in `IN_PROGRESS` status

### Stages 1-5: Deliberation Execution

1. **Stage 1: Ray Job Creation** (Step 5)
   - Validates that Ray Executor received deliberation requests
   - Verifies Ray Jobs were created for each (story, role) combination

2. **Stage 2: vLLM Invocation** (Step 6)
   - Validates that Ray Jobs invoked vLLM service
   - Verifies vLLM processed the requests

3. **Stage 3: NATS Event Reception** (Step 7)
   - Validates that vLLM published `agent.response.completed` events
   - Verifies Backlog Review Processor received the events

4. **Stage 4: Context Service Save** (Step 8)
   - Validates that deliberations were saved to Context Service
   - Verifies deliberation structure

5. **Stage 5: Deliberations Complete** (Step 9)
   - Polls ceremony status until it transitions to `REVIEWING`
   - Verifies all stories have review results
   - Verifies each review result has feedback from all 3 roles (ARCHITECT, QA, DEVOPS)

### Stages 6-12: Task Creation Execution

6. **Stage 6: Task Extraction Trigger** (Step 10)
   - Validates that Backlog Review Processor triggered task extraction
   - Verifies `ExtractTasksFromDeliberationsUseCase` executed

7. **Stage 7: Task Ray Job Creation** (Step 11)
   - Validates that Ray Executor created jobs for task extraction
   - Verifies Ray Jobs were created for each story

8. **Stage 8: Task vLLM Invocation** (Step 12)
   - Validates that Ray Jobs invoked vLLM for task extraction
   - Verifies vLLM processed the requests

9. **Stage 9: Task NATS Events** (Step 13)
   - Validates that vLLM published `agent.response.completed` events with `task_type: "TASK_EXTRACTION"`
   - Verifies Backlog Review Processor received the events

10. **Stage 10: Task Context Save** (Step 13.1)
    - Validates that tasks were saved to Context Service
    - Verifies task structure

11. **Stage 11: Tasks Created in Planning** (Step 13.1 - Planning)
    - Polls stories to verify tasks were created
    - Verifies each story has tasks with type `BACKLOG_REVIEW_IDENTIFIED`
    - Verifies tasks are associated to correct stories

12. **Stage 12: Tasks Complete Event** (Step 14)
    - Validates that `planning.backlog_review.tasks.complete` event was published
    - Verifies Planning Service received the event

### Flow Coverage

✅ **Verified Steps:**
- Step 5: EXEC → RAYJOB (Create Ray job for deliberations)
- Step 6: RAYJOB → VLLM (Model invocation for deliberations)
- Step 7: VLLM → BRP (NATS - VLLM response for deliberations)
- Step 8: BRP → CTX (Save deliberation response)
- Step 9: BRP → PL (DELIBERATIONS COMPLETED)
- Step 10: BRP → EXEC (Trigger task creation)
- Step 11: EXEC → RAYJOB_TASK (Create Ray job for tasks)
- Step 12: RAYJOB_TASK → VLLM_TASK (Model invocation for tasks)
- Step 13: VLLM_TASK → BRP (NATS - VLLM response for tasks)
- Step 13.1: BRP → CTX (Save TASK response)
- Step 13.1: BRP → PL (Tasks created in Planning)
- Step 14: BRP → PL (ALL TASK CREATED)

## Prerequisites

### Test Data

The test requires test data to exist. Run the test data creation job first:

```bash
cd e2e/tests/02-create-test-data
make deploy
```

Wait for the job to complete successfully before running this test.

### Ceremony Status

The test can work in two modes:

1. **Reuse Existing Ceremony**: If a ceremony in `IN_PROGRESS` status exists with the test stories, it will be reused.
2. **Create New Ceremony**: If no ceremony exists, the test will create one, add stories, and start it.

Alternatively, you can run the ceremony start test first:

```bash
cd e2e/tests/04-start-backlog-review-ceremony
make deploy
```

Wait for the ceremony to be in `IN_PROGRESS` status before running this test.

### Services

- **Planning Service**: Must be deployed and accessible
- **Backlog Review Processor**: Must be deployed and listening to NATS events
- **Ray Executor Service**: Must be deployed
- **vLLM Service**: Must be accessible
- **Context Service**: Must be deployed
- **NATS**: Must be accessible and configured
- **Neo4j**: Must be accessible

## Usage

### Build and Push Image

```bash
cd e2e/tests/05-validate-deliberations-and-tasks
make build-push
```

### Deploy Job

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

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLANNING_SERVICE_URL` | Planning Service gRPC endpoint | `planning.swe-ai-fleet.svc.cluster.local:50054` |
| `TEST_CREATED_BY` | User creating the ceremony | `e2e-test@system.local` |
| `TEST_PROJECT_NAME` | Project name to search for | `Test de swe fleet` |
| `TEST_EPIC_TITLE` | Epic title to search for | `Autenticacion` |
| `DELIBERATIONS_TIMEOUT` | Timeout for deliberations to complete (seconds) | `600` (10 minutes) |
| `TASKS_TIMEOUT` | Timeout for tasks to be created (seconds) | `600` (10 minutes) |
| `POLL_INTERVAL` | Polling interval for status checks (seconds) | `10` |

## Expected Output

On success, the test will output:

```
🧪 E2E Test: Validate Deliberations and Tasks (Por Etapas)
================================================================================

Configuration:
  Planning Service: planning.swe-ai-fleet.svc.cluster.local:50054
  Deliberations Timeout: 600s
  Tasks Timeout: 600s
  Poll Interval: 10s

================================================================================
[Etapa 0] Preparación
================================================================================
  ✓ Found project: PROJ-xxx
  ✓ Found epic: E-xxx
  ✓ Found 4 stories
  ✓ Ceremony BRC-xxx is in IN_PROGRESS
  ✓ Ceremony has 4 stories
  ✅ Etapa 0: Preparación completada. Ceremony: BRC-xxx

================================================================================
ETAPAS 1-5: Deliberation Execution
================================================================================

🔄 Iniciando validación de Deliberation Execution...

[Etapa 1] Ray Job Creation
  ✅ Etapa 1: Ray Job Creation

[Etapa 2] vLLM Invocation
  ✅ Etapa 2: vLLM Invocation

[Etapa 3] NATS Event Reception
  ✅ Etapa 3: NATS Event Reception

[Etapa 4] Context Service Save
  ✅ Etapa 4: Context Service Save

[Etapa 5] Deliberations Complete
  ℹ Waiting for deliberations to complete (timeout: 600s)...
  ℹ Polling ceremony status (attempt 1/60)...
  ℹ Status: IN_PROGRESS, Review Results: 0/4
  ...
  ℹ Polling ceremony status (attempt 25/60)...
  ℹ Status: REVIEWING, Review Results: 4/4
  ✓ All deliberations completed
  ✓ Ceremony transitioned to REVIEWING
  ✓ All 4 stories have review results
  ✓ Each story has feedback from 3 roles (ARCHITECT, QA, DEVOPS)
  ✅ Etapa 5: Deliberations Complete

================================================================================
ETAPAS 6-12: Task Creation Execution
================================================================================

🔄 Iniciando validación de Task Creation Execution...

[Etapa 6] Task Extraction Trigger
  ✅ Etapa 6: Task Extraction Trigger

[Etapa 7] Task Ray Job Creation
  ✅ Etapa 7: Task Ray Job Creation

[Etapa 8] Task vLLM Invocation
  ✅ Etapa 8: Task vLLM Invocation

[Etapa 9] Task NATS Events
  ✅ Etapa 9: Task NATS Events

[Etapa 10] Task Context Save
  ✅ Etapa 10: Task Context Save

[Etapa 11] Tasks Created in Planning
  ℹ Waiting for tasks to be created (timeout: 600s)...
  ℹ Checking tasks (attempt 1/60)...
  ℹ Stories with tasks: 0/4
  ...
  ℹ Checking tasks (attempt 15/60)...
  ℹ Stories with tasks: 4/4
  ✓ All stories have tasks created
  ✓ Story s-xxx has 3 tasks
  ✓ Story s-xxx has 2 tasks
  ✓ Story s-xxx has 4 tasks
  ✓ Story s-xxx has 2 tasks
  ✓ All tasks have type BACKLOG_REVIEW_IDENTIFIED
  ✅ Etapa 11: Tasks Created in Planning: {'s-xxx': 3, 's-xxx': 2, 's-xxx': 4, 's-xxx': 2}

[Etapa 12] Tasks Complete Event
  ✅ Etapa 12: Tasks Complete Event

================================================================================
📊 Test Execution Summary
================================================================================

Ceremony:
  Ceremony ID: BRC-xxx
  Stories: 4

Tasks Created:
  Total: 11 tasks
  By Story:
    - s-xxx: 3 tasks
    - s-xxx: 2 tasks
    - s-xxx: 4 tasks
    - s-xxx: 2 tasks

Timing by Stage:
  Etapa 0 (Preparación): 2.00s
  Etapa 1 (Ray Job Creation): 0.50s
  Etapa 2 (vLLM Invocation): 0.50s
  Etapa 3 (NATS Events): 0.50s
  Etapa 4 (Context Save): 0.50s
  Etapa 5 (Deliberations Complete): 72.00s
  Etapa 6 (Task Extraction Trigger): 0.50s
  Etapa 7 (Task Ray Job Creation): 0.50s
  Etapa 8 (Task vLLM Invocation): 0.50s
  Etapa 9 (Task NATS Events): 0.50s
  Etapa 10 (Task Context Save): 0.50s
  Etapa 11 (Tasks Created): 135.00s
  Etapa 12 (Tasks Complete Event): 0.50s
  Total: 213.50s

✅ Todas las etapas completadas exitosamente
✅ Test Completed Successfully
```

## Test Details

### What is Verified

- ✅ Ceremony can be found or created and is in `IN_PROGRESS` status
- ✅ Ray Jobs are created for deliberations (Stage 1)
- ✅ vLLM is invoked for deliberations (Stage 2)
- ✅ NATS events are received for deliberations (Stage 3)
- ✅ Deliberations are saved to Context Service (Stage 4)
- ✅ All deliberations complete and ceremony transitions to `REVIEWING` (Stage 5)
- ✅ Task extraction is triggered (Stage 6)
- ✅ Ray Jobs are created for task extraction (Stage 7)
- ✅ vLLM is invoked for task extraction (Stage 8)
- ✅ NATS events are received for tasks (Stage 9)
- ✅ Tasks are saved to Context Service (Stage 10)
- ✅ Tasks are created in Planning Service (Stage 11)
- ✅ Tasks complete event is published (Stage 12)

### Stage-by-Stage Validation

Each stage validates a specific part of the flow. If a stage fails, the test stops and reports exactly which stage failed, making debugging easier.

### Polling Strategy

Stages 5 and 11 use polling to wait for async operations:
- **Stage 5**: Polls ceremony status until it transitions to `REVIEWING` and all review results are complete
- **Stage 11**: Polls stories to verify tasks are created

Both stages have configurable timeouts and poll intervals.

## Notes

- **Long-Running Operation**: This test can take 10-20 minutes to complete, as it waits for vLLM processing, NATS events, and async operations.
- **Timeout Configuration**: Adjust `DELIBERATIONS_TIMEOUT` and `TASKS_TIMEOUT` if your environment needs more time.
- **Stage Independence**: Each stage is independent, allowing for precise failure identification.
- **Observability**: Each stage reports its progress and timing, making it easy to identify bottlenecks.

## Troubleshooting

### Deliberations Not Completing

If Stage 5 times out:

1. Check Backlog Review Processor logs for errors
2. Verify Ray Executor is running jobs
3. Verify vLLM is accessible
4. Check NATS connectivity
5. Verify Context Service is accessible
6. Increase `DELIBERATIONS_TIMEOUT` if needed

### Tasks Not Being Created

If Stage 11 times out:

1. Check Backlog Review Processor logs for `ExtractTasksFromDeliberationsUseCase`
2. Verify `TaskExtractionResultConsumer` processed events
3. Verify Planning Service received task creation requests
4. Check that deliberations are complete (ceremony in `REVIEWING` status)
5. Increase `TASKS_TIMEOUT` if needed

### Ceremony Not Found

If the test cannot find or create a ceremony:

1. Verify test data exists (run `02-create-test-data`)
2. Verify Planning Service is accessible
3. Check that stories exist in the epic

### Stage-Specific Failures

If a specific stage fails:

1. Review the stage logs for detailed error messages
2. Check the service logs for that stage (Ray, vLLM, BRP, Context, Planning)
3. Verify network connectivity between services
4. Check NATS stream configuration

## Related Tests

- **02-create-test-data**: Creates test data required by this test
- **04-start-backlog-review-ceremony**: Starts the ceremony (can be run before this test)
- **03-cleanup-test-data**: Cleans up test data after testing
