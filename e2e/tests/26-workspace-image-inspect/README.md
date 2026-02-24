# E2E Test: Workspace Image Inspect

This test validates `image.inspect` in workspace runtime.

## What it verifies

1. Catalog exposes `image.inspect`.
2. Dockerfile mode works and returns structured issues.
3. Image reference mode works and returns structured issues.
4. Invocation artifacts include `image-inspect-report.json`.

## Build and push

```bash
cd e2e/tests/26-workspace-image-inspect
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
