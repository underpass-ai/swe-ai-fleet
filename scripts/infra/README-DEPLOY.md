# Deployment Scripts

This folder keeps the deploy/cleanup entrypoints used by `Makefile`.

## Stable Commands

```bash
# Build+push all services (cache)
make deploy-build

# Build+push all services (no cache)
make deploy-build-no-cache

# Deploy all services (single deploy command)
make deploy
```

## Service Deploy

```bash
# Deploy one service (cache build by default)
make deploy-service SERVICE=planning

# Deploy one service with no-cache build
make deploy-service SERVICE=planning NO_CACHE=1

# Redeploy one service without rebuilding
make deploy-service SERVICE=vllm-server SKIP_BUILD=1 \
  VLLM_SERVER_IMAGE=registry.example.com/your-namespace/vllm-openai:cu13
```

Optional flags for `make deploy` / `make deploy-service`:

- `NO_CACHE=1`: force no-cache build.
- `SKIP_BUILD=1`: redeploy using existing image tags.
- `RESET_NATS=1`: run NATS stream reset during deploy.
- `WITH_E2E=1`: only for `make deploy`, build+push E2E images after deploy.

## Cleanup and Prune

```bash
# Clear jobs + Valkey + Neo4j + NATS + MinIO workspace buckets
make cluster-clear

# Keep only latest 2 service image tags
make service-image-prune KEEP=2

# Keep only latest 2 E2E image tags
make e2e-image-prune KEEP=2
```

Optional:

- `DRY_RUN=1`: preview prune actions without deletion.
- `REGISTRY=...`: override default `registry.underpassai.com/swe-ai-fleet`.

## Entry Scripts

- `scripts/infra/deploy.sh`: stable CLI wrapper (`all|service|list-services`).
- `scripts/infra/fresh-redeploy-v2.sh`: deploy engine used internally by wrapper.
- `scripts/infra/cluster-clear.sh`: runtime state cleanup.
- `scripts/infra/prune-service-images.sh`: service image tag pruning.
- `scripts/e2e/prune-images.sh`: E2E image tag pruning.
