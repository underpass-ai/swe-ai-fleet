# API Versioning Strategy - SWE AI Fleet

**Date**: 2025-10-18  
**Status**: ✅ Approved - Implementation in Progress  
**Author**: System Architecture Team

## 🎯 Objective

Establish a robust, production-ready API versioning and artifact management system for Protocol Buffer definitions across the SWE AI Fleet microservices ecosystem.

---

## 📊 Current Situation Analysis

### Problems Identified

1. **Inconsistent Namespace Convention**
   ```protobuf
   // ✅ Good - Has fleet prefix
   package fleet.context.v1;
   package fleet.planning.v1;
   
   // ❌ Inconsistent - Missing fleet prefix
   package orchestrator.v1;
   package ray_executor.v1;
   ```

2. **No Centralized Artifact Management**
   - Proto files scattered in `specs/` directory
   - Each service generates code independently
   - No versioning contract between services
   - Breaking changes can go undetected until runtime

3. **Build-Time Dependencies**
   - Services copy proto files during Docker build
   - No guarantee of API version compatibility
   - Difficult to track which service uses which API version

4. **Manual Change Management**
   - No automated breaking change detection
   - No formal API evolution process
   - Risk of unintended incompatibilities

---

## 💡 Proposed Solution

### Hybrid Approach: OCI Registry + Buf Validation

**Why This Approach?**
- ✅ Uses existing infrastructure (registry.underpassai.com)
- ✅ Industry-standard tooling (Buf)
- ✅ Automated validation without external dependencies
- ✅ Suitable for open-source projects
- ✅ Supports semantic versioning
- ✅ CI/CD friendly

---

## 🏗️ Architecture

### 1. Directory Structure

```
specs/
├── fleet/
│   ├── context/
│   │   └── v1/
│   │       └── context.proto
│   ├── orchestrator/
│   │   └── v1/
│   │       └── orchestrator.proto
│   ├── ray_executor/
│   │   └── v1/
│   │       └── ray_executor.proto
│   ├── planning/
│   │   └── v1/
│   │       └── planning.proto
│   ├── storycoach/
│   │   └── v1/
│   │       └── storycoach.proto
│   └── workspace/
│       └── v1/
│           └── workspace.proto
├── buf.yaml              # Buf configuration
├── buf.lock              # Dependency lock file
├── buf.gen.yaml          # Code generation config
├── VERSION               # Current API bundle version
└── README.md             # Proto documentation
```

### 2. Namespace Convention

**Standard Format**: `fleet.<service>.v<major_version>`

**Examples**:
```protobuf
package fleet.context.v1;
package fleet.orchestrator.v1;
package fleet.ray_executor.v1;

option go_package = "github.com/underpass-ai/swe-ai-fleet/gen/fleet/<service>/v1;<service>v1";
```

**Go Package Path**: `github.com/underpass-ai/swe-ai-fleet/gen/fleet/<service>/v1`

### 3. Versioning Scheme

**Semantic Versioning**: `vMAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (incompatible API changes)
- **MINOR**: New features (backward-compatible)
- **PATCH**: Bug fixes (backward-compatible)

**Example Evolution**:
```
v1.0.0 → Initial release (orchestrator.v1)
v1.1.0 → Add DeleteCouncil RPC (backward-compatible)
v1.1.1 → Fix DeleteCouncilResponse field types
v2.0.0 → Change CreateCouncil signature (breaking)
```

---

## 🔧 Implementation Plan

### Phase 1: Reorganize Proto Files ✅

1. **Restructure `specs/` directory**
   - Move protos to `specs/fleet/<service>/v1/`
   - Update package declarations
   - Update import paths

2. **Standardize namespaces**
   - Change `orchestrator.v1` → `fleet.orchestrator.v1`
   - Change `ray_executor.v1` → `fleet.ray_executor.v1`
   - Ensure all have `go_package` option

### Phase 2: Buf Configuration ✅

1. **Create `buf.yaml`**
   ```yaml
   version: v2
   modules:
     - path: specs
   lint:
     use:
       - STANDARD
       - PACKAGE_VERSION_SUFFIX  # Enforce v1, v2, etc.
   breaking:
     use:
       - FILE
   ```

2. **Create `buf.gen.yaml`**
   ```yaml
   version: v2
   plugins:
     - local: protoc-gen-python
       out: gen/python
     - local: protoc-gen-pyi
       out: gen/python
     - local: protoc-gen-go
       out: gen/go
   ```

### Phase 3: OCI Artifact Publishing 🚧

1. **Create publish script**: `scripts/publish-proto-bundle.sh`
   - Validate with `buf breaking`
   - Package protos as OCI artifact
   - Push to `registry.underpassai.com/swe-ai-fleet/protos:v{VERSION}`

2. **Version file**: `specs/VERSION`
   ```
   1.0.0
   ```

3. **CI/CD Integration**
   - On tag push (`v*`):
     - Validate breaking changes
     - Build proto bundle
     - Publish to registry
     - Update changelog

### Phase 4: Service Integration 🚧

1. **Update Dockerfiles**
   ```dockerfile
   # Before: Copy from local
   COPY specs/orchestrator.proto /app/specs/
   
   # After: Download specific version
   ARG PROTO_VERSION=1.0.0
   RUN curl -L https://registry.underpassai.com/v2/swe-ai-fleet/protos/manifests/${PROTO_VERSION} \
       | tar -xz -C /app/specs/
   ```

2. **Pin proto versions in services**
   - Each service declares required proto version
   - Build fails if incompatible version

---

## 📋 Breaking Change Policy

### What Constitutes a Breaking Change?

**❌ Breaking (MAJOR version bump)**:
- Remove field, method, or service
- Rename field or method
- Change field type
- Change field number
- Remove enum value
- Change method signature (request/response type)

**✅ Non-Breaking (MINOR version bump)**:
- Add new field (with default)
- Add new method
- Add new enum value
- Add new service
- Add new message type

**🔧 Patch (PATCH version bump)**:
- Documentation changes
- Comment updates
- Fix incorrect field types (if not yet used)

### Validation Process

```bash
# Before committing proto changes
buf breaking --against '.git#branch=main'

