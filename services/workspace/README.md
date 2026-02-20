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
- Isolation adapter: local or Kubernetes workspace manager
- Policy adapter: static policy engine (RBAC + approval + path scoping)
- Artifact adapter: local filesystem

Production adapters (OPA, object storage, etc.) can be added without changing the app layer.

When `INVOCATION_STORE_BACKEND=valkey`, the store persists an invocation metadata envelope only
(`status`, `duration`, `errors`, refs). `output` and `logs` are persisted as artifacts and linked by
`output_ref` / `logs_ref`.

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

## Tool Families

- `fs.*` (read/write/search + lifecycle ops)
- `git.*` (status/diff/apply + lifecycle)
- `repo.*` (detect/build/test/analysis/summaries)
- `conn.*` (profile discovery)
- `nats.*`, `kafka.*`, `rabbit.*` (governed messaging)
- `redis.*`, `mongo.*` (governed data access)
- `security.*`, `image.*`, `sbom.*`, `license.*`, `deps.*`, `secrets.*`
- `k8s.*` (read + optional delivery tools)
- `artifact.*`
- `api.benchmark`

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
- `WORKSPACE_BACKEND` (`local|kubernetes`, default: `local`)
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
- `SESSION_STORE_BACKEND` (`memory|valkey`, default: `memory`)
- `SESSION_STORE_KEY_PREFIX` (default: `workspace:session`)
- `SESSION_STORE_TTL_SECONDS` (default: `86400`)
- `WORKSPACE_CONN_PROFILE_ENDPOINTS_JSON` (optional server-side map `profile_id -> endpoint`)
- `WORKSPACE_CONTAINER_STRICT_BY_DEFAULT` (`true|false`, default: `true`)
- `WORKSPACE_ENABLE_K8S_DELIVERY_TOOLS` (`true|false`, default: `false`)
- `WORKSPACE_RATE_LIMIT_PER_MINUTE` (default: `0` disabled; per-session invocation ceiling)
- `WORKSPACE_MAX_CONCURRENCY_PER_SESSION` (default: `0` disabled; per-session in-flight ceiling)

Kubernetes backend variables:

- `WORKSPACE_K8S_NAMESPACE` (default: `swe-ai-fleet`)
- `WORKSPACE_K8S_SERVICE_ACCOUNT` (optional)
- `WORKSPACE_K8S_RUNNER_IMAGE` (optional; defaults to adapter image)
- `WORKSPACE_K8S_INIT_IMAGE` (optional; defaults to adapter image)
- `WORKSPACE_K8S_WORKDIR` (default: `/workspace/repo`)
- `WORKSPACE_K8S_CONTAINER` (default: `runner`)
- `WORKSPACE_K8S_POD_PREFIX` (default: `ws`)
- `WORKSPACE_K8S_READY_TIMEOUT_SECONDS` (default: `120`)
- `WORKSPACE_K8S_GIT_AUTH_SECRET` (optional default secret name mounted in initContainer)
- `WORKSPACE_K8S_GIT_AUTH_METADATA_KEY` (default: `git_auth_secret`)
- `WORKSPACE_K8S_RUN_AS_USER` (default: `1000`)
- `WORKSPACE_K8S_RUN_AS_GROUP` (default: `1000`)
- `WORKSPACE_K8S_FS_GROUP` (default: `1000`)
- `WORKSPACE_K8S_READ_ONLY_ROOT_FS` (`true|false`, default: `false`)
- `WORKSPACE_K8S_AUTOMOUNT_SA_TOKEN` (`true|false`, default: `false`)
- `KUBECONFIG` (optional; fallback order: `$KUBECONFIG` -> `~/.kube/config` -> in-cluster)

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

# 3) Invoke a tool (approval required for fs.write_file)
curl -s http://localhost:50053/v1/sessions/<session_id>/tools/fs.write_file/invoke \
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
