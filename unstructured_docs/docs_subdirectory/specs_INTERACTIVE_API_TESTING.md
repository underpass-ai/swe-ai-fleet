# Interactive gRPC API Testing

SWE AI Fleet provides industry-grade interactive API testing tools for developing and debugging gRPC services.

---

## Overview

We provide **two complementary tools** for testing gRPC endpoints:

| Tool | Type | Best For |
|------|------|----------|
| **grpcui** | Web UI | Interactive testing, browsing schemas, form-based requests |
| **grpcurl** | CLI | Automation, scripts, CI/CD, quick tests |

Both tools support:
- Server reflection (auto-discovery of services)
- Proto file loading (explicit schema definition)
- Streaming RPCs
- Metadata and headers
- TLS and authentication

---

## grpcui - Interactive Web UI

### What is grpcui?

**grpcui** provides a **Swagger-like web interface** for gRPC endpoints. It's the easiest way to explore and test your APIs without writing code.

**Features:**
- 🖥️ **Web-based UI** - No browser extensions needed
- 📋 **Browse services** - Discover all available methods
- ✏️ **Form inputs** - JSON forms for each request type
- 🔄 **Real-time execution** - Click to call, instant results
- 📊 **Schema viewer** - See message definitions inline
- 🌊 **Streaming support** - Test server-side streaming RPCs
- 💾 **Request history** - Save and replay calls

### Installation

#### Option 1: Install Script (Recommended)

```bash
bash scripts/install-grpcui.sh
```

This script:
- Detects your OS and architecture
- Downloads the latest binary (v1.3.4)
- Places it in `~/.local/bin`
- Verifies installation

#### Option 2: Go Install

If you have Go installed:

```bash
go install github.com/fullstorydev/grpcui/cmd/grpcui@latest
```

#### Option 3: Manual Download

```bash
# Download from GitHub releases
curl -sSL https://github.com/fullstorydev/grpcui/releases/download/v1.3.4/grpcui_1.3.4_linux_amd64.tar.gz | \
  tar -xz -C ~/.local/bin
```

### Usage

#### Basic Usage (Server Reflection)

If your gRPC server has **reflection enabled** (see below):

```bash
# Launch UI for all services
make -C specs grpcui-serve

# Or manually
grpcui -plaintext localhost:50055
```

Access the UI at `http://localhost:8080`

#### With Proto Files (Recommended)

More explicit and works without server reflection:

```bash
# Test specific service
make -C specs grpcui-serve SERVICE=orchestrator

# Custom host/port
make -C specs grpcui-serve SERVICE=orchestrator HOST=localhost PORT=50055

# Or manually
grpcui -plaintext \
  -protopath specs/fleet \
  -proto orchestrator/v1/orchestrator.proto \
  localhost:50055
```

#### Common Options

```bash
# Use TLS
grpcui -insecure localhost:50055

# Custom headers
grpcui -plaintext -H "Authorization: Bearer TOKEN" localhost:50055

# Multiple proto files
grpcui -plaintext \
  -protopath specs/fleet \
  -proto orchestrator/v1/orchestrator.proto \
  -proto context/v1/context.proto \
  localhost:50055
```

#### Available Services

Test any of these services:

```bash
make -C specs grpcui-serve SERVICE=context        # Context Service
make -C specs grpcui-serve SERVICE=orchestrator   # Orchestrator Service
make -C specs grpcui-serve SERVICE=ray_executor   # Ray Executor Service
make -C specs grpcui-serve SERVICE=planning       # Planning Service
make -C specs grpcui-serve SERVICE=storycoach     # StoryCoach Service
make -C specs grpcui-serve SERVICE=workspace      # Workspace Service
```

### Enabling Server Reflection

To use server reflection (no proto files needed), add this to your gRPC server:

