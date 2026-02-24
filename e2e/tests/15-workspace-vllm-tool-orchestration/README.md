# E2E Test: Workspace Tool Catalog Orchestration (data-driven)

This test validates broad coverage over the workspace tool catalog using a
**data-driven approach**: a YAML table (`tool_catalog.yaml`) declares every
tool invocation, its arguments, and expected outcome. The Python runner is a
generic loop that reads the table and executes each entry.

## What it verifies

1. Workspace API health and session bootstrap.
2. Dynamic tool catalog discovery from `/v1/sessions/{id}/tools`.
3. Coverage-oriented execution: one invocation per available tool.
4. Strict validation for filesystem tools and git lifecycle tools (when a repository is available).
5. Soft error handling for messaging, git degradation, and policy-denied writes.
6. Structured evidence (steps, catalog, invocations, final status).

## Adding a new tool

Add one entry to `tool_catalog.yaml`:

```yaml
- name: new.tool
  args: {key: "value"}
  approved: false
  strict: true
  checks:
    - field: some_field
      min: 1
```

No Python changes needed.

## Build and push

```bash
cd e2e/tests/15-workspace-vllm-tool-orchestration
make build-push
```

## Deploy and inspect

```bash
make deploy
make status
make logs
make delete
```

## Environment variables

- `WORKSPACE_URL` — workspace API endpoint (default: cluster-internal DNS)
- `WORKSPACE_AUTH_TOKEN` — optional trusted-header auth token
- `WORKSPACE_GIT_REPO_URL` — git repo for session setup (default: `octocat/Hello-World`)
- `WORKSPACE_GIT_REPO_REF` — optional git ref
- `EVIDENCE_FILE` — output path for evidence JSON

## Evidence output

- JSON evidence file written to `EVIDENCE_FILE`.
- Same JSON emitted to logs between `EVIDENCE_JSON_START` / `EVIDENCE_JSON_END` markers.
