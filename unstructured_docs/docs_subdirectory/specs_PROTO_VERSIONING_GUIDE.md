# Proto Versioning and Dependency Management Guide

**Version**: 1.0  
**Date**: 2025-10-30  
**Status**: Production Ready

---

## 🎯 Overview

This guide explains how to manage Protocol Buffer API definitions and their dependencies across SWE AI Fleet microservices.

**Key Principles:**
- ✅ All protos use semantic versioning (MAJOR.MINOR.PATCH)
- ✅ Breaking changes require major version bumps
- ✅ Services pin to specific proto versions
- ✅ Proto bundles are immutable once published
- ✅ Buf validates linting and breaking changes

---

## 📁 Directory Structure

```
specs/
├── fleet/                    # All service APIs
│   ├── context/v1/
│   ├── orchestrator/v1/
│   ├── ray_executor/v1/
│   ├── planning/v1/
│   ├── storycoach/v1/
│   └── workspace/v1/
├── buf.yaml                 # Buf configuration
├── buf.gen.yaml            # Code generation config
├── buf.lock                # Dependency lock (auto-generated)
├── VERSION                 # Current API version
├── CHANGELOG.md            # Version history
├── dependencies.yaml       # Service dependencies
└── Makefile                # Proto management commands
```

---

## 🛠️ Available Scripts

All scripts are in `scripts/specs/`:

### Core Scripts

| Script | Purpose | Example |
|--------|---------|---------|
| `validate-protos.sh` | Lint + breaking change detection | `./scripts/specs/validate-protos.sh` |
| `version-bump.sh` | Bump MAJOR/MINOR/PATCH version | `./scripts/specs/version-bump.sh auto` |
| `publish-proto-bundle.sh` | Build & push to registry | `./scripts/specs/publish-proto-bundle.sh` |
| `generate-docs.sh` | Generate HTML API docs | `./scripts/specs/generate-docs.sh` |
| `load-proto-deps.sh` | Download proto bundles | `./scripts/specs/load-proto-deps.sh --service=orchestrator` |
| `get-service-deps.sh` | Query dependencies.yaml | `./scripts/specs/get-service-deps.sh orchestrator` |

---

## 🔄 Common Workflows

### Developer Making Proto Changes

```bash
# 1. Edit proto file
vim specs/fleet/orchestrator/v1/orchestrator.proto

# 2. Validate changes
./scripts/specs/validate-protos.sh

# 3. Auto-bump version (detects breaking/non-breaking)
./scripts/specs/version-bump.sh auto

# 4. Commit
git add specs/
git commit -m "feat(api): add DeleteCouncil RPC"

# 5. Publish to registry
./scripts/specs/publish-proto-bundle.sh
```

### Service Developer Using Protos

```bash
# Check which proto versions a service needs
./scripts/specs/get-service-deps.sh orchestrator

# Download protos for local dev
./scripts/specs/load-proto-deps.sh --service=orchestrator --local

# In Dockerfile, use build args:
# ARG PROTO_VERSION=1.0.0
# COPY specs/fleet/orchestrator/v1 /app/specs
```

---

## 📋 Versioning Rules

### Breaking Changes (MAJOR bump)

❌ These changes **require** MAJOR version bump:

- Remove field, method, or service
- Rename field or method  
- Change field type (string → int, etc.)
- Change field number
- Remove enum value
- Change method signature (request/response)

**Example**: `orchestrator.proto` v1.0.0 → v2.0.0

```protobuf
message CreateCouncilRequest {
  string role = 1;
  // string description = 2;  // REMOVED - BREAKING
}
```

### Non-Breaking Changes (MINOR bump)

✅ These changes can be MINOR:

- Add new field (with default value)
- Add new method
- Add new enum value  
- Add new service
- Add new message type

**Example**: `orchestrator.proto` v1.0.0 → v1.1.0

```protobuf
service OrchestratorService {
  // Existing RPCs...
  
  // New RPC - backward compatible
  rpc GetStats(GetStatsRequest) returns (GetStatsResponse);
}
```

### Documentation (PATCH bump)

🔧 These changes can be PATCH:

- Documentation fixes
- Comment improvements
- Internal refactoring

