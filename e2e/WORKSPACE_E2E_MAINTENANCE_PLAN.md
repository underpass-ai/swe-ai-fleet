# Workspace E2E Maintenance Plan

## Objective

Keep the workspace E2E suite fast to evolve, deterministic to run, and cheap to maintain as the workspace catalog keeps growing.

## Current Baseline

- Workspace test directories: `30` (`14` to `43`).
- Workspace Python test files: `27`.
- Approximate Python LOC in `test_workspace_*.py`: `~13,992`.
- Common helper duplication (`print_step`, `_request`, `_write_evidence`, session lifecycle, invocation checks): high.
- Runner is growing and now handles infra concerns (ephemeral deps + evidence handling + sequencing).

## Main Maintenance Risks

1. Repeated test harness code in each test file.
2. Repeated `Dockerfile`/`job.yaml`/`Makefile` patterns across workspace tests.
3. Hardcoded sequencing and feature flags in `e2e/run-e2e-tests.sh`.
4. Soft-failure handling and evidence format drift between tests.
5. Infra dependency drift (ephemeral deps, runner image capabilities, connector profiles).

## Strategy

Use a phased migration with compatibility preserved at every step.

## Phase 0 (done)

Status: completed.

- Added workspace MinIO E2E (`43-workspace-minio-store`).
- Added automatic workspace evidence extraction in runner and MinIO upload (best-effort).
- Kept local evidence copy in `e2e/evidence/` for debugging and reproducibility.

Acceptance:

- `bash e2e/run-e2e-tests.sh --start-from 43 --skip-build --skip-push --cleanup` passes.
- Evidence JSON is saved locally and uploaded to `swe-workspaces-meta`.

## Phase 1 (in progress) - Shared Python Harness

Create and evolve `e2e/tests/workspace_common/` with:

- `base.py`: workspace HTTP/auth/session/invocation/evidence helpers (`WorkspaceE2EBase`).
- `console.py`: common colored output helpers.
- `__init__.py`: stable import surface for migrated tests.

Pilot completed:

- `21-workspace-profiles-governance` migrated.
- `24-workspace-security-sbom` migrated.
- Shared module added with `WorkspaceE2EBase` + console helpers.
- Existing behavior and assertions preserved in both migrated tests.

Remaining scope:

- Migrate next representative tests (`33`, `39`) to prove compatibility in quality-gate and messaging scenarios.

Acceptance:

- Migrated tests pass with no semantic regressions.
- Per-test code size reduced significantly (target: `>=20%` for migrated tests).

## Phase 2 - Test Descriptor + Runner Simplification

Introduce declarative metadata file:

- `e2e/tests/workspace_tests.yaml`

Fields per test:

- `id`, `name`, `job_name`, `requires_ephemeral_deps`, `tier`, `kind`, `timeout_override`, `tags`.

Refactor runner:

- Load workspace test metadata from descriptor (avoid hardcoded lists).
- Add `--workspace-only` and `--tier <smoke|core|full>` selectors.
- Remove duplicated function blocks in runner and centralize error handling.

Acceptance:

- Full suite still runs in identical order by default.
- Targeted runs (workspace-only, tiers) work without manual list editing.

Status update:

- Added `e2e/tests/workspace_tests.yaml` with workspace catalog (`14`-`43`) and metadata.
- Runner now loads workspace test configs and ephemeral dependency flags from descriptor.
- Added selectors `--workspace-only` and `--tier <smoke|core|full>`.

## Phase 3 - Template and Scaffolding

Create generator:

- `e2e/scripts/new-workspace-test.sh`

Generates:

- test skeleton using `workspace_common`.
- `Dockerfile`, `job.yaml`, `Makefile`, `README.md` from templates.

Acceptance:

- New workspace test can be created with one command and run end-to-end.
- No manual copy-paste from existing tests required.

## Phase 4 - Contract and Quality Gates

Standardize evidence schema:

- `schema_version`
- `test_id`, `run_id`, `status`, `steps`, `sessions`, `invocations`, `error_message`

Add lint checks:

- Validate evidence schema for workspace tests.
- Validate `job.yaml` labels/required env/secret refs.
- Validate that each workspace test uses shared harness imports.

Acceptance:

- CI fails fast on schema drift or malformed manifests.
- Evidence consumers can rely on a stable contract.

## Execution Order (recommended)

1. Phase 1 (shared harness pilot)
2. Phase 2 (descriptor + runner cleanup)
3. Phase 3 (scaffold generator)
4. Phase 4 (quality gates)

## Immediate Next Actions

1. Migrate tests `33` and `39` to `workspace_common`. ✅
2. Add `workspace_tests.yaml` with current workspace test catalog (`14`-`43`). ✅
3. Add `--workspace-only` selector to runner and keep current default sequence unchanged. ✅
