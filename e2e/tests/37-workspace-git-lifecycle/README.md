# E2E Test: Workspace Git Lifecycle

This test validates dedicated Git lifecycle contracts in workspace service.

## What it verifies

1. Catalog exposes `git.checkout`, `git.log`, `git.show`, `git.branch_list`, `git.commit`, `git.fetch`, `git.pull`, `git.push`.
2. Session with `platform_admin` can access high-risk `git.push` capability.
3. `allowed_git_ref_prefixes` enforcement denies checkout outside allowlist.
4. `git.checkout` + `git.commit` create a real commit on a feature branch.
5. `git.log` and `git.show` return structured history/details for the branch.
6. `git.push` requires approval (`approval_required`).
7. `git.push` denies non-allowlisted remote (`policy_denied`).
8. `git.fetch`, `git.pull`, and allowlisted `git.push` execute with valid policy path (success or runtime Git failure such as auth/network).

## Build and push

```bash
cd e2e/tests/37-workspace-git-lifecycle
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
