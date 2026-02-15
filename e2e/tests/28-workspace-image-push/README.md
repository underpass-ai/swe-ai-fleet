# E2E Test: Workspace Image Push

This test validates `image.push` in workspace runtime.

## What it verifies

1. Catalog exposes `image.push`.
2. Tool requires explicit approval.
3. Push output is structured and deterministic (`builder`, `simulated`, `pushed`, `image_ref`).
4. Invocation artifacts include `image-push-report.json`.

## Build and push

```bash
cd e2e/tests/28-workspace-image-push
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
