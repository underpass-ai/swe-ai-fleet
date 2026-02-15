# E2E Test: Workspace K8s Delivery Controlled

This test validates controlled Kubernetes delivery operations in workspace service.

## What it verifies

1. Catalog exposes `k8s.apply_manifest`, `k8s.rollout_status`, `k8s.restart_deployment`.
2. `k8s.apply_manifest` succeeds in an allowlisted namespace.
3. `k8s.rollout_status` succeeds for an applied deployment.
4. `k8s.restart_deployment` succeeds and returns `restarted_at`.
5. Namespace allowlist is enforced (`policy_denied` outside allowlist).
6. Manifest kind allowlist is enforced (`policy_denied` for unsupported kind).

## Build and push

```bash
cd e2e/tests/35-workspace-k8s-delivery-controlled
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
