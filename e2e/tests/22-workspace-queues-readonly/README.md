# E2E Test: Workspace Queues Readonly

This test validates queue tool governance for workspace external tools.

## What it verifies

1. Queue read tools are present in catalog for `devops` sessions.
2. Queue write tools are present but require explicit approval.
3. Read-only profiles block queue writes even when approved.
4. Subject/topic/queue allowlists enforce `policy_denied`.
5. Allowlisted queue requests are not blocked by policy.

## Build and push

```bash
cd e2e/tests/22-workspace-queues-readonly
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
