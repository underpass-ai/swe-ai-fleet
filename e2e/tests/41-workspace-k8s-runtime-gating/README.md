# E2E Test: Workspace K8s Runtime Gating

This test validates runtime-aware gating for cluster-scope tools when workspace backend is `local`.

## What it verifies

1. A session created on local backend has `runtime.kind=local`.
2. `ListTools` does not expose `k8s.*` tools in local runtime.
3. Direct invocation of a `k8s.*` tool still resolves capability but is denied with:
   - `error.code=policy_denied`
   - message mentioning kubernetes runtime requirement
4. Approval does not bypass runtime gating.
5. Non-cluster tools (for example `fs.list`) remain usable.

## Runtime model

- The test container starts `workspace-service` locally (`WORKSPACE_BACKEND=local`) and exercises its HTTP API on `127.0.0.1:50053`.
- No external workspace runtime deployment is required.

## Build and push

```bash
cd e2e/tests/41-workspace-k8s-runtime-gating
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
