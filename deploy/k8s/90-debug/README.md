# 90-debug - Development & Debug Tools

## Purpose

Debug and development tools for inspecting gRPC services and protobuf APIs.

**Optional** - Not required for production operation.

---

## Tools

### gRPC UI
Interactive web UI for testing gRPC services without writing client code.

**Services**:
- `grpcui/context/` - gRPC UI for Context Service (port 50054)
- `grpcui/orchestrator/` - gRPC UI for Orchestrator (port 50055)
- `grpcui/ray-executor/` - gRPC UI for Ray Executor (port 50057)

**Access**:
- https://grpcui-context.underpassai.com
- https://grpcui-orchestrator.underpassai.com
- https://grpcui-rayexecutor.underpassai.com

---

### Proto Docs Server
Auto-generated documentation from protobuf specs.

**Files**: `proto-docs/`
**Access**: https://proto-docs.underpassai.com

---

## Apply

```bash
# Apply all debug tools
kubectl apply -f grpcui/context/
kubectl apply -f grpcui/orchestrator/
kubectl apply -f grpcui/ray-executor/
kubectl apply -f proto-docs/

# Or individually
kubectl apply -f grpcui/context/deployment.yaml
kubectl apply -f grpcui/context/service.yaml
kubectl apply -f grpcui/context/ingress.yaml
```

---

## Dependencies

**Requires**:
- ✅ Microservices running (`30-microservices/`)
- ✅ ingress-nginx installed
- ✅ cert-manager for TLS

---

## Usage

### Testing gRPC Endpoints

1. Navigate to https://grpcui-context.underpassai.com
2. Select method from dropdown (e.g., `GetNodesByType`)
3. Fill in request parameters
4. Click "Invoke"
5. View response

### Viewing Proto Documentation

1. Navigate to https://proto-docs.underpassai.com
2. Browse service definitions
3. View message schemas
4. See method signatures

---

## Removal

Debug tools can be removed in production:

```bash
kubectl delete -f grpcui/
kubectl delete -f proto-docs/
```

They do not affect system operation.

---

## Notes

- grpcui pods run with minimal resources (100m CPU, 128Mi RAM)
- All use `latest` tag (auto-pulls updates)
- TLS certificates managed by cert-manager


