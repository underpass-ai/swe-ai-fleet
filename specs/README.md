# API Definitions - SWE AI Fleet

This directory contains all Protocol Buffer API definitions for SWE AI Fleet microservices.

## 📋 Directory Structure

```
specs/
├── fleet/                      # All service APIs
│   ├── context/v1/
│   ├── orchestrator/v1/
│   ├── ray_executor/v1/
│   ├── planning/v1/
│   ├── storycoach/v1/
│   └── workspace/v1/
├── buf.yaml                   # Buf configuration
├── buf.gen.yaml              # Code generation config
├── buf.lock                  # Dependency lock (auto-generated)
├── VERSION                   # Current API version
├── CHANGELOG.md              # Version history
└── README.md                 # This file
```

## 📌 Current Version

Current API version: **v1.0.0** (see [CHANGELOG.md](CHANGELOG.md))

## 🏷️ Namespace Convention

All services use `fleet.<service>.v<major>`:

- `fleet.context.v1` - Decision graph management
- `fleet.orchestrator.v1` - Multi-agent coordination
- `fleet.ray_executor.v1` - Distributed execution
- `fleet.planning.v1` - User story workflow
- `fleet.storycoach.v1` - Story refinement
- `fleet.workspace.v1` - Code evaluation

## 🛠️ Developer Workflow

### Validate Protos

```bash
# Full validation (lint + breaking changes)
./scripts/specs/validate-protos.sh

# Skip breaking change checks
./scripts/specs/validate-protos.sh --no-breaking

# Strict mode (fail on warnings)
./scripts/specs/validate-protos.sh --strict
```

### Make Changes

```bash
# 1. Edit proto file
vim fleet/orchestrator/v1/orchestrator.proto

# 2. Validate
./scripts/specs/validate-protos.sh

# 3. Bump version
./scripts/specs/version-bump.sh patch  # or minor/major/auto

# 4. Generate docs
./scripts/specs/generate-docs.sh

# 5. Publish to registry
./scripts/specs/publish-proto-bundle.sh
```

### Version Bumping

```bash
# Patch bump (bug fixes)
./scripts/specs/version-bump.sh patch

# Minor bump (new features, backward-compatible)
./scripts/specs/version-bump.sh minor

# Major bump (breaking changes)
./scripts/specs/version-bump.sh major

# Auto-detect (recommended)
./scripts/specs/version-bump.sh auto
```

### Publishing

```bash
# Publish current version
./scripts/specs/publish-proto-bundle.sh

# Publish specific version
./scripts/specs/publish-proto-bundle.sh --version=1.2.0

# Dry run (test without publishing)
./scripts/specs/publish-proto-bundle.sh --dry-run
```

### Documentation

```bash
# Generate HTML docs
./scripts/specs/generate-docs.sh

# View docs
cd docs/api && python3 -m http.server 8000
# Open http://localhost:8000
```

## 🔍 Breaking Change Policy

### MAJOR Version Bump Required (Breaking)

❌ Breaking changes:
- Remove field, method, or service
- Rename field or method
- Change field type
- Change field number
- Remove enum value
- Change method signature

### MINOR Version Bump (Non-Breaking)

✅ Backward-compatible additions:
- Add new field (with default)
- Add new method
- Add new enum value
- Add new service
- Add new message type

### PATCH Version Bump (Documentation)

🔧 Non-functional changes:
- Documentation updates
- Comment fixes
- Internal refactoring

## 📖 Examples

### Adding a New RPC (Minor Bump)

```protobuf
// fleet/orchestrator/v1/orchestrator.proto
service OrchestratorService {
  // Existing RPCs...

  // New RPC - backward compatible
  rpc GetStats(GetStatsRequest) returns (GetStatsResponse);
}
```

```bash
./scripts/specs/validate-protos.sh        # Should pass
./scripts/specs/version-bump.sh minor     # 1.0.0 → 1.1.0
./scripts/specs/publish-proto-bundle.sh
```

### Removing a Field (Major Bump)

```protobuf
message CreateCouncilRequest {
  string role = 1;
  // string description = 2;  // REMOVED
}
```

```bash
./scripts/specs/validate-protos.sh        # Will FAIL with breaking change
./scripts/specs/version-bump.sh major     # 1.0.0 → 2.0.0
./scripts/specs/publish-proto-bundle.sh
```

## 🔗 Integration with Services

### Using Versioned Protos in Dockerfiles

```dockerfile
# Pin to specific version
ARG PROTO_VERSION=1.0.0

# Download from registry
RUN curl -L registry.underpassai.com/swe-fleet/protos:v${PROTO_VERSION} \
    | tar -xz -C /app/specs/

# Generate code
RUN python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet \
    --python_out=/app/gen \
    orchestrator/v1/orchestrator.proto
```

## 📚 Documentation

- [API Versioning Strategy](../docs/API_VERSIONING_STRATEGY.md) - Full versioning policy
- [Tooling Setup](../docs/TOOLING_SETUP.md) - Install buf, podman, etc.
- [Interactive API Testing](../docs/specs/INTERACTIVE_API_TESTING.md) - grpcui and grpcurl guide
- [Breaking Change Examples](../docs/examples/PROTO_BREAKING_CHANGES.md) - Detailed examples
- [Changelog](CHANGELOG.md) - Version history

## 🚀 Quick Reference

| Task | Command |
|------|---------|
| Validate | `./scripts/specs/validate-protos.sh` |
| Bump version | `./scripts/specs/version-bump.sh auto` |
| Generate docs | `./scripts/specs/generate-docs.sh` |
| Publish | `./scripts/specs/publish-proto-bundle.sh` |
| Test API (grpcui) | `make -C specs grpcui-serve SERVICE=orchestrator` |
| Serve docs | `make -C specs docs-serve` |
| Lint only | `cd specs && buf lint` |
| Check breaking | `cd specs && buf breaking --against '.git#branch=main'` |

## ⚠️ Important Notes

1. **Never commit generated files** (`_pb2.py`, `_pb2_grpc.py`, etc.) to git
2. **Always validate before bumping** version
3. **Breaking changes require major** version bump and explicit approval
4. **Proto bundles are immutable** - never overwrite published versions
5. **Pin service versions** to avoid unexpected breaking changes
