# Deployment & Redeployment Operations

**Status**: Production-ready flow  
**Namespace**: `swe-ai-fleet`  
**Registry**: `registry.underpassai.com/swe-ai-fleet`

This document defines the supported deploy operations for SWE AI Fleet.

## Quick Reference

```bash
# Build+push images (cache)
make deploy-build

# Build+push images (no-cache)
make deploy-build-no-cache

# Deploy all services (single deploy command)
make deploy

# Deploy all services + reset NATS streams
make deploy RESET_NATS=1

# Deploy one service
make deploy-service SERVICE=planning

# Verify system health
bash scripts/infra/verify-health.sh
```

## Initial Deployment

Prerequisites:

- Kubernetes context configured.
- Registry access configured.
- Cluster infra base available (namespace, NATS, Neo4j, Valkey).

Recommended first deploy:

```bash
make deploy RESET_NATS=1
```

## Standard Redeploy Workflow

After code/config changes:

```bash
# Default: cached build + deploy
make deploy
```

Useful variants:

```bash
# Force clean build
make deploy NO_CACHE=1

# Re-apply deployments without rebuilding images
make deploy SKIP_BUILD=1

# Deploy one service without rebuilding (example: external vLLM image)
make deploy-service SERVICE=vllm-server SKIP_BUILD=1 \
  VLLM_SERVER_IMAGE=registry.example.com/your-namespace/vllm-openai:cu13
```

## Verification

```bash
# Health summary
bash scripts/infra/verify-health.sh

# Pods
kubectl get pods -n swe-ai-fleet

# Rollout check
kubectl rollout status deployment/planning -n swe-ai-fleet --timeout=120s

# Logs
kubectl logs -n swe-ai-fleet -l app=planning --tail=100
```

## Troubleshooting

See `deploy/k8s/K8S_TROUBLESHOOTING.md`.

## Best Practices

1. Run tests before deploy.
2. Use `make deploy` / `make deploy-service` instead of manual kubectl image patching.
3. Use `NO_CACHE=1` only when you need a clean rebuild.
4. Verify rollout and logs after each deploy.
