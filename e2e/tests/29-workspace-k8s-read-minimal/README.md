# E2E Test: Workspace K8s Read Minimal

This test validates the minimal Kubernetes read catalog:

- `k8s.get_pods`
- `k8s.get_images`
- `k8s.get_services`
- `k8s.get_deployments`
- `k8s.get_logs`

## What it verifies

1. Catalog exposes all minimal K8s read tools.
2. Each tool can be invoked successfully using the Kubernetes SDK backend in workspace service.
3. Artifacts are emitted for each invocation.

## Build and push

```bash
cd e2e/tests/29-workspace-k8s-read-minimal
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
