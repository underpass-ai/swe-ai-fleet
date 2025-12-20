# E2E Test: Start Backlog Review Ceremony

This test verifies that a backlog review ceremony can be successfully started in the system.

## Test Flow

This test follows the **Backlog Review Flow** diagram (see `services/backlog_review_processor/BACKLOG_REVIEW_FLOW_NO_STYLES.md`).

The test performs the following steps:

1. **Find Test Data** (Step 1.1: Repository access)
   - Searches for the test project "Test de swe fleet"
   - Finds epic "Autenticacion"
   - Lists associated stories

2. **Create Ceremony** (Step 2: UI → PL gRPC)
   - Creates a new backlog review ceremony in DRAFT status

3. **Add Stories** (Step 2: UI → PL gRPC)
   - Adds the discovered stories to the ceremony

4. **Start Ceremony** (Step 2: UI → PL gRPC)
   - Starts the ceremony, which internally triggers:
     - **Step 3**: PL → CTX (Get context rehydration by RBAC and StoryId)
     - **Step 4**: PL → EXEC (Trigger deliberation per RBAC agent and StoryId)
   - Returns ceremony in IN_PROGRESS status with deliberations submitted count

5. **Verify Status**: Verifies that the ceremony status is IN_PROGRESS

6. **Verify Deliberations**: Verifies that deliberations were submitted (expected: 3 roles × stories count)

### Flow Coverage

✅ **Verified Steps:**
- Step 1.1: Repository access (find project/epic/stories)
- Step 2: UI → PL gRPC (Create ceremony, Add stories, Start ceremony)
- Step 3: PL → CTX (implicitly verified via deliberations_submitted count)
- Step 4: PL → EXEC (implicitly verified via deliberations_submitted count)

❌ **Not Verified (Async Steps):**
- Step 5-9: Deliberation execution (Ray → vLLM → NATS → BRP → CTX → PL)
- Step 10-14: Task creation execution (Ray → vLLM → NATS → BRP → CTX → PL)

These async steps occur in the background and take several minutes. They are verified by the system's async processing, not by this e2e test.

## Prerequisites

### Test Data

The test requires test data to exist. Run the test data creation job first:

```bash
cd e2e/tests/02-create-test-data
make deploy
```

Wait for the job to complete successfully before running this test.

### Services

- **Planning Service**: Must be deployed and accessible
- **Orchestrator Service**: Must be deployed (for ceremony start)
- **Neo4j**: Must be accessible (for test data lookup)
- **Valkey**: Must be accessible (for ceremony state)

## Usage

### Build and Push Image

```bash
cd e2e/tests/04-start-backlog-review-ceremony
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

## Expected Output

On success, the test will output:

```
🧪 E2E Test: Start Backlog Review Ceremony
================================================================================

Step 1: Find Test Data
  ✓ Found project: PROJ-xxx - 'Test de swe fleet'
  ✓ Found epic: E-xxx - 'Autenticacion'
  ✓ Found 4 stories

Step 2: Create Backlog Review Ceremony
  ✓ Ceremony created: BRC-xxx
  Status: DRAFT

Step 3: Add Stories to Ceremony
  ✓ Added 4 stories to ceremony
  Ceremony status: DRAFT
  Stories in ceremony: 4

Step 4: Start Backlog Review Ceremony
  ✓ Ceremony started successfully
  Ceremony ID: BRC-xxx
  Status: IN_PROGRESS
  Deliberations submitted: 12
  Message: Ceremony started: 12 deliberations submitted

📊 Test Execution Summary
================================================================================

Test Data:
  Project: PROJ-xxx - 'Test de swe fleet'
  Epic: E-xxx - 'Autenticacion'
  Stories (4):
    - s-xxx
    - s-xxx
    - s-xxx
    - s-xxx

Ceremony:
  Ceremony ID: BRC-xxx
  Status: IN_PROGRESS

✅ Test Completed Successfully
```

## Test Details

### What is Verified

- ✅ Test data can be discovered (project, epic, stories)
- ✅ Backlog review ceremony can be created
- ✅ Stories can be added to a ceremony
- ✅ Ceremony can be started successfully
- ✅ Ceremony status transitions to IN_PROGRESS
- ✅ Deliberations are submitted to the Orchestrator

### What is NOT Verified

- ❌ Deliberation results (arrive asynchronously via NATS)
- ❌ Ceremony completion (requires PO approval/rejection)
- ❌ Review results processing

## Notes

- **Asynchronous Processing**: The ceremony start triggers background processing. The test only verifies that the ceremony is started (IN_PROGRESS status), not that deliberations complete.
- **Test Data Dependency**: This test depends on test data created by `02-create-test-data`. Ensure that job runs successfully first.
- **Long-Running Operation**: Starting a ceremony may take time as it involves multiple gRPC calls. The job has a 10-minute timeout.
- **No Cleanup**: This test does not clean up the created ceremony. Use `03-cleanup-test-data` or manual cleanup if needed.

## Troubleshooting

### Test Data Not Found

If the test fails with "Project not found" or "Epic not found":

1. Verify that `02-create-test-data` job completed successfully
2. Check that the project name matches: "Test de swe fleet"
3. Check that the epic title matches: "Autenticacion"

### Ceremony Start Fails

If the ceremony start fails:

1. Verify Planning Service is accessible
2. Verify Orchestrator Service is accessible
3. Check that stories were successfully added to the ceremony
4. Review logs for gRPC errors

### Status Not IN_PROGRESS

If the ceremony status is not IN_PROGRESS after starting:

1. Check Planning Service logs for errors
2. Verify the ceremony has stories (cannot start empty ceremony)
3. Verify the ceremony was in DRAFT status before starting
