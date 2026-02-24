# E2E Test: Workspace Repo Analysis Summaries (CAT-014)

This test validates:

- `repo.test_failures_summary`
- `repo.stacktrace_summary`

## What it verifies

1. Catalog exposes CAT-014 repo analysis tools.
2. `repo.test_failures_summary` returns deterministic failed test summaries.
3. `repo.stacktrace_summary` returns deterministic stacktrace summaries.
4. Both tools emit structured summary artifacts.

## Build and push

```bash
cd e2e/tests/31-workspace-repo-analysis-summaries
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
