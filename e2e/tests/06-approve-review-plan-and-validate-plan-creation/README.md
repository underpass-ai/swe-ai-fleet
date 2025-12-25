# E2E Test: Approve Review Plan and Validate Plan Creation

This E2E test validates the Human-in-the-Loop approval flow (steps 15-18) of the Backlog Review Flow.

## Overview

This test validates the complete flow of approving a review plan and creating an official Plan entity with tasks that include decision metadata. The test is divided into 8 independent stages:

1. **Stage 0**: Preparation - Find ceremony in REVIEWING state
2. **Stage 1**: Approve plan for first story
3. **Stage 2**: Validate plan in storage (Neo4j/Valkey)
4. **Stage 3**: Validate tasks with decision metadata
5. **Stage 4**: Validate ceremony updated
6. **Stage 5**: Validate event published
7. **Stage 6**: Approve plan for all remaining stories
8. **Stage 7**: Validate final state
9. **Stage 8**: Validate complete persistence

## Flow Verified

Following `BACKLOG_REVIEW_FLOW.md`:

- **Step 15**: PO approves review plan (Human-in-the-Loop)
- **Step 16**: Create official Plan entity
- **Step 17**: Create tasks with decision (save_task_with_decision)
- **Step 18**: Publish `planning.plan.approved` event

## Prerequisites

### Test Data

- ✅ Project: "Test de swe fleet"
- ✅ Epic: "Autenticacion"
- ✅ Stories: 4 stories (RBAC, AUTH0, Autenticacion en cliente, Rol Admin y Rol User)
- ✅ **Ceremony in REVIEWING state** (completed by test 05)
- ✅ **All deliberations complete**
- ✅ **All tasks created** (type `BACKLOG_REVIEW_IDENTIFIED`)

**Note:** This test should be run after test 05 (`05-validate-deliberations-and-tasks`) which creates the ceremony and waits for it to reach REVIEWING state.

### Services Required

- ✅ **Planning Service**: Must be deployed
- ✅ **Neo4j**: Must be accessible
- ✅ **Valkey**: Must be accessible
- ✅ **NATS**: Must be accessible (for event validation)

### Initial State

- Ceremony must be in state `REVIEWING`
- Each story must have `review_result` with `plan_preliminary`
- Each story must have tasks created (type `BACKLOG_REVIEW_IDENTIFIED`)

## Building

