# E2E Test: Workspace FS Ops

This test validates dedicated filesystem lifecycle contracts in workspace service.

## What it verifies

1. Catalog exposes `fs.mkdir`, `fs.write_file`, `fs.copy`, `fs.move`, `fs.stat`, `fs.read_file`, `fs.delete`.
2. `fs.delete` enforces explicit approval (`approval_required`).
3. Fixture lifecycle works: `mkdir -> write_file -> copy -> stat -> move -> read_file`.
4. Path traversal is denied (`policy_denied`).
5. Workspace root delete is denied (`policy_denied`).
6. Directory delete without `recursive=true` is rejected (`invalid_argument`).
7. Recursive delete succeeds and `fs.stat` confirms `exists=false`.

## Build and push

```bash
cd e2e/tests/38-workspace-fs-ops
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
