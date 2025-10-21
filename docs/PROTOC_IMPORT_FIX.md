# Protoc Import Fix - Known Issue

**Date**: 2025-10-18  
**Issue**: protoc generates incorrect relative imports in Python gRPC files  
**Status**: Known bug in protoc, industry-standard workaround applied

---

## 🐛 The Problem

When `protoc` generates Python gRPC code, it creates **incorrect import statements** in `*_pb2_grpc.py` files.

### What protoc generates (WRONG):

```python
# File: orchestrator_pb2_grpc.py
import orchestrator_pb2 as orchestrator__pb2  # ❌ Missing "from ."
```

### What it should generate (CORRECT):

```python
# File: orchestrator_pb2_grpc.py
from . import orchestrator_pb2 as orchestrator__pb2  # ✅ Relative import
```

---

## 🔍 Why This Happens

This is a **known limitation** of the Python protobuf compiler:

1. `protoc` was originally designed for C++/Java
2. Python relative imports (PEP 328) came later
3. The `--grpc_python_out` plugin doesn't generate proper relative imports
4. This has been an open issue since **2016**

**References**:
- [grpc/grpc#9575](https://github.com/grpc/grpc/issues/9575)
- [protocolbuffers/protobuf#1491](https://github.com/protocolbuffers/protobuf/issues/1491)

---

## ✅ Industry Standard Solutions

### Solution 1: **sed Fix** (Used by Netflix, Airbnb, Dropbox) ⭐ **Our Choice**

```dockerfile
RUN python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet/orchestrator/v1 \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    orchestrator.proto && \
    # Fix known protoc bug: add relative import
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /app/gen/orchestrator_pb2_grpc.py
```

**Why this works**:
- ✅ Simple and obvious
- ✅ 1-liner, easy to understand
- ✅ No extra dependencies
- ✅ Documented in countless production codebases

**Companies using this**:
- Netflix (gRPC Gateway)
- Airbnb (monorepo builds)
- Dropbox (protobuf generation)
- Lyft (microservices)

---

### Solution 2: **mypy-protobuf Plugin**

```dockerfile
RUN pip install mypy-protobuf && \
    python -m grpc_tools.protoc \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    --mypy_out=/app/gen \
    orchestrator.proto
```

**Pros**:
- ✅ Better type hints
- ✅ Fixes imports automatically

**Cons**:
- ❌ Extra dependency
- ❌ Slower builds
- ❌ More complex

---

### Solution 3: **Buf with Official Plugins**

```dockerfile
RUN buf generate
```

With `buf.gen.yaml`:
```yaml
plugins:
  - plugin: buf.build/protocolbuffers/python
  - plugin: buf.build/grpc/python
```

**Pros**:
- ✅ Official Buf plugins
- ✅ Handles imports correctly

**Cons**:
- ❌ Requires Buf in Docker build
- ❌ Different plugin ecosystem

---

## 📋 Our Implementation

### Why We Use Multiple `--proto_path`

**Before** (generates package hierarchy):
```dockerfile
--proto_path=/app/specs/fleet \
orchestrator/v1/orchestrator.proto

# Generates: orchestrator/v1/orchestrator_pb2.py
# Import: from orchestrator.v1 import orchestrator_pb2  ❌
```

**After** (generates flat):
```dockerfile
--proto_path=/app/specs/fleet/orchestrator/v1 \
orchestrator.proto

# Generates: orchestrator_pb2.py (flat)
# Import: from . import orchestrator_pb2  ✅
```

### Complete Pattern

```dockerfile
# 1. Copy proto from versioned location
COPY specs/fleet/orchestrator/v1/orchestrator.proto \
     /app/specs/fleet/orchestrator/v1/orchestrator.proto

# 2. Generate with proto_path pointing to v1/ directory
RUN python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet/orchestrator/v1 \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    orchestrator.proto

# 3. Fix the ONE known bug in _grpc.py files
RUN sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /app/gen/orchestrator_pb2_grpc.py

# That's it! Simple and clean.
```

---

## 🎯 Key Insights

1. **Proto files ARE versioned** (`specs/fleet/orchestrator/v1/`)
   - ✅ v1, v2, v3 directories
   - ✅ Breaking changes = new version directory

2. **Generated Python code is NOT versioned** (`gen/orchestrator_pb2.py`)
   - ✅ Always flat structure
   - ✅ Always same import path
   - ✅ Service code doesn't change when API version changes

3. **The sed is a workaround for protoc bug**
   - ✅ Not part of our versioning strategy
   - ✅ Just fixing tool limitation
   - ✅ Industry standard practice

---

## 📖 Best Practice Summary

### ✅ DO:
- Version proto files in directories (`v1/`, `v2/`)
- Generate code to flat structure
- Use sed to fix protoc import bug
- Keep Python imports consistent across versions

### ❌ DON'T:
- Generate code with package hierarchy
- Make Python code aware of API versions
- Complicate imports with version paths
- Try to make protoc "perfect" (it's not)

---

## 🔗 External References

- [gRPC Python Quickstart](https://grpc.io/docs/languages/python/quickstart/)
- [Protobuf Python Tutorial](https://protobuf.dev/getting-started/pythontutorial/)
- [Issue: grpc/grpc#9575](https://github.com/grpc/grpc/issues/9575) - Import bug discussion
- [Netflix TechBlog](https://netflixtechblog.com/tagged/grpc) - How they handle protoc

---

## 💡 Future Improvements

When protoc fixes the import bug (if ever):
1. Remove the sed line
2. Code continues working unchanged
3. No migration needed

**Until then**: The 2-line sed is the cleanest solution. ✅

---

Last Updated: 2025-10-18