**Python:**
```python
from grpc_reflection.v1alpha import reflection

def serve():
    server = grpc.aio.server()

    # Register your service
    orchestrator_pb2_grpc.add_OrchestratorServiceServicer_to_server(
        OrchestratorService(), server
    )

    # Enable reflection
    SERVICE_NAMES = (
        orchestrator_pb2.DESCRIPTOR.services_by_name['OrchestratorService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    # Start server
    server.add_insecure_port('[::]:50055')
    await server.start()
    await server.wait_for_termination()
```

**Go:**
```go
import (
    "google.golang.org/grpc/reflection"
)

func main() {
    s := grpc.NewServer()

    // Register your service
    pb.RegisterOrchestratorServiceServer(s, &orchestratorService{})

    // Enable reflection
    reflection.Register(s)

    // Start server
    lis, _ := net.Listen("tcp", ":50055")
    s.Serve(lis)
}
```

**⚠️ Security Note**: Only enable reflection in development/staging. Disable in production.

---

## grpcurl - CLI Testing

### What is grpcurl?

**grpcurl** is a **curl-like CLI tool** for gRPC. Perfect for scripts, automation, and quick tests.

### Installation

```bash
# Option 1: Go install
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# Option 2: Binary download
curl -sSL https://github.com/fullstorydev/grpcurl/releases/download/v1.9.1/grpcurl_1.9.1_linux_amd64.tar.gz | \
  tar -xz -C ~/.local/bin
```

### Usage Examples

#### List Services

```bash
# With reflection
grpcurl -plaintext localhost:50055 list

# With proto
grpcurl -plaintext \
  -protopath specs/fleet \
  -proto orchestrator/v1/orchestrator.proto \
  localhost:50055 list
```

#### Describe Service

```bash
grpcurl -plaintext localhost:50055 describe \
  fleet.orchestrator.v1.OrchestratorService
```

#### Describe Method

```bash
grpcurl -plaintext localhost:50055 describe \
  fleet.orchestrator.v1.OrchestratorService.Deliberate
```

#### Call Unary Method

```bash
grpcurl -plaintext -d '{
  "task_description": "Add user authentication",
  "role": "DEV",
  "rounds": 1,
  "num_agents": 3
}' localhost:50055 fleet.orchestrator.v1.OrchestratorService/Deliberate
```

#### Call Server-Streaming Method

```bash
grpcurl -plaintext -d '{
  "task_description": "Add user authentication",
  "role": "DEV"
}' localhost:50055 fleet.orchestrator.v1.OrchestratorService/StreamDeliberation
```

#### With Headers

```bash
grpcurl -plaintext \
  -H "Authorization: Bearer TOKEN" \
  -H "X-Request-ID: abc-123" \
  localhost:50055 \
  fleet.orchestrator.v1.OrchestratorService/ListCouncils
```

#### With Proto Files

```bash
grpcurl -plaintext \
  -protopath specs/fleet \
  -proto orchestrator/v1/orchestrator.proto \
  -proto context/v1/context.proto \
  localhost:50055 \
  fleet.orchestrator.v1.OrchestratorService/Deliberate \
  -d '{"task_description": "test", "role": "DEV"}'
```

---

## Comparison with REST Swagger UI

| Feature | Swagger UI (REST) | grpcui (gRPC) |
|---------|------------------|---------------|
| **Discovery** | OpenAPI spec | Server reflection or proto files |
| **UI** | Web-based forms | Web-based forms |
| **Test execution** | Click to call | Click to call |
| **Schema viewer** | JSON schema | Proto definition |
| **Streaming** | Server-Sent Events | ✅ Native gRPC streaming |
| **Type safety** | JSON (runtime) | Proto (compile-time) |
| **TLS** | HTTPS | ✅ gRPC over TLS |
| **Authentication** | Bearer tokens, API keys | ✅ gRPC metadata/headers |

---

## Real-World Workflows

### Development Workflow

1. **Start your gRPC server** (e.g., Orchestrator Service)
2. **Launch grpcui:**
   ```bash
   make -C specs grpcui-serve SERVICE=orchestrator
   ```
3. **Open `http://localhost:8080`** in browser
4. **Browse services** → Select method → **Fill form** → **Execute**
5. **Inspect response** → Debug issues → Repeat

