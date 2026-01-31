# E2E Impact Analysis: Context & Planning Changes

This document analyses how recent changes (story.created epic_id, plan.approved timestamp/approved_at, Context use-case sync→to_thread, save_task, test 07 contract) can affect E2E tests.

---

## 1. Summary of Relevant Changes

| Area | Change | E2E impact |
|------|--------|------------|
| **Planning** | `story.created` payload now includes `epic_id` | Context consumer requires it; old Planning → NAK |
| **Context** | `plan.approved` mapper accepts `approved_at` or `timestamp` | Fixes KeyError; no break |
| **Context** | Use cases call graph port via `asyncio.to_thread(...)` | Fixes TypeError; no break if Neo4j driver used per-thread |
| **Context** | `GraphCommandPort` + `Neo4jCommandStore.save_task` added | Fixes AttributeError on task.created; no break |
| **E2E 07** | Contract assertions in `publish_task_extraction_event` | Fail only if payload missing keys (current payload is valid) |

---

## 2. Changes That Can Break E2E

### 2.1 Story created without `epic_id` (Context NAK)

- **Cause:** Context mapper `payload_to_story` now **requires** `epic_id` and fails with `ValueError` if missing (fail-fast). Planning was updated to **send** `epic_id` in `story.created`.
- **When E2E fails:** Context service is deployed with the new code, but **Planning** is still an old image that does **not** send `epic_id`. Then:
  - E2E 02 runs `CreateStory` via gRPC → Planning (old) publishes `story.created` **without** `epic_id`.
  - Context (new) receives the event → mapper raises `ValueError` → consumer NAKs.
  - Result: story is created in Planning but **not** synced to Context graph. Any E2E that assumes Context has the story (e.g. graph queries) can fail or see inconsistent data.
- **Fix:** Deploy **Planning** with the change that adds `epic_id` to `story.created` **before** or **together with** Context. E2E 02 uses Planning gRPC only; with new Planning, events include `epic_id` and Context accepts them.

### 2.2 Test 07 default `TEST_STORY_ID=ST-001` (pre-existing; fix = redeploy / pass story id)

- **Cause:** Test 07 defaults to `TEST_STORY_ID=ST-001`. Test 02 creates stories via Planning `CreateStory`, which generates IDs like `s-<uuid>`, so it **never** creates a story with id `ST-001`.
- **When E2E fails:** After running 02, test 07 runs with default `ST-001` → `ensure_story_exists("ST-001")` fails → test 07 exits with “Story ST-001 not found in Planning Service”.
- **Not introduced by our changes:** Pre-existing E2E design (default ST-001 vs test 02 auto-generated IDs).
- **Fix:** Redeploy: run test 02, then set `TEST_STORY_ID` to a story id from 02 output before running test 07; or ensure test 07 runs in a pipeline that passes story ids between jobs. No fallbacks in test code.

### 2.3 LogRecord.name conflict (application fix reverted)

- **Cause:** `Story.get_log_context()` and `Project.get_log_context()` return a dict with key `"name"`. The use cases pass this as `extra=log_ctx` to `logger.info()`. In Python 3.13, `logging.LogRecord` reserves the attribute `name`; passing `extra={"name": "..."}` raises `KeyError: "Attempt to overwrite 'name' in LogRecord"`.
- **When E2E fails:** Even when `story.created` payload is valid (epic_id present), Context consumer calls `SynchronizeStoryFromPlanningUseCase.execute(story)`. The first line that logs uses `extra=log_ctx` (with `"name"`) → crash → consumer catches and NAKs. Story is **never** persisted to Neo4j.
- **Current state:** Domain was reverted (still returns `"name"`). Application-layer fix (building `safe_extra` renaming `name` → `story_name`/`project_name` at call site) was **reverted** per request. So the crash remains until fixed elsewhere (e.g. logging helper in infrastructure or consumer that sanitizes `extra` before calling the use case).
- **E2E impact:** Any flow that triggers `planning.story.created` or `planning.project.created` and expects Context to persist the entity will see NAK / no data in Neo4j (E2E 01, 02→03 cleanup, 05/06 assumptions on Context save).

---

## 3. Root-cause chain: “Why E2E stopped working”

Failure order when Context (new) consumes events:

