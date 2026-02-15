# E2E Test: Workspace Tool Execution

This test validates the new `workspace` microservice end-to-end in Kubernetes.

## What it verifies

1. Workspace API health and tool catalog availability.
2. Tool execution from API entrypoint (`fs.write` + `fs.read`) modifies files inside the session workspace.
3. Multi-agent isolation: two independent sessions use the same path with different contents and do not interfere.
4. Policy server-side enforcement:
   - unapproved `fs.write_*` call returns `approval_required`.
   - out-of-scope path call returns `policy_denied`.
5. VLLM prompt-driven execution: model returns a structured tool call (`fs.write`), the call is executed, and result is verified.
6. Structured evidence is produced (steps, sessions, invocations, and final status).

## Build and push

```bash
cd e2e/tests/14-workspace-tool-execution
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
- `EVIDENCE_FILE` (default in script): `/tmp/e2e-workspace-14-<timestamp>-evidence.json`

Set `REQUIRE_VLLM=false` if you only want to validate workspace API behavior without LLM dependency.

## Evidence output

- The test writes a JSON evidence file to `EVIDENCE_FILE`.
- The same JSON is emitted to logs between markers:
  - `EVIDENCE_JSON_START`
  - `EVIDENCE_JSON_END`
