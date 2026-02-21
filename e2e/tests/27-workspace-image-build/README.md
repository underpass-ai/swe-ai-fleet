# E2E Test: Workspace Image Build

This test validates `image.build` in workspace runtime.

## What it verifies

1. Catalog exposes `image.build`.
2. Tool requires approval and executes with approved request.
3. Build output is structured and deterministic (`builder`, `simulated`, `image_ref`, `digest`).
4. Invocation artifacts include `image-build-report.json`.

## Runtime compatibility note

In some clusters, `buildah`/`podman` are installed but cannot execute real builds due to user-namespace limitations (for example `CLONE_NEWUSER: Function not implemented`).

For this case, workspace returns deterministic synthetic output instead of failing the invocation:

- `builder = synthetic`
- `simulated = true`

## Build and push

```bash
cd e2e/tests/27-workspace-image-build
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
