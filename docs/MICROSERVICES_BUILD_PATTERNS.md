# Microservices Build Patterns

This document describes the build patterns and best practices used for gRPC microservices in this project.

## 🎯 Core Principles

### 1. Generate APIs During Container Build
**Never commit generated protobuf files to git.**

```dockerfile
# Copy protobuf spec
COPY specs/orchestrator.proto /app/specs/orchestrator.proto

# Generate gRPC code from protobuf during build
RUN mkdir -p /app/services/orchestrator/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs \
    --python_out=/app/services/orchestrator/gen \
    --grpc_python_out=/app/services/orchestrator/gen \
    --pyi_out=/app/services/orchestrator/gen \
    orchestrator.proto && \
    # Fix imports in generated files \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /app/services/orchestrator/gen/orchestrator_pb2_grpc.py && \
    # Create __init__.py \
    echo 'from . import orchestrator_pb2, orchestrator_pb2_grpc\n__all__ = ["orchestrator_pb2", "orchestrator_pb2_grpc"]' \
    > /app/services/orchestrator/gen/__init__.py
```

**Benefits:**
- ✅ Containers are self-contained and reproducible
- ✅ No generated code in git (cleaner repo, better diffs)
- ✅ Same .proto spec → same output always
- ✅ No drift between local and container environments
- ✅ CI/CD doesn't need Python to build containers

### 2. Use BuildKit Cache Mounts
**Dramatically speed up rebuilds with persistent caches.**

```dockerfile
# Syntax directive required for cache mounts
# syntax=docker/dockerfile:1

# APT package cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc g++

# Pip package cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt
```

**Performance:**
- First build: ~60 seconds
- Subsequent builds: ~10-15 seconds (5-6x faster)
- Cache is shared across builds on the same host

**Cache locations:**
- `/var/cache/apt` - Downloaded .deb packages
- `/var/lib/apt` - APT state
- `/root/.cache/pip` - Downloaded Python wheels

### 3. Layer Optimization
**Order Dockerfile instructions from least to most frequently changing.**

```dockerfile
# 1. Base image (rarely changes)
FROM python:3.11-slim

# 2. System dependencies (rarely changes)
RUN apt-get install gcc g++

# 3. Python dependencies (changes occasionally)
COPY requirements.txt .
RUN pip install -r requirements.txt

# 4. Protobuf spec (changes occasionally)
COPY specs/service.proto .
RUN python -m grpc_tools.protoc ...

# 5. Application code (changes frequently)
COPY src/ /app/src/
COPY services/myservice/ /app/services/myservice/
```

**Why this order?**
- Docker caches each layer
- Changing a layer invalidates all subsequent layers
- Putting stable things first maximizes cache hits

### 4. Security Best Practices
**Every container must run as non-root with minimal privileges.**

```dockerfile
# Create non-root user
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Kubernetes deployment
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: service
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: false
      runAsNonRoot: true
      runAsUser: 1000
      capabilities:
        drop:
          - ALL
```

### 5. .dockerignore
**Prevent copying generated files and caches into the build context.**

```
# Generated protobuf files - regenerated during build
gen/
*_pb2.py
*_pb2_grpc.py
*_pb2.pyi

# Python cache
__pycache__/
*.pyc
*.pyo
.Python

# Virtual environments
venv/
env/
```

## 🚫 Anti-Patterns to Avoid

### ❌ Committing Generated Code
```bash
git add services/*/gen/*.py  # DON'T DO THIS
```

**Problems:**
- Bloats repository
- Merge conflicts on generated code
- Can drift from .proto spec
- Unclear diffs in PRs

### ❌ Mocking in Production Servers
```python
# In production server.py - DON'T DO THIS
class MockAgent(Agent):
    def generate(self, task, ...):
        return "fake response"
```

**Problems:**
- Production server does nothing real
- Tests don't catch integration issues
- Confuses development vs production

**Solution:** Use dependency injection or raise NotImplementedError

### ❌ Using :latest Tags
```yaml
# In deployment - DON'T DO THIS
image: registry/service:latest
```

**Problems:**
- Not reproducible
- Can pull compromised images
- Difficult rollbacks

**Solution:** Use semantic versions: `v0.1.0`

### ❌ Running as Root
```dockerfile
# DON'T DO THIS - missing USER directive
FROM python:3.11-slim
CMD ["python", "server.py"]
```

**Problems:**
- Security vulnerability
- Violates principle of least privilege
- Fails security scans (SonarQube, etc.)

**Solution:** Always add `USER appuser` before CMD

## 📚 Complete Build Flow

### For Service Container:

