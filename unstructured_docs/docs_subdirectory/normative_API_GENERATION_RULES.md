# API Generation Rules - SWE AI Fleet

## 🔧 **CRITICAL RULE: NO Generated Code in Git**

### ❌ **NEVER COMMIT:**
- Generated gRPC code (`*_pb2.py`, `*_pb2_grpc.py`)
- Generated OpenAPI clients
- Generated TypeScript interfaces from protobuf
- Any code generated from definitions

### ✅ **ALWAYS COMMIT:**
- API definitions (`.proto` files)
- OpenAPI specifications
- Documentation and examples
- Build scripts that generate code

### 🏗️ **Build-Time Generation:**
- Generate code during Docker build
- Use `RUN` commands in Dockerfile
- Store generated code in containers only
- Use `.gitignore` to exclude generated directories

### 📁 **Directory Structure:**
```
services/
├── my-service/
│   ├── specs/           # ✅ API definitions
│   │   └── my_api.proto
│   ├── gen/            # ❌ Generated code (gitignored)
│   │   ├── my_api_pb2.py
│   │   └── my_api_pb2_grpc.py
│   └── Dockerfile      # ✅ Generates code during build
```

### 🎯 **Why This Rule:**
1. **Avoid Merge Conflicts**: Generated code changes frequently
2. **Reproducibility**: Code can always be regenerated from definitions
3. **Clean History**: Git history focuses on actual changes, not generated noise
4. **Consistency**: All environments generate same code from same definitions

### 🚨 **Current Issue:**
The monitoring dashboard needs to access Ray Executor gRPC stubs but should generate them during build, not copy them.

**Solution**: Generate ray_executor stubs in monitoring Dockerfile from the proto definition.
