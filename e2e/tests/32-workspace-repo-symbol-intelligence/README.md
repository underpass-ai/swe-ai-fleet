# E2E Test: Workspace Repo Symbol Intelligence (CAT-015)

This test validates:

- `repo.changed_files`
- `repo.symbol_search`
- `repo.find_references`

## What it verifies

1. Catalog exposes CAT-015 tools.
2. `repo.changed_files` returns structured changed file metadata.
3. `repo.symbol_search` returns deterministic symbol matches.
4. `repo.find_references` can exclude declarations.
5. All tools emit structured artifacts for evidence.

## Build and push

```bash
cd e2e/tests/32-workspace-repo-symbol-intelligence
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