```bash
# 1. Build with cache mounts (Podman or Docker)
podman build -t localhost:5000/swe-ai-fleet/orchestrator:v0.1.0 \
  -f services/orchestrator/Dockerfile .

# What happens:
# ├─ Install system deps (with cache)
# ├─ Install Python deps (with cache)
# ├─ Install grpcio-tools (with cache)
# ├─ Copy .proto spec
# ├─ Generate pb2 files from spec
# ├─ Fix imports with sed
# ├─ Create __init__.py
# ├─ Copy application code
# ├─ Create non-root user
# └─ Set user to appuser

# 2. Push to registry
podman push localhost:5000/swe-ai-fleet/orchestrator:v0.1.0

# 3. Deploy to Kubernetes
kubectl apply -f deploy/k8s/11-orchestrator-service.yaml
```

### For Integration Tests:

```bash
# Run integration tests (all in containers)
./scripts/run-integration-tests-podman.sh

# What happens:
# ├─ Build service container
# │  └─ APIs generated inside
# ├─ Build test-runner container
# │  └─ APIs generated inside
# ├─ Create podman network
# ├─ Start service container
# ├─ Wait for service to be ready
# ├─ Run test-runner container
# │  └─ Connects to service via gRPC
# └─ Cleanup containers and network
```

## 🔧 Configuration

### BuildKit/Podman Build Arguments

```bash
# Enable BuildKit (Docker)
export DOCKER_BUILDKIT=1

# Podman (BuildKit enabled by default)
podman build --format docker ...
```

### Cache Management

```bash
# View cache usage
podman system df

# Clear build cache
podman builder prune -af

# Keep cache but remove old data
podman builder prune --keep-storage 10GB
```

## 📊 Performance Comparison

### Without Cache Mounts:
```
Build time: 60-90 seconds every time
Cache hit: 0%
Network: Downloads same packages repeatedly
Disk: Creates duplicate layers
```

### With Cache Mounts:
```
First build: 60 seconds
Rebuild (code change): 10-15 seconds
Rebuild (deps change): 20-25 seconds
Cache hit: 80-90%
Network: Downloads once, reuses cached
Disk: Shared cache across builds
```

## 🎓 Lessons Learned

### 1. API Generation in Containers
**Problem:** Committing generated protobuf files causes merge conflicts and repo bloat.

**Solution:** Generate during container build from canonical .proto spec.

**Result:** Cleaner git history, reproducible builds, no drift.

### 2. Integration Tests Without Local Dependencies
**Problem:** Tests fail if pytest/grpcio not installed locally.

**Solution:** Run tests inside containers that have all dependencies.

**Result:** Tests work on any machine with just Podman/Docker installed.

### 3. Podman Socket Configuration
**Problem:** Testcontainers expects Docker socket.

**Solution:** Configure for Podman:
```bash
export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
export TESTCONTAINERS_RYUK_DISABLED="true"
systemctl --user start podman.socket
```

**Result:** Testcontainers works seamlessly with Podman.

### 4. Production vs Test Code Separation
**Problem:** Mixing test mocks in production server makes it non-functional.

**Solution:** 
- Production server returns `UNIMPLEMENTED` for missing features
- Unit tests use mocks in test files
- Integration tests verify infrastructure only
- Real implementations injected via dependency injection

**Result:** Clear separation, honest error messages, maintainable code.

## 🔗 Related Documentation

- [Orchestrator Service README](../services/orchestrator/README.md)
- [Integration Tests with Podman](../tests/integration/services/orchestrator/PODMAN_SETUP.md)
- [Docker BuildKit Cache](https://docs.docker.com/build/cache/)
- [Podman Build Documentation](https://docs.podman.io/en/latest/markdown/podman-build.1.html)

## 📝 Checklist for New Microservices

When creating a new gRPC microservice:

- [ ] Define .proto spec in `specs/`
- [ ] Create Dockerfile with:
  - [ ] `# syntax=docker/dockerfile:1` directive
  - [ ] Cache mounts for apt and pip
  - [ ] Protobuf generation during build
  - [ ] Import fixes with sed
  - [ ] Non-root user (UID 1000)
  - [ ] `USER appuser` before CMD
- [ ] Create `.dockerignore` excluding `gen/`
- [ ] Create `requirements.txt`
- [ ] Implement server with:
  - [ ] Proper error handling
  - [ ] UNIMPLEMENTED for missing features
  - [ ] No mocks in production code
  - [ ] Health checks
- [ ] Create K8s deployment with:
  - [ ] SecurityContext (pod and container)
  - [ ] Resource limits
  - [ ] Semantic version tags (not :latest)
  - [ ] Health probes
- [ ] Write unit tests (mock dependencies)
- [ ] Write integration tests (real containers)
- [ ] Document in README.md

## 🎯 Summary

**Key Pattern:** 
```
.proto spec (git) → Container build → Generated APIs → Production server
```

**Never:**
- ❌ Commit generated files
- ❌ Mock in production code
- ❌ Use :latest tags in K8s
- ❌ Run as root

**Always:**
- ✅ Generate APIs during build
- ✅ Use cache mounts
- ✅ Run as non-root
- ✅ Use semantic versions
- ✅ Test in containers

