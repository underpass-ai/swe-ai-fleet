# E2E Test 07 – Due Diligence: Why Restart & Redelivery Idempotency Test Fails

**Document type:** Due diligence / root-cause analysis
**Scope:** E2E test `07-restart-redelivery-idempotency`
**Status:** Failure root cause identified; fix options documented
**Date:** 2026-01-29

---

## 1. Executive Summary

E2E test 07 fails in the sequential pipeline with:

```text
✗ Story ST-001 not found in Planning Service. Run test 02 (create-test-data) first to create test data, or set TEST_STORY_ID to an existing story.
```

**Root cause:** Test 07 is configured with **placeholder** `TEST_STORY_ID=ST-001` and `TEST_CEREMONY_ID=BRC-TEST-001` in its Job manifest. The E2E runner **never** passes real story/ceremony IDs from earlier tests (02, 04, 05, 06). Those placeholders are **never** created by any test: test 02 creates stories with IDs like `s-<uuid>`, and ceremonies are created with IDs like `BRC-<uuid>`. So in a full run, test 07 always runs against non-existent entities.

This is a **design and wiring gap**, not a regression introduced by a single commit. The test was added with placeholder env and the pipeline was never updated to supply real IDs.

---

## 2. Observed Failure

### 2.1 Symptom

- **Test:** `07-restart-redelivery-idempotency`
- **Runner:** `e2e/run-e2e-tests.sh` (sequential: 00 → 01 → 02 → 04 → 05 → 06 → 07 → …)
- **Failure:** Test 07 pod runs, connects to Planning and NATS, then exits with exit code 1 after:
  - `ensure_story_exists(self.story_id)` returns `False` for `story_id="ST-001"`.
  - Message: *"Story ST-001 not found in Planning Service. Run test 02 (create-test-data) first to create test data, or set TEST_STORY_ID to an existing story."*

### 2.2 Configuration at Failure Time

From the test output:

```text
Configuration:
  Planning Service: planning.swe-ai-fleet.svc.cluster.local:50054
  NATS: nats://nats.swe-ai-fleet.svc.cluster.local:4222
  Story ID: ST-001
  Ceremony ID: BRC-TEST-001
  Task Timeout: 120s
```

So the test is using the **default** values from `job.yaml`, not values from the pipeline.

### 2.3 What the Pipeline Actually Produces

- **Test 02** creates project, epic, and stories via Planning gRPC. Story IDs are **server-generated** (e.g. `s-386bbb75-c0a9-41a5-872c-f7525dc64703`). No test ever creates a story with id `ST-001`.
- **Test 04** starts a backlog review ceremony; ceremony ID is server-generated (e.g. `BRC-2f327119-6a42-4331-a7be-dd18d153ef78`).
- **Test 05** creates a **new** ceremony and adds stories from test 02 (discovered by `TEST_PROJECT_NAME` / `TEST_EPIC_TITLE` / `TEST_CREATED_BY`). Ceremony ID again is server-generated (e.g. `BRC-98897513-b7f7-492f-878f-7ec462eabf21`).
- **Test 06** discovers the same test data (project/epic/stories) and finds a ceremony in REVIEWING that contains those stories.

So after 02, 04, 05, 06 the cluster has **real** story IDs and ceremony IDs, but they are **never** written into test 07’s environment.

---

## 3. Root Cause Analysis

### 3.1 Test 07 Design

- Test 07 expects **existing** entities:
  - A **story** that exists in Planning (for `GetStory` and `ListTasks`).
  - A **ceremony** ID (used in the task-extraction event payload and idempotency key).
- It reads them from **environment variables**:
  - `TEST_STORY_ID` (default in code and in `job.yaml`: `ST-001`).
  - `TEST_CEREMONY_ID` (default: `BRC-TEST-001`).
- It does **not** discover story/ceremony by project/epic/created_by or by listing ceremonies (unlike tests 05 and 06).

Source references:

