# E2E Test: Workspace Profiles Governance

This test validates policy enforcement for external connector tools in workspace.

## What it verifies

1. Workspace health and external tool visibility for a `devops` session.
2. `allowed_profiles` enforcement denies tools using non-allowed profiles.
3. `allowed_redis_key_prefixes` enforcement denies keys outside allowed prefixes.
4. `allowed_rabbit_queues` enforcement denies queues outside allowed prefixes.
5. Mongo database scoping is enforced by tool handler before network execution.

## Build and push

```bash
cd e2e/tests/21-workspace-profiles-governance
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

- The test writes a JSON evidence file to `EVIDENCE_FILE`.
- The same JSON is emitted to logs between:
  - `EVIDENCE_JSON_START`
  - `EVIDENCE_JSON_END`
