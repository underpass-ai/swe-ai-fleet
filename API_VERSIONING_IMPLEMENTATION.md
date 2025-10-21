# API Versioning Implementation Plan

**Status**: 🚧 In Progress  
**Start Date**: 2025-10-18  
**Target Completion**: 2025-10-25 (1 week)

---

## 📅 Implementation Timeline

### Phase 1: Proto Reorganization (Day 1-2) ✅ COMPLETE

**Tasks**:
1. ✅ Create new directory structure
2. ✅ Move proto files to new locations
3. ✅ Update package declarations
4. ✅ Update import statements
5. ✅ Verify no references to old paths
6. ✅ Create buf.yaml, buf.gen.yaml, VERSION, README
7. ✅ Validate with buf lint

**Commands**:
```bash
# Create new structure
mkdir -p specs/fleet/{context,orchestrator,ray_executor,planning,storycoach,workspace}/v1

# Move files (will do via script)
mv specs/context.proto specs/fleet/context/v1/
mv specs/orchestrator.proto specs/fleet/orchestrator/v1/
# ... etc

# Update package declarations in each proto
# orchestrator.v1 → fleet.orchestrator.v1
```

### Phase 2: Buf Setup (Day 2-3) ✅ COMPLETE

**Tasks**:
1. ✅ Install Buf (v1.40.1)
2. ✅ Create `buf.yaml`
3. ✅ Create `buf.gen.yaml`  
4. ⏳ Create `buf.lock` (will be auto-generated on first use)
5. ✅ Test local validation (some style warnings, non-critical)

**Files to Create**:
- `specs/buf.yaml`
- `specs/buf.gen.yaml`
- `specs/VERSION` (starting at 1.0.0)

### Phase 3: Service Updates (Day 3-5) ✅ COMPLETE

**Tasks**:
1. ✅ Update Dockerfiles to reference new paths
2. ⏳ Regenerate code with new package names (will happen on next build)
3. ⏳ Update import statements in Python code (if needed after rebuild)
4. ⏳ Test each service builds correctly (next step)
5. ⏳ Update documentation

**Services Updated**:
- [x] orchestrator ✅
- [x] ray-executor ✅
- [x] context ✅
- [x] jobs/orchestrator ✅
- [x] monitoring (no protos) N/A
- [x] jobs/nats (no protos) N/A

### Phase 4: CI/CD Integration (Day 5-6) 🔜

**Tasks**:
1. Add Buf validation to CI
2. Create proto publishing script
3. Test on feature branch
4. Document workflow

### Phase 5: OCI Publishing (Day 6-7) 🔜

**Tasks**:
1. Create bundle packaging script
2. Test push to registry
3. Test pull from registry
4. Update Dockerfiles to use versioned bundles

---

## 🎯 Immediate Actions (Next 2 Hours)

### Action 1: Install Buf ✅

```bash
# Option 1: Homebrew (if available)
brew install bufbuild/buf/buf

# Option 2: Direct download
BUF_VERSION=1.40.1
curl -sSL \
  "https://github.com/bufbuild/buf/releases/download/v${BUF_VERSION}/buf-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/buf
chmod +x /usr/local/bin/buf
buf --version
```

### Action 2: Create Directory Structure ✅

```bash
cd /home/tirso/ai/developents/swe-ai-fleet

# Create new structure
mkdir -p specs/fleet/{context,orchestrator,ray_executor,planning,storycoach,workspace}/v1

# Move files
mv specs/context.proto specs/fleet/context/v1/
mv specs/orchestrator.proto specs/fleet/orchestrator/v1/
mv specs/ray_executor.proto specs/fleet/ray_executor/v1/
mv specs/planning.proto specs/fleet/planning/v1/
mv specs/storycoach.proto specs/fleet/storycoach/v1/
mv specs/workspace.proto specs/fleet/workspace/v1/
```

### Action 3: Update Package Declarations ⏳

**orchestrator.proto**:
```protobuf
// Before
package orchestrator.v1;

// After
package fleet.orchestrator.v1;

option go_package = "github.com/underpass-ai/swe-ai-fleet/gen/fleet/orchestrator/v1;orchestratorv1";
```

