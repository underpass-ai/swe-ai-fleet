# E2E Test: Workspace API Benchmark

This test validates the `api.benchmark` tool contract in workspace service.

## What it verifies

1. `api.benchmark` is exposed in catalog for `devops` sessions.
2. Happy path benchmark succeeds against an allowlisted route.
3. Route outside profile allowlist is denied with `policy_denied`.
4. Limits above hard constraints are rejected (`invalid_argument`).

## Build and push

```bash
cd e2e/tests/34-workspace-api-benchmark
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