### CI/CD Integration

Use **grpcurl** in automated tests:

```bash
#!/bin/bash
# scripts/test-api.sh

SERVICE="${1:-orchestrator}"
ENDPOINT="${2:-localhost:50055}"

echo "Testing $SERVICE at $ENDPOINT..."

# Health check
grpcurl -plaintext \
  -H "X-Health-Check: true" \
  $ENDPOINT \
  fleet.$SERVICE.v1.${SERVICE^}Service/GetStatus

# Test deliberation
RESPONSE=$(grpcurl -plaintext -d '{
  "task_description": "E2E test task",
  "role": "DEV",
  "rounds": 1
}' $ENDPOINT fleet.orchestrator.v1.OrchestratorService/Deliberate)

echo "✓ Deliberation test passed"
echo "$RESPONSE"
```

### Debugging

**grpcurl** is perfect for quick debugging:

```bash
# Quick health check
grpcurl -plaintext localhost:50055 describe fleet.orchestrator.v1.OrchestratorService

# Test specific method
grpcurl -plaintext -d '{"role":"DEV"}' localhost:50055 \
  fleet.orchestrator.v1.OrchestratorService/ListCouncils

# Stream debug logs
grpcurl -plaintext localhost:50055 \
  fleet.orchestrator.v1.OrchestratorService/StreamDeliberation \
  -d '{"task_description":"debug", "role":"DEV"}' | jq .
```

---

## Integration with Proto Versioning

Both tools work seamlessly with our **proto versioning system**:

### Testing Published Versions

When proto bundles are published to the OCI registry:

```bash
# Load versioned proto bundle
export PROTO_VERSION="1.0.0"
docker run --rm -v $(pwd)/specs:/specs \
  registry.underpassai.com/swe-fleet/protos:$PROTO_VERSION

# Use with grpcui
grpcui -plaintext \
  -protopath specs/fleet \
  -proto orchestrator/v1/orchestrator.proto \
  localhost:50055
```

### Documentation Generation

Interactive testing complements our markdown docs:

1. **Read documentation**: `specs/docs/api/*.md`
2. **Serve docs**: `make -C specs docs-serve`
3. **Test in UI**: `make -C specs grpcui-serve`

---

## Troubleshooting

### "grpcui not found"

```bash
# Install it
bash scripts/install-grpcui.sh

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### "Unknown service" or "Method not found"

**Problem**: Server reflection not enabled or proto files not loaded.

**Solution**: Specify proto files explicitly:

```bash
grpcui -plaintext \
  -protopath specs/fleet \
  -proto orchestrator/v1/orchestrator.proto \
  localhost:50055
```

### Connection refused

**Problem**: gRPC server not running or wrong port.

**Solution**: Check server status:

```bash
# Check if port is listening
netstat -tuln | grep 50055

# Or with ss
ss -tuln | grep 50055

# Check pod logs (if in K8s)
kubectl logs -n swe-ai-fleet deployment/orchestrator
```

### TLS certificate errors

**Problem**: Using `-insecure` when you need `-plaintext`.

**Solution**: Use the right flag:

```bash
# Plaintext (no TLS)
grpcui -plaintext localhost:50055

# TLS with self-signed cert
grpcui -insecure localhost:50055

# TLS with proper cert
grpcui localhost:50055
```

---

## References

- **grpcui**: https://github.com/fullstorydev/grpcui
- **grpcurl**: https://github.com/fullstorydev/grpcurl
- **gRPC Reflection**: https://grpc.github.io/grpc/core/md_doc_server_reflection_tutorial.html
- **SWE AI Fleet Tooling Setup**: [TOOLING_SETUP.md](../TOOLING_SETUP.md)
- **Proto Versioning Guide**: [PROTO_VERSIONING_GUIDE.md](./PROTO_VERSIONING_GUIDE.md)
- **API Documentation**: [specs/docs/api/](../../specs/docs/api/README.md)

---

**Last Updated**: 2025-10-31