```bash
cd e2e/tests/06-approve-review-plan-and-validate-plan-creation
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
| `PLANNING_SERVICE_URL` | Planning Service endpoint | No | `planning.swe-ai-fleet.svc.cluster.local:50054` |
| `TEST_CREATED_BY` | Test creator identifier | No | `e2e-test@system.local` |
| `TEST_PROJECT_NAME` | Project name for test data | No | `Test de swe fleet` |
| `TEST_EPIC_TITLE` | Epic title for test data | No | `Autenticacion` |
| `PO_APPROVED_BY` | PO username approving plan | No | `e2e-po@system.local` |
| `PO_NOTES` | PO approval notes | No | `E2E test approval - plan looks good` |
| `PO_CONCERNS` | PO concerns (optional) | No | `` |
| `PRIORITY_ADJUSTMENT` | Priority adjustment (optional) | No | `` |
| `PO_PRIORITY_REASON` | Reason for priority adjustment (optional) | No | `` |
| `STAGE_TIMEOUT` | Timeout per stage in seconds | No | `30` |

## Test Stages

### Stage 0: Preparation

Validates that:
- ✅ Ceremony exists and is in state `REVIEWING`
- ✅ All stories have `review_results` with `plan_preliminary`
- ✅ All stories have tasks created

### Stage 1: Approve Plan for First Story

Validates that:
- ✅ `ApproveReviewPlan` returns success
- ✅ Plan created with `plan_id` valid
- ✅ Plan has correct properties
- ✅ Ceremony updated with `approved_result`

### Stage 2: Validate Plan in Storage

Validates that:
- ✅ Plan exists (validated through task associations)
- ✅ Note: Direct Neo4j/Valkey validation would require additional clients

### Stage 3: Validate Tasks with Decision

Validates that:
- ✅ Tasks have `plan_id` assigned
- ✅ Tasks have type `BACKLOG_REVIEW_IDENTIFIED`
- ✅ Number of tasks matches `task_decisions` in `plan_preliminary`
- ✅ Note: `decision_metadata` validation would require Neo4j access

### Stage 4: Validate Ceremony Updated

Validates that:
- ✅ `StoryReviewResult` has `approval_status == "APPROVED"`
- ✅ `StoryReviewResult` has `approved_by` and `approved_at`
- ✅ `StoryReviewResult` has `po_notes`

### Stage 5: Validate Event Published

Validates that:
- ✅ Event `planning.plan.approved` published (assumed if ApproveReviewPlan succeeded)
- ✅ Note: Direct NATS validation would require NATS client subscription

### Stage 6: Approve Plan for All Remaining Stories

Validates that:
- ✅ All remaining stories have plans approved
- ✅ Each story has Plan associated
- ✅ All tasks have decision metadata

### Stage 7: Validate Final State

Validates that:
- ✅ All stories have `approval_status == "APPROVED"`
- ✅ Number of plans = number of stories

### Stage 8: Validate Complete Persistence

Validates that:
- ✅ All Plans validated through task associations
- ✅ All tasks have `plan_id` assigned
- ✅ Note: Direct Neo4j/Valkey validation would require additional clients

## Known Issues

### Planning Service Bug: ListBacklogReviewCeremonies with Approved Reviews

**Symptom:** Test fails with `INVALID_ARGUMENT` error: "Approved review must have po_notes explaining WHY PO approved"

**Root Cause:** The Planning Service has a bug where `ListBacklogReviewCeremonies` fails when trying to reconstruct ceremonies from storage that have `StoryReviewResult` objects with `approval_status=APPROVED` but missing `po_notes`. The validation in `StoryReviewResult.__post_init__` requires `po_notes` for approved reviews, but the storage adapter may reconstruct objects without this field.

**Workaround:** The test will retry the operation. However, this is a service bug that needs to be fixed in the Planning Service.

**Fix Required:** The Planning Service storage adapter or mapper should either:
1. Ensure `po_notes` is always present when reconstructing approved reviews, OR
2. Make the validation conditional (only validate on creation, not on reconstruction from storage)

## Troubleshooting

### Test fails with "Ceremony not found in REVIEWING state"

**Cause**: Test 05 has not been run or ceremony is not in REVIEWING state.

**Solution**:
```bash
# Run test 05 first
cd e2e/tests/05-validate-deliberations-and-tasks
make build-push
make deploy
make logs

# Wait for ceremony to reach REVIEWING state
# Then run test 06
```

### Test fails with "ApproveReviewPlan failed"

**Cause**: Planning Service error or ceremony not ready.

**Solution**:
- Check Planning Service logs
- Verify ceremony is in REVIEWING state
- Verify story has `plan_preliminary` in `review_result`

### Test fails with "No tasks found with plan_id"

**Cause**: Tasks were not created with plan_id.

**Solution**:
- Check Planning Service logs for task creation
- Verify `save_task_with_decision` is called correctly
- Verify `task_decisions` exist in `plan_preliminary`

## Integration with Test 05

This test is designed to run **after** test 05 (`05-validate-deliberations-and-tasks`), which:

1. Creates or finds a ceremony
2. Starts the ceremony (moves to IN_PROGRESS)
3. Waits for deliberations to complete
4. Waits for tasks to be created
5. Verifies ceremony reaches REVIEWING state

Test 06 then:
1. Finds the ceremony in REVIEWING state
2. Approves plans for all stories
3. Validates plan creation and task persistence

## References

- [Backlog Review Flow](../../../../services/backlog_review_processor/BACKLOG_REVIEW_FLOW.md) - Complete flow diagram
- [Test 05](../05-validate-deliberations-and-tasks/README.md) - Previous test in sequence
- [E2E Test Procedure](../../../PROCEDURE.md) - General E2E test procedure

---

**Last Updated**: 2025-12-20
**Maintained by**: SWE AI Fleet Development Team

