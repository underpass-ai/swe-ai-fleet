# E2E Test: Workspace Security Container + License

This test validates the next security tools in workspace:

1. `security.scan_container`
2. `security.license_check`

## What it verifies

1. Required tools are exposed in catalog.
2. A workspace fixture is created with `go.mod` and `Dockerfile`.
3. `security.scan_container` succeeds and returns structured output with scanner `trivy` or `heuristic-dockerfile` (findings may be zero on clean Trivy runs).
4. `security.license_check` succeeds and reports policy `fail` when `unknown_policy=deny`.
5. Invocation artifacts include:
   - `container-scan-findings.json`
   - `license-check-report.json`

## Build and push

```bash
cd e2e/tests/25-workspace-security-container-license
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