- `e2e/tests/07-restart-redelivery-idempotency/test_restart_redelivery_idempotency.py`:
  - `self.story_id = os.getenv("TEST_STORY_ID", "ST-001")`.
  - `self.ceremony_id = os.getenv("TEST_CEREMONY_ID", "BRC-TEST-001")`.
  - `ensure_story_exists(self.story_id)` is called before running the idempotency scenario; if the story does not exist, the test exits with the message above.

### 3.2 Job Manifest

- `e2e/tests/07-restart-redelivery-idempotency/job.yaml` **hardcodes**:
  - `TEST_STORY_ID: "ST-001"`.
  - `TEST_CEREMONY_ID: "BRC-TEST-001"`.
- There is **no** ConfigMap, Secret, or env override that the runner injects for test 07. The job is applied as-is.

### 3.3 E2E Runner Behaviour

- `e2e/run-e2e-tests.sh`:
  - Runs tests in order: 00, 01, 02, 04, 05, 06, 07, 08, 09, 10, 11, 03.
  - For each test it: (optionally) builds/pushes the image, deploys the **static** `job.yaml` from the test directory, waits for the job to complete, and optionally runs inspect helpers (e.g. `inspect_test_data` after 02, `inspect_ceremony` after 04, `inspect_tasks` after 05).
  - It **does not**:
    - Parse story IDs or ceremony IDs from test 02/04/05/06 output or from Neo4j.
    - Patch or override the Job spec for test 07 with `TEST_STORY_ID` / `TEST_CEREMONY_ID`.
    - Use a shared ConfigMap/Secret that test 02/05/06 write and test 07 reads.

So test 07 **always** runs with the placeholder values from `job.yaml` when executed by the runner.

### 3.4 Why Tests 05 and 06 Succeed

- **Test 05** (`05-validate-deliberations-and-tasks`):
  - Uses `TEST_PROJECT_NAME`, `TEST_EPIC_TITLE`, `TEST_CREATED_BY` (set in its `job.yaml` to match test 02 data).
  - **Discovers** project → epic → stories via Planning gRPC (`ListProjects`, `ListEpics`, `ListStories`).
  - **Creates** a new ceremony via `CreateBacklogReviewCeremony` and adds those stories. So it never relies on a pre-set `TEST_STORY_ID` or `TEST_CEREMONY_ID`.
- **Test 06** (`06-approve-review-plan-and-validate-plan-creation`):
  - Same env (project/epic/created_by).
  - Discovers stories, then **finds** a ceremony in REVIEWING that contains those stories via `ListBacklogReviewCeremonies` and filtering. So it adapts to whatever ceremony exists (e.g. from test 05).

Test 07, by contrast, **requires** explicit IDs and has no discovery path; it is the only test in this chain that depends on pipeline-supplied story/ceremony IDs, and the pipeline does not supply them.

---

## 4. Commits and Code Changes Relevant to the Failure

### 4.1 Introduction of Test 07 and Placeholder Env

