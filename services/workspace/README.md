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
- `GET /metrics` (Prometheus exposition format)

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

The full, authoritative capability snapshot is generated from code at:

- `docs/CAPABILITY_CATALOG.md`

Image tooling runtime note:

- In some clusters, `buildah`/`podman` can be detected but fail at runtime with `CLONE_NEWUSER` user-namespace errors.
- Workspace now degrades `image.build`/`image.push` to deterministic synthetic mode for this specific incompatibility, instead of failing the invocation.
- Details and operational guidance: `docs/IMAGE_BUILD_RUNTIME_FALLBACK.md`.

Regenerate after catalog changes:

```bash
make -C services/workspace catalog-docs
```

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
- `WORKSPACE_AUTH_MODE` (`payload|trusted_headers`, default: `payload`)
- `WORKSPACE_AUTH_SHARED_TOKEN` (required when `WORKSPACE_AUTH_MODE=trusted_headers`)
- `WORKSPACE_AUTH_TENANT_HEADER` (default: `X-Workspace-Tenant-Id`)
- `WORKSPACE_AUTH_ACTOR_HEADER` (default: `X-Workspace-Actor-Id`)
- `WORKSPACE_AUTH_ROLES_HEADER` (default: `X-Workspace-Roles`)
- `WORKSPACE_AUTH_TOKEN_HEADER` (default: `X-Workspace-Auth-Token`)
- `WORKSPACE_CONN_PROFILE_ENDPOINTS_JSON` (optional server-side map `profile_id -> endpoint`)
- `WORKSPACE_CONN_PROFILE_HOST_ALLOWLIST_JSON` (optional server-side map `profile_id -> ["host", "*.domain", "CIDR"]`; when set, endpoints outside allowlist are rejected)
- `WORKSPACE_OTEL_ENABLED` (`true|false`, default: `false`)
- `WORKSPACE_OTEL_EXPORTER_OTLP_ENDPOINT` (optional OTLP HTTP endpoint `host:port` when OTel is enabled)
- `WORKSPACE_OTEL_EXPORTER_OTLP_INSECURE` (`true|false`, default: `false`; use plain HTTP OTLP)
- `WORKSPACE_VERSION` (optional service version label for telemetry resource attributes)
- `WORKSPACE_ENV` (optional deployment environment label for telemetry resource attributes)
- `WORKSPACE_CONTAINER_STRICT_BY_DEFAULT` (`true|false`, default: `true`)
- `WORKSPACE_CONTAINER_ALLOW_SYNTHETIC_FALLBACK` (`true|false`, default: `true`; set to `false` in production to force runtime-backed execution only)
- `WORKSPACE_ENABLE_K8S_DELIVERY_TOOLS` (`true|false`, default: `false`)
- `WORKSPACE_RATE_LIMIT_PER_MINUTE` (default: `0` disabled; per-session invocation ceiling)
- `WORKSPACE_RATE_LIMIT_PER_MINUTE_PER_PRINCIPAL` (default: `0` disabled; per-principal invocation ceiling shared by sessions with same `tenant_id` + `actor_id`)
- `WORKSPACE_MAX_CONCURRENCY_PER_SESSION` (default: `0` disabled; per-session in-flight ceiling)
- `WORKSPACE_MAX_OUTPUT_BYTES_PER_INVOCATION` (default: `0` disabled; deny invocation when output payload exceeds this JSON size)
- `WORKSPACE_MAX_ARTIFACTS_PER_INVOCATION` (default: `0` disabled; deny invocation when tool returns too many artifacts)
- `WORKSPACE_MAX_ARTIFACT_BYTES_PER_INVOCATION` (default: `0` disabled; deny invocation when artifact bytes exceed quota)

Kubernetes backend variables:

- `WORKSPACE_K8S_NAMESPACE` (default: `swe-ai-fleet`)
- `WORKSPACE_K8S_SERVICE_ACCOUNT` (optional)
- `WORKSPACE_K8S_RUNNER_IMAGE` (optional; defaults to adapter image)
- `WORKSPACE_K8S_RUNNER_IMAGE_BUNDLES_JSON` (optional JSON map `profile -> image`; selected via session metadata key below)
- `WORKSPACE_K8S_RUNNER_PROFILE_METADATA_KEY` (default: `runner_profile`)
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

Production runner images:

- Dockerfile targets are under `services/workspace/runner-images/Dockerfile` (`base`, `toolchains`, `secops`, `container`, `k6`, `fat`).
- Build/push helper: `scripts/workspace/runner-images.sh`.
- Detailed reference: `services/workspace/docs/RUNNER_IMAGES.md`.
- Make targets:
  - `make workspace-runner-list TAG=v0.1.0`
  - `make workspace-runner-build PROFILE=all TAG=v0.1.0`
  - `make workspace-runner-build-push PROFILE=all TAG=v0.1.0`

When `WORKSPACE_AUTH_MODE=trusted_headers`, session/invocation access is bound to the authenticated
`tenant_id` + `actor_id` from headers; `principal` in the request body is ignored for session creation.

Production note:

- `deploy/k8s/30-microservices/workspace.yaml` is configured for `trusted_headers`.
- `payload` mode should be reserved for local/e2e workflows.

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
