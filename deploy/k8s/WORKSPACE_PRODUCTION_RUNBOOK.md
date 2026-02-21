# Workspace Production Runbook (Kubernetes)

## Scope

Operational runbook for validating the `workspace` microservice in a **production cluster**, including:

- Kubernetes control plane health
- node and GPU availability
- in-cluster service connectivity
- `workspace` deployment and smoke tests
- interpretation of `curl` errors

## Validation Snapshot (executed on February 13, 2026)

The following checks were executed from this repo environment against the live cluster:

1. Kubernetes API and versions:
- `kubectl version` returned:
  - Client `v1.35.0`
  - Server `v1.34.1`

2. Cluster reachability:
- `kubectl cluster-info` reported control plane at `https://k8s.local:6443`

3. Node health and GPU capacity:
- `kubectl get nodes -o wide`:
  - `wrx80-node1` in `Ready` state
- `kubectl get nodes ... custom-columns`:
  - `CPU=32`
  - `MEMORY=527995848Ki`
  - `GPU capacity=8`
  - `GPU allocatable=8`

4. NVIDIA operator stack:
- Namespace `nvidia` present.
- Device plugin, toolkit, dcgm-exporter and validator pods in `Running`/`Completed` states.

5. Real GPU consumption:
- Running pods requesting GPU:
  - `ray/ray-gpu-gpu-workers-worker-7dkf6` (`1/1` GPU)
  - `ray/ray-gpu-gpu-workers-worker-p862p` (`1/1` GPU)
  - `swe-ai-fleet/vllm-server-5bb4d568cb-x7mk8` (`1/1` GPU)
- `nvidia-smi -L` executed inside `vllm` and `ray` pods returned visible RTX 3090 devices.
- `kubectl describe node wrx80-node1` showed:
  - `nvidia.com/gpu: 8` allocatable
  - `nvidia.com/gpu: 3` currently allocated

6. `workspace` service state:
- In namespace `swe-ai-fleet`, `workspace` was **not deployed** at snapshot time:
  - `kubectl get deploy -n swe-ai-fleet -o wide` -> no `workspace` deployment
  - `kubectl get svc -n swe-ai-fleet workspace` -> `NotFound`
  - `kubectl get endpoints -n swe-ai-fleet workspace` -> `NotFound`
- In-cluster connectivity test from a debug pod:
  - `vllm /v1/models` responded OK
  - `workspace.swe-ai-fleet.svc.cluster.local` failed DNS resolution (service missing)

## Why `curl` can fail in this context

When you see:

```text
curl: (7) failed to open socket: Operation not permitted
```

possible causes are:

1. Local sandbox/network restrictions from the caller environment.
2. Kubernetes `NetworkPolicy` egress deny.
3. The target service is not deployed (or has no endpoints).
4. DNS/service naming mismatch.

In this production snapshot, for `workspace`, the immediate blocker is **service absence** (not DNS/network policy misconfiguration).

## Post-Deploy Validation (executed on February 13, 2026)

After publishing and deploying `workspace`, the service became operational:

- Deployment image:
  - `registry.underpassai.com/swe-ai-fleet/workspace:v0.1.0-20260213-202832`
- Deployment status:
  - `1/1 ready`
- Service endpoint:
  - `10.109.109.211:50053`
- Backing pod endpoint:
  - `10.244.253.200:50053`

In-cluster smoke test (real API calls) returned:

```text
health_ok
session_created:session-700696632e49906b
tools_ok
fs_write_ok
fs_read_ok
session_closed
SMOKE_OK
```

This confirms:

1. `workspace` health endpoint is reachable in cluster.
2. Session lifecycle works (`create` + `close`).
3. Catalog exposure is correct (`fs.read` and `fs.write` present).
4. Tool execution from API effectively mutates and reads data in the workspace.

## Persistence Validation (restart-safe invocations)

The service is configured with:

- `INVOCATION_STORE_BACKEND=valkey`
- `INVOCATION_STORE_TTL_SECONDS=86400`

Validation executed on February 13, 2026:

1. Created a session and invoked tools, producing invocation IDs:
   - `inv-5f101c0f08454771`
   - `inv-9a12e03ea5cb1955`
2. Restarted deployment:
   - `kubectl rollout restart deployment/workspace -n swe-ai-fleet`
