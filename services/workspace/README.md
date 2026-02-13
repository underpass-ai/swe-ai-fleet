# Workspace Execution Service

Go microservice that provides:

- isolated workspace sessions (ephemeral filesystem root per session),
- structured tool catalog (capabilities with policy metadata),
- policy-enforced tool invocation (no free-form shell endpoint),
- deterministic JSON responses with stable error codes,
- invocation logs and artifact persistence.

## Current Scope

This service is an **execution-plane runtime skeleton** intended for integration with the orchestrator:

- Transport: HTTP/JSON
- Isolation adapter: local workspace manager (dev mode)
- Policy adapter: static policy engine (RBAC + approval + path scoping)
- Artifact adapter: local filesystem

Production adapters (Kubernetes workspaces, OPA, object storage, etc.) can be added without changing the app layer.

## API

### Health

- `GET /healthz`

### Sessions

- `POST /v1/sessions`
- `DELETE /v1/sessions/{session_id}`

### Capability catalog

- `GET /v1/sessions/{session_id}/tools`

### Tool invocation

- `POST /v1/sessions/{session_id}/tools/{tool_name}/invoke`

### Invocation observability

- `GET /v1/invocations/{invocation_id}`
- `GET /v1/invocations/{invocation_id}/logs`
- `GET /v1/invocations/{invocation_id}/artifacts`

## Tool Families (initial)

- `fs.list`
- `fs.read`
- `fs.write`
- `fs.search`
- `git.status`
- `git.diff`
- `git.apply_patch`
- `repo.run_tests`

Each tool includes metadata for:

- `scope`
- `side_effects`
- `risk_level`
- `requires_approval`
- `idempotency`
- `constraints` (timeouts/retries/output)
- `observability` (trace/span names)

## Environment variables

- `PORT` (default: `50053`)
- `WORKSPACE_ROOT` (default: `/tmp/swe-workspaces`)
- `ARTIFACT_ROOT` (default: `/tmp/swe-artifacts`)
- `LOG_LEVEL` (`debug|info|warn|error`, default: `info`)
- `INVOCATION_STORE_BACKEND` (`memory|valkey`, default: `memory`)
- `VALKEY_ADDR` (optional; if unset, uses `VALKEY_HOST:VALKEY_PORT`)
- `VALKEY_HOST` (default: `valkey.swe-ai-fleet.svc.cluster.local`)
- `VALKEY_PORT` (default: `6379`)
- `VALKEY_DB` (default: `0`)
- `VALKEY_PASSWORD` (optional)
- `INVOCATION_STORE_KEY_PREFIX` (default: `workspace:invocation`)
- `INVOCATION_STORE_TTL_SECONDS` (default: `86400`)

## Run

```bash
go run ./cmd/workspace
```

Or with local Makefile:

```bash
make run
```

## Example flow

```bash
# 1) Create session
curl -s http://localhost:50053/v1/sessions \
  -H 'content-type: application/json' \
  -d '{
    "principal": {"tenant_id":"demo","actor_id":"alice","roles":["developer"]},
    "source_repo_path":"/workspace",
    "allowed_paths":["."],
    "expires_in_seconds": 3600
  }'

# 2) List tools for session
curl -s http://localhost:50053/v1/sessions/<session_id>/tools

# 3) Invoke a tool (approval required for fs.write)
curl -s http://localhost:50053/v1/sessions/<session_id>/tools/fs.write/invoke \
  -H 'content-type: application/json' \
  -d '{
    "approved": true,
    "args": {"path":"notes/demo.txt","content":"hola"}
  }'
```

## Tests

```bash
go test ./...
```

Coverage gate for core execution packages (`internal/app` + `internal/adapters`) at 80%:

```bash
make coverage-core COVERAGE_MIN=80
```

## Troubleshooting

If you hit `curl: (7) failed to open socket: Operation not permitted`, see:

- `deploy/k8s/WORKSPACE_CURL_SOCKET_ISSUE.md`