- **Commit:** `7232bfbe` – *feat(B0.5.1): Add idempotency tests to E2E tests 04, 05 and 06 (#123)*
- **Relevance:** Introduced `e2e/tests/07-restart-redelivery-idempotency/job.yaml` with:
  - `TEST_STORY_ID: "ST-001"`
  - `TEST_CEREMONY_ID: "BRC-TEST-001"`
- So from day one, test 07 was **not** wired to real pipeline data; it used placeholders. If it was ever run in a full pipeline without override, it would have failed on `GetStory("ST-001")` (or later when the test was extended with `ensure_story_exists`, that check would fail).

### 4.2 Explicit Story Existence Check (Fail-Fast)

- **Commit:** `2ede8838` – *EventEnvelope in publisher, purge streams doc, E2E 07 story check, Planning CreateTask details*
- **Relevance:** Added `ensure_story_exists()` to test 07 and made the test **fail fast** with a clear message if the story is not found. So:
  - **Before:** The test might have failed later (e.g. on ListTasks or on event processing) with a less clear error.
  - **After:** The test fails immediately at startup with: *"Story ST-001 not found in Planning Service. Run test 02 first or set TEST_STORY_ID."*

This commit did **not** introduce the underlying problem; it made the existing design gap (placeholder IDs, no pipeline wiring) **visible** and **explicit**.

### 4.3 No Runner or Job Change to Pass IDs to Test 07

- No commit in the analysed history adds logic to:
  - Extract story ID(s) or ceremony ID from test 02/04/05/06 output or from Neo4j.
  - Inject `TEST_STORY_ID` / `TEST_CEREMONY_ID` into test 07’s Job (e.g. via `kubectl set env`, patched manifest, or ConfigMap/Secret).

So the failure is due to **missing wiring**, not a regression from a specific code change.

### 4.4 E2E Runner: When Test 07 Was Added to the Pipeline

- **Before commit 7232bfbe:** The runner loop was `01 02 03 04 05 06` — **test 07 was not executed** by the pipeline at all (see `e2e/run-e2e-tests.sh` in commit **fb8711c8**).
- **In commit 7232bfbe:** The loop was extended to `01 02 03 04 05 06 07`. Test 07 was **added** to the sequential run in the same PR that introduced the test and its `job.yaml` with placeholder env.
- **Implication:** Test 07 did not "start failing" because something broke; it **started being run** by the pipeline when 7232bfbe added it. Before that, the full E2E suite never ran test 07. So **"before it didn't fail"** simply means **the runner never ran test 07 before 7232bfbe**.

Later runner commits only added more tests and reordered (03 at the end, 08–11 added):

- **c4037f96:** Loop `01 02 03 04 05 06 07 08`.
- **890f520d:** Loop `01 02 04 05 06 07 08 09 10 11 03` (03 cleanup at end).

None of these runner changes inject `TEST_STORY_ID` or `TEST_CEREMONY_ID` for test 07.

### 4.5 Existing Documentation

- **docs/e2e-impact-from-context-planning-changes.md** already states:
  - *"Test 07 default TEST_STORY_ID=ST-001 (pre-existing; fix = redeploy / pass story id)"*.
  - *"Test 07: Ensure TEST_STORY_ID is set to an existing story (e.g. from test 02 output). No fallbacks; redeploy / pass story id between jobs."*

This aligns with the root cause above: design pre-existing; fix is to pass story (and optionally ceremony) ID from the pipeline.

---

## 5. Why E2E 07 “Stopped Working”

**Why it didn't fail before:** The E2E runner **did not run test 07** before commit **7232bfbe**. The sequential loop was `01 02 03 04 05 06`. That commit added test 07 to the loop (`01 02 03 04 05 06 07`), so the pipeline started executing test 07 for the first time. With the same placeholder env (ST-001, BRC-TEST-001) in `job.yaml`, test 07 then failed whenever the full suite was run. So the change was **including** test 07 in the runner, not a regression in test 07 or in the runner logic.

Other factors:

1. **Never worked in full pipeline:** Once test 07 was in the loop, it never passed with default env; it would need manual override or discovery (see fix options).
2. **Failure became visible:** After `ensure_story_exists` was added (2ede8838), test 07 fails **at the beginning** with a clear message instead of later with a more obscure error.
3. **Manual runs:** If test 07 was ever run manually after 02 with `TEST_STORY_ID` set to a real story, it would pass; the design just was never wired into the runner.

The **technical** answer is: test 07 fails because it runs with `TEST_STORY_ID=ST-001` and `TEST_CEREMONY_ID=BRC-TEST-001`, and the pipeline never replaces these with real IDs from previous tests.

### 5.1 Why test 07 might have worked yesterday

If test 07 **passed or ran further** yesterday, the most likely cause is **commit 2ede8838** (27 Jan 2026, 21:29): *EventEnvelope in publisher, purge streams doc, E2E 07 story check, Planning CreateTask details*.

- **Before 2ede8838:** Test 07 did **not** call `ensure_story_exists()` at the start. It would connect, print configuration, get initial task count (`ListTasks(story_id="ST-001")`), publish the event, and then wait for tasks. So the test would **run past the first step** and fail later (e.g. timeout waiting for tasks, or BRP failing to create tasks for non-existent story). You would not see *"Story ST-001 not found in Planning Service"* at the beginning.
- **After 2ede8838:** Test 07 calls `ensure_story_exists(self.story_id)` **before** doing anything else. With `ST-001` from `job.yaml`, that check fails immediately and the test exits with the clear message. So the **same underlying problem** (placeholder IDs, no wiring) now **fails fast at the start** instead of later.

So if “07 funcionaba ayer” means the test **did not fail at the first step** (or even passed because you had `TEST_STORY_ID` set), then:

1. **Code before 2ede8838:** The test would not fail at `ensure_story_exists` because that check did not exist; it would fail later. Pulling 2ede8838 would make the failure appear at the start.
2. **Yesterday you ran test 07 with `TEST_STORY_ID` (and optionally `TEST_CEREMONY_ID`) set** to real values (e.g. from a previous test 02 run). Today you ran the full suite without setting them, so the test fails at the start.

The runner has **never** injected `TEST_STORY_ID` or `TEST_CEREMONY_ID` for test 07; no commit removes such logic. So “working yesterday” is explained either by (1) running without the fail-fast check (code before 2ede8838), or (2) setting those env vars manually or via another script when running test 07.

---

## 6. Recommended Fixes

### 6.1 Option A: Runner Injects Story and Ceremony IDs (Pipeline Wiring)

- **Idea:** After test 02 (and optionally after 05/06), the runner obtains at least one **story_id** and, if needed, one **ceremony_id** (e.g. from Neo4j or from parsing test output), then deploys test 07 with overridden env.
- **Implementation options:**
  1. **Neo4j after test 02:** Query Neo4j for a `Story` node (e.g. by project/epic) and read `story_id`; after test 05/06, query for a `BacklogReviewCeremony` in REVIEWING and read `ceremony_id`. Then deploy test 07’s Job with `kubectl set env job/e2e-restart-redelivery-idempotency TEST_STORY_ID=<id> TEST_CEREMONY_ID=<id>` **before** creating the job, or use a generated `job.yaml` / `kubectl apply -f -` with substituted env.
  2. **ConfigMap written by test 02/05:** Have test 02 (and optionally 05) write a ConfigMap (e.g. `e2e-test-data`) with `TEST_STORY_ID` and optionally `TEST_CEREMONY_ID`. Test 07’s `job.yaml` would reference this ConfigMap in `envFrom` or `valueFrom`. The runner would need to ensure test 02 (and 05) run before 07 and that the ConfigMap exists; test 07 would need to be able to run when only story ID is set (ceremony ID can be optional or derived).
  3. **Runner parses logs:** After test 02, parse job logs for “Story created: s-…” and “Ceremony ID: BRC-…”; store in shell variables and pass them when deploying test 07 (e.g. `envsubst` or a small script that patches the Job manifest). Fragile if log format changes.

- **Pros:** Test 07 stays simple (env-based); single source of truth for “which story/ceremony” is the runner.
- **Cons:** Runner and/or test 02/05 need to be extended; may require convention on ConfigMap names and keys.

### 6.2 Option B: Test 07 Discovers Story (and Optionally Ceremony)

- **Idea:** Make test 07 behave like tests 05/06: use `TEST_PROJECT_NAME`, `TEST_EPIC_TITLE`, `TEST_CREATED_BY` (and optionally same env as in 05/06), discover stories via `ListProjects` → `ListEpics` → `ListStories`, pick one story (e.g. first). Optionally discover a ceremony in REVIEWING that contains that story via `ListBacklogReviewCeremonies` and filter.
- **Implementation:** In `test_restart_redelivery_idempotency.py`, add a “discovery” step (similar to test 05’s preparation): if `TEST_STORY_ID` is not set or is the placeholder `ST-001`, run discovery and set `self.story_id` (and optionally `self.ceremony_id`). Keep `TEST_STORY_ID` / `TEST_CEREMONY_ID` as overrides when provided.
- **Pros:** No runner changes; test 07 works in the same sequential run as 02 → 04 → 05 → 06 with the same `job.yaml` (using same project/epic env as 05/06).
- **Cons:** Test 07 becomes slightly more complex and depends on the same test data shape (project/epic) as 05/06; duplicate discovery logic unless shared.

### 6.3 Option C: Document and Manual Override Only

- **Idea:** Do not change runner or test 07 logic. Document that for the **full** E2E run, test 07 must be run with env override (e.g. `kubectl set env` after extracting IDs from test 02/05 logs or Neo4j), or run test 07 standalone with `TEST_STORY_ID` and `TEST_CEREMONY_ID` set to known-good values.
- **Pros:** No code change.
- **Cons:** Sequential “run all” will keep failing unless users or CI explicitly script the override.

### 6.4 Recommendation

- **Short term:** Implement **Option B** (discovery in test 07 using same project/epic/created_by as 05/06) so that the existing runner and `job.yaml` work without any pipeline changes. Align test 07’s `job.yaml` env with 05/06 (`TEST_PROJECT_NAME`, `TEST_EPIC_TITLE`, `TEST_CREATED_BY`) and keep `TEST_STORY_ID` / `TEST_CEREMONY_ID` as optional overrides.
- **Medium term:** If a single source of truth for “E2E test data” is desired (e.g. ConfigMap written by test 02), consider **Option A** and optionally simplify test 07 back to env-only, fed by the runner or ConfigMap.

### 6.5 After applying Option B: rebuild test 07 image

When the E2E runner is invoked with **`--skip-build`**, it does not rebuild or push images; it still deploys each test’s Job (e.g. `kubectl apply -f job.yaml`). The cluster uses whatever image is already in the registry (Job has `imagePullPolicy: Always`). To pick up the discovery fix:

- **From project root:** Rebuild and push the test 07 image, then run the suite with `--skip-build`:
  ```bash
  make e2e-build-push-test TEST=07-restart-redelivery-idempotency
  ./e2e/run-e2e-tests.sh --skip-build
  ```
- Or run the full E2E suite **without** `--skip-build` once so that all test images (including 07) are built and pushed before deploy.

---

## 7. References

| Item | Location |
|------|----------|
| Test 07 script | `e2e/tests/07-restart-redelivery-idempotency/test_restart_redelivery_idempotency.py` |
| Test 07 Job | `e2e/tests/07-restart-redelivery-idempotency/job.yaml` |
| Test 07 README | `e2e/tests/07-restart-redelivery-idempotency/README.md` |
| E2E runner | `e2e/run-e2e-tests.sh` |
| Test 05 discovery | `e2e/tests/05-validate-deliberations-and-tasks/validate_deliberations_and_tasks.py` (ListProjects, ListEpics, ListStories, CreateBacklogReviewCeremony) |
| Test 06 discovery | `e2e/tests/06-approve-review-plan-and-validate-plan-creation/approve_review_plan_and_validate_plan_creation.py` (ListStories, ListBacklogReviewCeremonies) |
| E2E impact doc | `docs/e2e-impact-from-context-planning-changes.md` |
| Commits | `7232bfbe` (test 07 job + placeholders), `2ede8838` (ensure_story_exists) |

---

## 8. Self-Verification Report

- **Completeness:** ✓ Failure symptom, configuration, pipeline output, and code paths described; root cause (placeholder IDs + no pipeline wiring) stated; commits referenced; three fix options with pros/cons.
- **Logical and architectural consistency:** ✓ No contradictions; aligns with existing doc `e2e-impact-from-context-planning-changes.md`.
- **Domain boundaries and dependencies validated:** ✓ Test 07 depends on Planning (GetStory, ListTasks) and NATS; story/ceremony IDs must exist; pipeline produces them but does not pass them to test 07.
- **Edge cases and failure modes covered:** ✓ Clarified “why it stopped working” (never wired vs. fail-fast made it visible); optional override and discovery behaviour mentioned.
- **Trade-offs analyzed:** ✓ Option A (runner) vs B (discovery in test) vs C (doc only) summarised.
- **Confidence level:** High. Root cause is code and manifest inspection plus runner behaviour; no assumption about historic CI behaviour beyond commit messages and doc.
- **Unresolved questions:** None for the root-cause analysis. Choice of fix (A vs B vs C) is a product/process decision.