1. **Payload contract:** Context mapper requires `epic_id` and `name` or `title` in `story.created`. If Planning (old) does not send `epic_id` → `ValueError` in mapper → consumer NAK → story not in graph.
2. **Logging crash (after revert):** If payload is valid, use case runs. First `logger.info(..., extra=log_ctx)` is called with `log_ctx` containing `"name"` (from domain `get_log_context()`). Python 3.13 raises `KeyError` → consumer NAK → story still not in graph.
3. **Test 07 story id:** E2E 07 uses `TEST_STORY_ID=ST-001` by default; E2E 02 creates stories with server-generated IDs → `ST-001` does not exist → test 07 fails at `ensure_story_exists`.

**E2E tests that depend on Context/Neo4j having stories or projects:**

| E2E test | Dependency | Failure mode if Context broken |
|----------|------------|---------------------------------|
| 01 GetGraphRelationships | Context gRPC + Neo4j | Missing nodes/relations if stories not synced |
| 02 Create test data | Planning gRPC only | OK; stories in Planning. Context may NAK/crash and not persist |
| 03 Cleanup test data | Planning + Neo4j | May not find Story/Epic/Project in Neo4j to delete |
| 05 Validate deliberations/tasks | Assumes Context save | “Context save assumed” may be wrong if sync fails |
| 06 Approve review plan | plan.approved → Context | OK if `approved_at` accepted; plan approval written |
| 07 Restart/redelivery | Planning GetStory/ListTasks + TEST_STORY_ID | Fails if TEST_STORY_ID not set from 02 output |
| 09/11 Ceremony real side effects | Neo4j instance node | Unrelated to story/project sync |

---

## 4. Changes That Fix E2E (No New Failures)

- **plan.approved:** Context mapper now accepts `approved_at` (Planning) or `timestamp`. E2E 06 flow that triggers `planning.plan.approved` (via ApproveReviewPlan) works with current Planning payload.
- **record_plan_approval / graph writes:** Use cases now call sync graph methods via `asyncio.to_thread(...)`. This removes `TypeError: object NoneType can't be used in 'await' expression`. Plan-approved and other graph writes succeed.
- **save_task:** Context adapter now implements `save_task`. `planning.task.created` consumer no longer raises `AttributeError`; tasks are persisted in the graph.
- **Test 07 payload:** Contract assertions only require `task_id`, `story_id`, `ceremony_id`, `tasks` (each with `title`). The payload built in `publish_task_extraction_event` already has these; no change to payload shape was made, so assertions do not introduce new failures.

---

## 5. Deployment Order Recommendation

To avoid E2E failures due to `story.created` contract:

1. Deploy **Planning** first (so it publishes `story.created` **with** `epic_id`), then **Context**, or
2. Deploy **Planning** and **Context** together from the same release.

If Context is deployed before Planning is updated, Context will NAK all `story.created` events that lack `epic_id` until Planning is updated.

---

## 6. Quick Checklist for “E2E stopped working”

- [ ] **Planning image** includes the change that adds `epic_id` to `story.created` (EventPayloadMapper, MessagingPort, CreateStoryUseCase, NATS adapter).
- [ ] **Context image** is the one that accepts `epic_id` and uses `asyncio.to_thread` for graph writes.
- [ ] **LogRecord.name:** Resolve `KeyError: "Attempt to overwrite 'name' in LogRecord"` (domain returns `"name"` in `get_log_context()`; use cases pass `extra=log_ctx` to logger). Fix options: application-layer `safe_extra` at call site, or infrastructure/consumer that sanitizes `extra` before logging. Until fixed, story/project sync will NAK after mapper success.
- [ ] **Test 07:** Ensure `TEST_STORY_ID` is set to an existing story (e.g. from test 02 output). No fallbacks; redeploy / pass story id between jobs.
- [ ] **Test 06:** No direct dependency on Context/Neo4j in the test code; plan.approved flow is fixed by accepting `approved_at`.

---

## 7. References

- Planning: `services/planning/infrastructure/mappers/event_payload_mapper.py` (`story_created_payload`), `application/usecases/create_story_usecase.py`, `infrastructure/adapters/nats_messaging_adapter.py`.
- Context: `core/context/infrastructure/mappers/planning_event_mapper.py` (`payload_to_story`, `payload_to_plan_approval`), `application/usecases/record_plan_approval.py` and other sync-from-planning/record use cases (`asyncio.to_thread`), `adapters/neo4j_command_store.py` (`save_task`).
- E2E 07: `e2e/tests/07-restart-redelivery-idempotency/test_restart_redelivery_idempotency.py` (contract assertions, `TEST_STORY_ID`).
