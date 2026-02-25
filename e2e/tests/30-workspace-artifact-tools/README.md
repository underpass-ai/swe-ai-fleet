# E2E Test: Workspace Artifact Tools (CAT-013)

This test validates:

- `artifact.upload`
- `artifact.download`
- `artifact.list`

## What it verifies

1. Catalog exposes CAT-013 artifact tools.
2. `artifact.upload` reads a workspace file and emits invocation artifact payload.
3. `artifact.list` returns artifact candidates under workspace path.
4. `artifact.download` returns expected content in `utf8` and `base64` encodings.

## Build and push

```bash
cd e2e/tests/30-workspace-artifact-tools
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
