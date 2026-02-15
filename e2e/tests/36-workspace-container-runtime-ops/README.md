# E2E Test: Workspace Container Runtime Ops

This test validates container runtime tool contracts in workspace service.

## What it verifies

1. Catalog exposes `container.ps`, `container.logs`, `container.run`, `container.exec`.
2. `container.run` enforces explicit approval (`approval_required`).
3. `container.ps` succeeds (real runtime or simulated fallback).
4. `container.run` succeeds (real runtime or simulated fallback).
5. `container.logs` and `container.exec` succeed with returned `container_id`.
6. `container.exec` blocks non-allowlisted command (`invalid_argument`).

## Build and push

```bash
cd e2e/tests/36-workspace-container-runtime-ops
make build-push
```

## Deploy and inspect

```bash
make deploy
make status
make logs
make delete
```

## Evidence output

- The test writes JSON evidence to `EVIDENCE_FILE`.
- The same JSON is emitted in logs between:
  - `EVIDENCE_JSON_START`
  - `EVIDENCE_JSON_END`