# Example output:
# ✓ No breaking changes detected
# or
# ✗ BREAKING CHANGE: Field "council_id" removed from CreateCouncilResponse
```

---

## 🔄 Workflow

### Developer Workflow

```bash
# 1. Make proto changes
vim specs/fleet/orchestrator/v1/orchestrator.proto

# 2. Validate
buf lint
buf breaking --against '.git#branch=main'

# 3. Generate code locally (for testing)
buf generate

# 4. Commit and PR
git add specs/
git commit -m "feat(api): add DeleteCouncil RPC to orchestrator.v1"

# 5. CI validates and tests

# 6. On merge to main, tag release
git tag v1.1.0
git push origin v1.1.0

# 7. CI publishes to OCI registry
```

### Service Consumer Workflow

```dockerfile
# services/my-service/Dockerfile

ARG PROTO_BUNDLE_VERSION=1.1.0

# Download proto bundle from registry
RUN curl -L registry.underpassai.com/v2/swe-ai-fleet/protos/blobs/sha256:${PROTO_SHA} \
    | tar -xz -C /app/specs/

# Generate code from specific version
RUN python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet \
    --python_out=/app/gen \
    orchestrator/v1/orchestrator.proto
```

---

## 🛠️ Tooling

### Required Tools

1. **Buf** (v1.40.0+)
   ```bash
   # Install
   brew install bufbuild/buf/buf
   # or
   go install github.com/bufbuild/buf/cmd/buf@latest
   ```

2. **OCI CLI** (Already have via podman)
   ```bash
   podman --version
   ```

3. **protoc** (Already have via grpcio-tools)
   ```bash
   python -m grpc_tools.protoc --version
   ```

### Helper Scripts

**`scripts/validate-protos.sh`**:
```bash
#!/bin/bash
set -e
cd specs
buf lint
buf breaking --against '.git#branch=main'
echo "✅ Proto validation passed"
```

**`scripts/publish-proto-bundle.sh`**:
```bash
#!/bin/bash
set -e
VERSION=$(cat specs/VERSION)
buf build -o protos-${VERSION}.bin
# Push to OCI registry
# ... (implementation in Phase 3)
```

**`scripts/generate-protos.sh`**:
```bash
#!/bin/bash
set -e
cd specs
buf generate
echo "✅ Code generated in gen/"
```

---

## 📚 Migration Path

### Step-by-Step Migration

**Week 1: Setup**
- [ ] Install Buf
- [ ] Create buf.yaml, buf.gen.yaml
- [ ] Reorganize specs/ directory
- [ ] Update all package declarations

**Week 2: Validation**
- [ ] Set up baseline (`buf mod update`)
- [ ] Configure breaking change detection
- [ ] Test with existing protos
- [ ] Document validation in CI

**Week 3: Publishing**
- [ ] Create OCI publishing script
- [ ] Tag initial version (v1.0.0)
- [ ] Publish to registry
- [ ] Verify download works

**Week 4: Service Updates**
- [ ] Update 1 service as pilot (orchestrator)
- [ ] Verify build and deploy
- [ ] Document process
- [ ] Roll out to remaining services

---

## 🎯 Success Criteria

1. ✅ All protos use consistent `fleet.<service>.v<N>` namespace
2. ✅ `buf breaking` runs in CI on every PR
3. ✅ Proto bundles published to OCI registry on tag
4. ✅ Services pin to specific proto versions
5. ✅ Breaking changes detected before merge
6. ✅ Documentation updated for new workflow

---

## 📖 References

- [Buf Documentation](https://buf.build/docs/)
- [Protobuf Style Guide](https://protobuf.dev/programming-guides/style/)
- [Semantic Versioning](https://semver.org/)
- [OCI Artifacts](https://github.com/opencontainers/artifacts)
- [API Versioning Best Practices](https://cloud.google.com/apis/design/versioning)

---

## 🔗 Related Documents

- [API Generation Rules](../API_GENERATION_RULES.md)
- [Microservices Build Patterns](./MICROSERVICES_BUILD_PATTERNS.md)
- [Proto Breaking Change Examples](./examples/PROTO_BREAKING_CHANGES.md)

---

## 📝 Changelog

### 2025-10-18 - Initial Strategy
- Defined hybrid OCI + Buf approach
- Established namespace convention
- Created migration plan
- Set up validation workflow

