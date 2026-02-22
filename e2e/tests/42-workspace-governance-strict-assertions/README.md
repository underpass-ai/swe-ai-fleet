# E2E Test: Workspace Governance Strict Assertions

This test validates strict governance contracts for external profile tools.

## What it verifies

1. Catalog exposes required governance tools (`conn.*`, `redis.*`, `nats.*`).
2. Approval-gated write tools without approval return:
   - `http_status=428`
   - `invocation.status=denied`
   - `error.code=approval_required`
3. Read-only write denials enforced by handlers return:
   - `http_status=500`
   - `invocation.status=failed`
   - `error.code=policy_denied`
4. Scope denials enforced by policy engine return:
   - `http_status=403`
   - `invocation.status=denied`
   - `error.code=policy_denied`
5. Session metadata endpoint override (`connection_profile_endpoints_json`) is ignored.
6. Allowlisted read operations still succeed with poisoned metadata endpoints.

## Runtime requirements

- Ephemeral dependencies stack must be up (`e2e-nats`), handled by `run-e2e-tests.sh`.

## Build and push

```bash
cd e2e/tests/42-workspace-governance-strict-assertions
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