3. Queried both IDs after restart:
   - `GET /v1/invocations/{id}` returned `status: succeeded`

Result:
- invocation metadata survived pod restart (state persisted in Valkey instead of in-process memory).

## Production Deployment Procedure for `workspace`

Use one of these:

```bash
# Recommended pipeline path
make deploy-workspace

# Or direct manifest apply
kubectl apply -f deploy/k8s/30-microservices/workspace.yaml
kubectl apply -f deploy/k8s/30-microservices/workspace-hpa.yaml

# Optional but recommended: egress hardening
kubectl apply -f deploy/k8s/30-microservices/workspace-networkpolicy.yaml
```

Then verify:

```bash
kubectl rollout status deployment/workspace -n swe-ai-fleet --timeout=180s
kubectl get deploy,svc,pods -n swe-ai-fleet -l app=workspace -o wide
kubectl get endpoints -n swe-ai-fleet workspace -o wide
kubectl get hpa -n swe-ai-fleet workspace
kubectl get networkpolicy -n swe-ai-fleet workspace-egress-restricted
```

Expected:
- deployment `AVAILABLE=1`
- service exists on `50053/TCP`
- endpoints list one or more pod IPs

## Runner Images by Bundle (recommended)

`workspace` supports server-side bundle selection for session pods:

- default runner image via `WORKSPACE_K8S_RUNNER_IMAGE`
- optional bundle map via `WORKSPACE_K8S_RUNNER_IMAGE_BUNDLES_JSON`
- selector metadata key via `WORKSPACE_K8S_RUNNER_PROFILE_METADATA_KEY` (default `runner_profile`)

Behavior:

- if session metadata includes `runner_profile=<profile>`, workspace resolves the image from the server-side bundle map.
- unknown profiles are rejected (`create session` fails).
- callers cannot inject arbitrary image refs through metadata.

Example metadata in `POST /v1/sessions`:

```json
{
  "metadata": {
    "runner_profile": "toolchains"
  }
}
```

## Optional: Enable K8s Delivery Tools (sandbox/dev only)

Default production posture keeps delivery tools disabled and runs `workspace` with
`workspace-runtime` service account.

To enable controlled delivery tools (`k8s.apply_manifest`, `k8s.rollout_status`,
`k8s.restart_deployment`) in a non-production namespace:

```bash
# 1) Enable delivery tools
kubectl set env deployment/workspace -n swe-ai-fleet \
  WORKSPACE_ENABLE_K8S_DELIVERY_TOOLS=true

# 2) Switch API pod identity to the delivery service account
kubectl patch deployment workspace -n swe-ai-fleet --type=merge \
  -p '{"spec":{"template":{"spec":{"serviceAccountName":"workspace-delivery"}}}}'

# 3) Rollout and verify
kubectl rollout status deployment/workspace -n swe-ai-fleet --timeout=180s
```

## Production AuthN/AuthZ (trusted headers mode)

By default the service accepts `principal` from request payload for local/e2e workflows.
For production, switch to trusted header mode so callers cannot forge roles in body:

```bash
# 1) Create/update shared token secret used by gateway/orchestrator
kubectl create secret generic workspace-auth -n swe-ai-fleet \
  --from-literal=shared_token='<strong-random-token>' \
  --dry-run=client -o yaml | kubectl apply -f -

# 2) Enable trusted headers mode
kubectl set env deployment/workspace -n swe-ai-fleet \
  WORKSPACE_AUTH_MODE=trusted_headers

# 3) Rollout
kubectl rollout status deployment/workspace -n swe-ai-fleet --timeout=180s
```

Required headers per request in `trusted_headers` mode:

- `X-Workspace-Auth-Token`
- `X-Workspace-Tenant-Id`
- `X-Workspace-Actor-Id`
- `X-Workspace-Roles` (optional but recommended)

In this mode:

- `POST /v1/sessions` ignores `principal` from body and uses authenticated headers.
- Session and invocation routes are restricted to the same `tenant_id` + `actor_id`.

## Production Container Runtime Posture (disable simulation)

To avoid synthetic `container.*` results in production, force runtime-backed execution:

```bash
kubectl set env deployment/workspace -n swe-ai-fleet \
  WORKSPACE_CONTAINER_ALLOW_SYNTHETIC_FALLBACK=false \
  WORKSPACE_CONTAINER_STRICT_BY_DEFAULT=true

kubectl rollout status deployment/workspace -n swe-ai-fleet --timeout=180s
```

