# E2E Test: Workspace Quality Gate Pipeline (CAT-016)

This test validates:

- `quality.gate`
- `ci.run_pipeline` integration with quality gates

## What it verifies

1. Catalog exposes CAT-016 tools.
2. `ci.run_pipeline` evaluates `quality.gate` thresholds and fails on gate breach.
3. `quality.gate` can be invoked directly with deterministic metrics.
4. Quality gate artifacts are emitted for both direct and integrated flows.

## Build and push

```bash
cd e2e/tests/33-workspace-quality-gate-pipeline
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

- JSON evidence is written to `EVIDENCE_FILE`.
- The same JSON is printed in logs between:
  - `EVIDENCE_JSON_START`
  - `EVIDENCE_JSON_END`
