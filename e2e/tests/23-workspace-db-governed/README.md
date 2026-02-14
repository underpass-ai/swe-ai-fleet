# E2E Test: Workspace DB Governed

This test validates governance for Redis/Mongo read tools.

## What it verifies

1. Redis/Mongo read tools are present in catalog.
2. Write-style DB tools are absent from catalog.
3. Redis key-prefix policy enforces `policy_denied`.
4. Mongo database scoping enforces `policy_denied`.
5. Allowlisted DB reads are not blocked by policy.

## Build and push

```bash
cd e2e/tests/23-workspace-db-governed
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