**Example**: `orchestrator.proto` v1.0.0 → v1.0.1

---

## 🔗 Service Dependencies

Services declare their proto dependencies in `specs/dependencies.yaml`:

```yaml
services:
  orchestrator:
    version: "1.0.0"
    required:
      - orchestrator    # Own API
      - ray_executor    # Calls Ray Executor
      - context         # Queries context graph
```

### Querying Dependencies

```bash
# Get orchestrator's required proto versions
./scripts/specs/get-service-deps.sh orchestrator

# Output:
# 1.0.0
# orchestrator ray_executor context
```

---

## 🚀 Publishing Proto Bundles

### Publishing Process

```bash
# 1. Validate protos
cd specs && make validate

# 2. Bump version if needed
make minor    # or patch/major

# 3. Publish to registry
make publish

# 4. Verify publication
podman images | grep protos
```

### Registry Format

Bundles are published as:
```
registry.underpassai.com/swe-fleet/protos:v1.0.0
registry.underpassai.com/swe-fleet/protos:v1.1.0
registry.underpassai.com/swe-fleet/protos:v2.0.0
```

Each bundle contains all protos at that version.

---

## 🔍 Validation in CI/CD

### GitHub Actions Example

```yaml
name: Validate Protos

on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: bufbuild/buf-setup-action@v1
      - run: |
          cd specs
          make validate
```

### Breaking Change Detection

```bash
# In CI, run:
buf breaking --against '.git#branch=main'
```

If breaking changes detected, CI fails with message:
```
✗ BREAKING CHANGE: Field "description" removed from CreateCouncilRequest
```

---

## 📦 Using Protos in Service Dockerfiles

### Current Approach (Local COPY)

**Recommended for monorepo:**

```dockerfile
# Copy proto files from monorepo
COPY specs/fleet/orchestrator/v1/orchestrator.proto \
     /app/specs/fleet/orchestrator/v1/orchestrator.proto

# Generate code
RUN python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet/orchestrator/v1 \
    --python_out=/app/gen \
    orchestrator.proto
```

### Future Approach (Registry Download)

**For distributed services:**

```dockerfile
ARG PROTO_VERSION=1.0.0

# Download proto bundle
RUN curl -L registry.underpassai.com/v2/swe-fleet/protos/manifests/v${PROTO_VERSION} \
    | tar -xz -C /app/specs/

# Generate code
RUN python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet \
    --python_out=/app/gen \
    orchestrator/v1/orchestrator.proto
```

---

## 📚 Advanced Usage

### Custom Registry

```bash
REGISTRY=myregistry.com make publish
```

### Dry-Run Publishing

```bash
./scripts/specs/publish-proto-bundle.sh --dry-run
```

### Service-Specific Loading

```bash
# Load only orchestrator protos
./scripts/specs/load-proto-deps.sh --service=orchestrator --version=1.0.0

# Load all protos
./scripts/specs/load-proto-deps.sh --service=all --version=1.0.0
```

---

## 🐛 Troubleshooting

### "buf is not installed"

```bash
# Install buf
curl -sSL "https://github.com/bufbuild/buf/releases/download/v1.40.1/buf-$(uname -s)-$(uname -m)" \
  -o ~/.local/bin/buf
chmod +x ~/.local/bin/buf
```

### "Breaking changes detected but version not bumped"

```bash
# Auto-detect and bump
./scripts/specs/version-bump.sh auto

# Or manually bump major
./scripts/specs/version-bump.sh major
```

### "Proto bundle not found in registry"

```bash
# Check if bundle exists
podman images registry.underpassai.com/swe-fleet/protos

# Fall back to local
./scripts/specs/load-proto-deps.sh --local
```

---

## 📖 Additional Resources

- [API Versioning Strategy](../../API_VERSIONING_STRATEGY.md) - Full strategy doc
- [Buf Documentation](https://buf.build/docs/) - Official Buf docs
- [Protobuf Style Guide](https://protobuf.dev/programming-guides/style/) - Google style guide
- [Specs README](../specs/README.md) - Quick reference

---

## 🎓 Examples

See [examples](../../examples/) directory for:
- Breaking change examples
- Migration guides
- Dockerfile patterns
- CI/CD configurations



