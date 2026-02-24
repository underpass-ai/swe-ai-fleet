# E2E Test: Workspace vLLM Tool Orchestration

This test validates a more complex `workspace` + `vllm-server` integration in Kubernetes.

## What it verifies

1. Workspace API health and session bootstrap.
2. Dynamic tool catalog discovery from `/v1/sessions/{id}/tools`.
3. vLLM planning step that returns an ordered tool sequence based on the discovered catalog.
4. Coverage-oriented execution: one invocation per available tool (with support for old/new tool naming).
5. Strict validation for filesystem tools and explicit coverage for git lifecycle tools (`checkout`, `branch_list`, `log`, `show`, `fetch`) when a repository is available.
6. Structured evidence is produced (steps, catalog, planning, invocations, and final status).

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

- `WORKSPACE_URL` (default in job): `http://workspace.swe-ai-fleet.svc.cluster.local:50053`
- `VLLM_CHAT_URL` (default in job): `http://vllm-server-service.swe-ai-fleet.svc.cluster.local:8000/v1/chat/completions`
- `VLLM_MODEL` (default in job): `Qwen/Qwen3-0.6B`
- `REQUIRE_VLLM` (`true|false`, default in job: `true`)
- `STRICT_VLLM_PLAN` (`true|false`, default in job: `false`)
- `WORKSPACE_GIT_REPO_URL` (default in job): `https://github.com/octocat/Hello-World.git`
- `WORKSPACE_GIT_REPO_REF` (default in job): empty
- `EVIDENCE_FILE` (default in script): `/tmp/e2e-ws-vllm-<timestamp>-evidence.json`

Set `REQUIRE_VLLM=false` to allow deterministic fallback order when vLLM is unavailable.

## Evidence output

- The test writes a JSON evidence file to `EVIDENCE_FILE`.
- The same JSON is emitted to logs between markers:
  - `EVIDENCE_JSON_START`
  - `EVIDENCE_JSON_END`