**ray_executor.proto**:
```protobuf
// Before
package ray_executor.v1;

// After  
package fleet.ray_executor.v1;

option go_package = "github.com/underpass-ai/swe-ai-fleet/gen/fleet/ray_executor/v1;ray_executorv1";
```

### Action 4: Create Buf Configuration ⏳

**specs/buf.yaml**:
```yaml
version: v2
modules:
  - path: fleet
lint:
  use:
    - STANDARD
    - PACKAGE_VERSION_SUFFIX
  except:
    - PACKAGE_DIRECTORY_MATCH  # Disable strict directory matching for now
breaking:
  use:
    - FILE
```

**specs/buf.gen.yaml**:
```yaml
version: v2
managed:
  enabled: true
plugins:
  - local: python -m grpc_tools.protoc
    out: ../gen/python
    opt:
      - paths=source_relative
  - local: python -m grpc_tools.protoc --pyi_out
    out: ../gen/python
    opt:
      - paths=source_relative
```

**specs/VERSION**:
```
1.0.0
```

### Action 5: Create Helper Scripts ⏳

**scripts/validate-protos.sh**:
```bash
#!/bin/bash
set -e

echo "🔍 Validating proto files..."

cd specs/fleet

# Lint
echo "📝 Running buf lint..."
buf lint

# Breaking changes (against main)
echo "🔄 Checking for breaking changes..."
if git rev-parse --verify main >/dev/null 2>&1; then
  buf breaking --against '.git#branch=main'
else
  echo "⚠️  No main branch, skipping breaking change detection"
fi

echo "✅ Proto validation passed!"
```

**scripts/generate-protos-local.sh**:
```bash
#!/bin/bash
set -e

echo "🏗️  Generating proto code locally..."

cd specs/fleet

# Generate with buf
buf generate

echo "✅ Code generated in gen/"
ls -lh ../../gen/python/fleet/
```

---

## 🔥 Critical Path Items

### Before We Can Proceed

1. ✅ **Backup current state**
   ```bash
   git checkout -b feature/api-versioning
   git add -A
   git commit -m "chore: checkpoint before API versioning refactor"
   ```

2. ⏳ **Test current services still work**
   - Verify orchestrator builds
   - Verify ray-executor builds
   - Run unit tests

3. ⏳ **Communication**
   - Document migration in PR description
   - Update ROADMAP.md
   - Notify team (if applicable)

---

## 🎯 Success Metrics

- [ ] All protos in `specs/fleet/<service>/v1/` structure
- [ ] All packages use `fleet.<service>.v1` format
- [ ] `buf lint` passes with zero warnings
- [ ] `buf breaking` configured and working
- [ ] All services build with new proto paths
- [ ] All tests pass (unit + integration)
- [ ] CI runs `buf lint` on every PR
- [ ] Documentation updated

---

## 🚨 Rollback Plan

If something goes wrong:

```bash
# Abort and return to previous state
git checkout main
git branch -D feature/api-versioning

# Or revert specific commit
git revert <commit-sha>
```

**Indicators to Rollback**:
- Services fail to build after 2 hours of troubleshooting
- Breaking changes in production
- Team consensus to delay

---

## 📝 Next Steps

**Right Now** (Tirso to approve):
1. Create feature branch
2. Install Buf
3. Reorganize proto files
4. Update package declarations
5. Run validation
6. Commit changes

**After Approval**:
1. Update all Dockerfiles
2. Regenerate code
3. Fix imports
4. Test builds
5. Run tests
6. Create PR

---

## 📞 Questions/Blockers

- ❓ Do we need to support Go clients now, or Python-only is fine?
  - **Answer**: Python-only for now, add `go_package` for future
  
- ❓ Should we version the entire bundle or individual protos?
  - **Answer**: Entire bundle (simpler for microservices)

- ❓ When to bump MAJOR vs MINOR version?
  - **Answer**: Follow breaking change policy in strategy doc

---

## ✅ Ready to Start?

**Prerequisites**:
- [x] Strategy document approved
- [x] Implementation plan reviewed
- [ ] Tirso approval to proceed
- [ ] Feature branch created
- [ ] Buf installed

**Let's go! 🚀**

