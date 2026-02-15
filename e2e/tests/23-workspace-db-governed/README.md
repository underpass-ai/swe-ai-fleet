# E2E Test: Workspace DB Governed

This test validates governance for Redis/Mongo tools with controlled writes.

## What it verifies

1. Redis/Mongo governed tools are present in catalog.
2. Mongo write-style tools remain absent from catalog.
3. Redis key-prefix policy enforces `policy_denied`.
4. Redis write tools are blocked when not approved (`approval_required` or `policy_denied`).
5. Mongo database scoping enforces `policy_denied`.
6. Allowlisted DB reads are not blocked by policy.
7. Redis write operations remain denied for `dev.redis` (read-only profile) even with approval.

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