With this posture:

- `strict:false` requests are effectively treated as strict.
- if no runtime is available, `container.*` invocations fail with `execution_failed` instead of simulated success.

RBAC sanity checks:

```bash
# runtime SA must not mutate deployments
kubectl auth can-i create deployments -n swe-ai-fleet \
  --as=system:serviceaccount:swe-ai-fleet:workspace-runtime

# delivery SA can mutate delivery resources
kubectl auth can-i create deployments -n swe-ai-fleet \
  --as=system:serviceaccount:swe-ai-fleet:workspace-delivery
kubectl auth can-i update configmaps -n swe-ai-fleet \
  --as=system:serviceaccount:swe-ai-fleet:workspace-delivery
```

To return to default posture:

```bash
kubectl set env deployment/workspace -n swe-ai-fleet \
  WORKSPACE_ENABLE_K8S_DELIVERY_TOOLS=false
kubectl patch deployment workspace -n swe-ai-fleet --type=merge \
  -p '{"spec":{"template":{"spec":{"serviceAccountName":"workspace-runtime"}}}}'
kubectl rollout status deployment/workspace -n swe-ai-fleet --timeout=180s
```

## In-Cluster Smoke Test (post-deploy)

Run from a debug pod in `swe-ai-fleet`:

```bash
kubectl run -n swe-ai-fleet ws-smoke \
  --image=docker.io/curlimages/curl:8.8.0 \
  --restart=Never --rm -i --command -- sh -lc '
set -e
echo "[health]"
curl -sS http://workspace.swe-ai-fleet.svc.cluster.local:50053/healthz
'
```

Then API flow:

1. `POST /v1/sessions`
2. `GET /v1/sessions/{id}/tools`
3. `POST /v1/sessions/{id}/tools/fs.write/invoke` (`approved=true`)
4. `POST /v1/sessions/{id}/tools/fs.read/invoke`

Validation criterion:
- content written by `fs.write` is read back by `fs.read` in the same session workspace.

Metrics check:

```bash
kubectl run -n swe-ai-fleet ws-metrics \
  --image=docker.io/curlimages/curl:8.8.0 \
  --restart=Never --rm -i --command -- sh -lc '
set -e
curl -sS http://workspace.swe-ai-fleet.svc.cluster.local:50053/metrics | head -n 40
'
```

Optional tracing enablement (OpenTelemetry):

```bash
kubectl set env deployment/workspace -n swe-ai-fleet \
  WORKSPACE_OTEL_ENABLED=true \
  WORKSPACE_OTEL_EXPORTER_OTLP_ENDPOINT='<otel-collector-host:4318>' \
  WORKSPACE_OTEL_EXPORTER_OTLP_INSECURE=true

kubectl rollout status deployment/workspace -n swe-ai-fleet --timeout=180s
```

Connection profile endpoint allowlist (recommended):

```bash
kubectl set env deployment/workspace -n swe-ai-fleet \
  WORKSPACE_CONN_PROFILE_HOST_ALLOWLIST_JSON='{"dev.nats":["*.svc.cluster.local"],"dev.redis":["10.0.0.0/8"]}'

kubectl rollout status deployment/workspace -n swe-ai-fleet --timeout=180s
```

## Optional End-to-End Validation

After deployment, run:

```bash
./e2e/run-e2e-tests.sh --start-from 14 --skip-build
```

Test `14-workspace-tool-execution` validates:
- tool catalog availability
- real `fs.write/fs.read` execution from API
- multi-agent workspace isolation
- vLLM prompt-driven structured tool-call execution

## Quick Triage Checklist

1. `kubectl get deploy -n swe-ai-fleet workspace`
2. `kubectl get svc -n swe-ai-fleet workspace`
3. `kubectl get endpoints -n swe-ai-fleet workspace`
4. `kubectl logs -n swe-ai-fleet -l app=workspace --tail=200`
5. `kubectl get networkpolicy -n swe-ai-fleet`
6. In-cluster `curl` to `/healthz` from a debug pod
7. If GPU workloads fail, verify:
   - `kubectl get pods -n nvidia`
   - `kubectl describe node wrx80-node1 | rg "nvidia.com/gpu"`
