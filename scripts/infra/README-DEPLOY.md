# Deployment Scripts Documentation

## Overview

This directory contains deployment scripts for the SWE AI Fleet microservices.

- **`deploy.sh`**: Stable entrypoint used by Makefile targets.
- **`fresh-redeploy-v2.sh`**: Main deployment engine with per-service support.

## Quick Start

### List Available Services

```bash
# Via script
./scripts/infra/fresh-redeploy-v2.sh --list-services

# Via Makefile
make list-services
```

### Deploy a Single Service

```bash
# Fast deploy (with cache) - Recommended for development
make deploy-service-fast SERVICE=planning

# Fresh deploy (no cache) - Recommended for production
make deploy-service SERVICE=planning

# Direct script usage
./scripts/infra/fresh-redeploy-v2.sh --service planning --fast
./scripts/infra/fresh-redeploy-v2.sh --service planning --fresh
```

### Deploy All Services

```bash
# Fast deploy all services
make fast-redeploy

# Fresh deploy all services
make fresh-redeploy

# Direct script usage
./scripts/infra/fresh-redeploy-v2.sh --fast
./scripts/infra/fresh-redeploy-v2.sh --fresh
```

## Available Services

| Service | Has NATS | Description |
|---------|----------|-------------|
| `orchestrator` | Yes | Multi-agent orchestration |
| `ray-executor` | No | GPU task execution |
| `context` | Yes | Knowledge graph context |
| `planning` | Yes | Story FSM & lifecycle |
| `planning-ui` | No | Planning UI frontend |
| `workflow` | Yes | Task FSM & RBAC |
| `task-derivation` | Yes | Task derivation service |

## Usage Examples

### Development Workflow

```bash
# 1. Make changes to planning service
# 2. Fast deploy (uses cache, faster builds)
make deploy-service-fast SERVICE=planning

# 3. Test changes
# 4. If issues, check logs
kubectl logs -n swe-ai-fleet -l app=planning --tail=100
```

### Production Deployment

```bash
# Fresh deploy (no cache, ensures clean build)
make deploy-service SERVICE=planning

# Or deploy all services
make fresh-redeploy
```

### Skip Build (Redeploy Only)

```bash
# Useful when you only want to update deployment config
./scripts/infra/fresh-redeploy-v2.sh --service planning --skip-build
```

### vLLM CUDA 13 Image Override

```bash
# Deploy vllm-server with a custom CUDA 13 image (no YAML edits)
make deploy-service-skip-build SERVICE=vllm-server \
  VLLM_SERVER_IMAGE=registry.example.com/your-namespace/vllm-openai:cu13
```

### Reset NATS Streams

```bash
# Deploy service and reset NATS streams
./scripts/infra/fresh-redeploy-v2.sh --service orchestrator --reset-nats
```

## Makefile Targets

| Target | Description | Usage |
|--------|-------------|-------|
| `make list-services` | List all available services | `make list-services` |
| `make deploy-service` | Deploy a service (fresh, no cache) | `make deploy-service SERVICE=planning` |
| `make deploy-service-fast` | Deploy a service (fast, with cache) | `make deploy-service-fast SERVICE=planning` |
| `make fresh-redeploy` | Deploy all services (fresh) | `make fresh-redeploy` |
| `make fast-redeploy` | Deploy all services (fast) | `make fast-redeploy` |

## Script Options

### `fresh-redeploy-v2.sh` Options

| Option | Description | Example |
|--------|-------------|---------|
| `-s, --service <name>` | Deploy specific service | `--service planning` |
| `--fast` | Use cache for faster builds | `--fast` |
| `--fresh` | Build without cache (default) | `--fresh` |
| `--skip-build` | Skip building images | `--skip-build` |
| `--reset-nats` | Reset NATS streams | `--reset-nats` |
| `-l, --list-services` | List available services | `--list-services` |
| `-h, --help` | Show help message | `--help` |

## Current Deployment Engine

### `fresh-redeploy-v2.sh`
- ✅ Deploy individual services or all services
- ✅ Fast (cache) or fresh (no cache) modes
- ✅ Better error messages and user feedback
- ✅ Service validation
- ✅ List available services
- ✅ More modular and maintainable

## Troubleshooting

### Service Not Found

```bash
# List available services
make list-services

# Verify service name spelling
./scripts/infra/fresh-redeploy-v2.sh --service <service-name> --list-services
```

### Build Failures

```bash
# Check build logs
tail -f /tmp/swe-ai-fleet-build-*.log

# Try fresh build (no cache)
make deploy-service SERVICE=planning
```

### Deployment Issues

```bash
# Check pod status
kubectl get pods -n swe-ai-fleet -l app=planning

# Check logs
kubectl logs -n swe-ai-fleet -l app=planning --tail=100

# Describe pod
kubectl describe pod -n swe-ai-fleet <pod-name>
```

### NATS Consumer Issues

If a service with NATS consumers is not starting:

```bash
# Check NATS streams
kubectl exec -n swe-ai-fleet -it <nats-pod> -- nats stream ls

# Restart service with NATS reset
./scripts/infra/fresh-redeploy-v2.sh --service orchestrator --reset-nats
```

## Best Practices

1. **Development**: Use `--fast` mode for faster iteration
2. **Production**: Use `--fresh` mode for clean builds
3. **Single Service**: Deploy only the service you're working on
4. **All Services**: Use `fresh-redeploy-v2.sh` without `--service`
5. **Testing**: Always verify deployment with `kubectl get pods` after deployment
