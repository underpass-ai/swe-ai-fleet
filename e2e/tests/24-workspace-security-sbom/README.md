# E2E Test: Workspace Security + SBOM

This test validates the new supply-chain security tools in workspace:

1. `security.scan_dependencies`
2. `sbom.generate`

## What it verifies

1. Required tools are exposed in catalog.
2. A minimal Go workspace can be created with `fs.write_file`.
3. `security.scan_dependencies` succeeds and returns structured dependency output.
4. `sbom.generate` succeeds and reports `sbom.cdx.json`.
5. Invocation artifact metadata includes `sbom.cdx.json`.

## Build and push

```bash
cd e2e/tests/24-workspace-security-sbom
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
