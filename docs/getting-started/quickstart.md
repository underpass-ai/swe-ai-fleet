# Quick Start Guide — Microservices Architecture

Get the SWE AI Fleet microservices up and running in 5 minutes.

## Prerequisites

- **Container Runtime**: CRI-O (K8s native) or containerd
- **Container Tools**: Podman (rootless) or buildah (for builds) or nerdctl (containerd CLI)
- **Languages**: Go 1.21+, Python 3.13, Node.js 20+
- **Tools**: `protoc` (Protocol Buffers compiler)

> **Note**: This project uses Kubernetes-native container runtimes (CRI-O/containerd). For local development, use Podman (rootless, daemonless) or buildah. The Makefile auto-detects your tools. See [PODMAN_CRIO_GUIDE.md](PODMAN_CRIO_GUIDE.md) for setup.

## Option 1: Local Development (No K8s)

### 1. Install dependencies

```bash
# Install Go gRPC plugins
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Install Python gRPC tools
pip install grpcio grpcio-tools nats-py pyyaml kubernetes

# Install UI dependencies
cd ui/po-react
npm install
cd ../..
```

### 2. Generate gRPC code

```bash
cd services
make gen
cd ..
```

### 3. Start NATS JetStream

```bash
docker run -d --name nats -p 4222:4222 -p 8222:8222 \
  nats:2.10-alpine --jetstream
```

### 4. Start Planning Service

```bash
cd services/planning/cmd
FSM_CONFIG=../../../config/agile.fsm.yaml \
NATS_URL=nats://localhost:4222 \
PORT=50051 \
go run main.go
```

Leave this terminal running.

### 5. Start Story Coach Service

Open a new terminal:

```bash
cd services/storycoach/cmd
PORT=50052 \
go run main.go
```

### 6. Start Workspace Scorer

Open a new terminal:

```bash
cd services/workspace/cmd
RIGOR_CONFIG=../../../config/rigor.yaml \
PORT=50053 \
go run main.go
```

### 7. Start UI (Development Mode)

Open a new terminal:

```bash
cd ui/po-react
npm run dev
```

### 8. Open in Browser

Visit: http://localhost:3000

You should see the PO Planner UI. Try creating a story!

**Note**: Without the Gateway service, direct gRPC calls from browser won't work. You'll need to either:
- Mock the API responses in the UI for development, or
- Implement the Gateway service (REST/SSE → gRPC bridge)

## Option 2: Podman Compose (Easiest!)

Run the entire stack with a single command using Podman Compose (rootless, no daemon):

### 1. Build and start all services

**With Podman (recommended):**
```bash
# Build images
podman-compose build

# Start all services (rootless, no sudo!)
podman-compose -f podman-compose.yml up -d

# View logs
podman-compose logs -f

# Check status
podman-compose ps
```

### 2. Access services

- **UI**: http://localhost:3000
- **NATS Monitoring**: http://localhost:8222
- **Neo4j Browser**: http://localhost:7474 (neo4j/underpassai)
- **Planning gRPC**: localhost:50051
- **Story Coach gRPC**: localhost:50052
- **Workspace gRPC**: localhost:50053

### 3. Stop services

```bash
# Podman
podman-compose down

# To remove volumes (clean slate)
podman-compose down -v
```

> **Why Podman?** Runs rootless (no sudo), daemonless (no background process), OCI-compliant, and works with CRI-O/containerd images. Perfect for local development and more secure. See [PODMAN_CRIO_GUIDE.md](PODMAN_CRIO_GUIDE.md).

This starts:
- NATS JetStream
- Planning Service
- Story Coach Service
- Workspace Scorer
- PO UI
- Redis (for context)
- Neo4j (for context graph)

## Option 3: Kubernetes (Full Production Setup)

### 1. Build and push images

```bash
# Set your container registry
export REGISTRY=ghcr.io/your-org/swe-fleet

# Build all images (auto-detects podman/buildah/nerdctl)
cd services
make docker-build
make docker-build-ui
make docker-push

# Or force specific tool
CONTAINER_ENGINE=podman make docker-build
CONTAINER_ENGINE=buildah make docker-build
CONTAINER_ENGINE=nerdctl make docker-build
```

The Makefile automatically detects your container build tool (podman > buildah > nerdctl)!

### 2. Update K8s manifests with your registry

Edit `deploy/k8s-new/*.yaml` and replace `ghcr.io/underpass-ai` with your registry.

### 3. Deploy to Kubernetes

```bash
kubectl apply -f deploy/k8s/00-namespace.yaml
kubectl apply -f deploy/k8s/
```

### 4. Wait for pods to be ready

```bash
kubectl wait --for=condition=ready pod -l app=nats -n swe --timeout=300s
kubectl wait --for=condition=ready pod -l app=planning -n swe --timeout=300s
kubectl wait --for=condition=ready pod -l app=po-ui -n swe --timeout=300s
```

### 5. Port-forward to access UI

```bash
kubectl port-forward svc/po-ui 8080:80 -n swe
```

Visit: http://localhost:8080

## Testing the System

### Test gRPC services directly

Use `grpcurl` to test services:

```bash
# Install grpcurl
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# List Planning service methods
grpcurl -plaintext localhost:50051 list fleet.planning.v1.PlanningService

# Create a story
grpcurl -plaintext -d '{"title":"Test Story","brief":"Testing"}' \
  localhost:50051 fleet.planning.v1.PlanningService/CreateStory

# List stories
grpcurl -plaintext -d '{}' \
  localhost:50051 fleet.planning.v1.PlanningService/ListStories

# Score a story
grpcurl -plaintext -d '{"title":"As a user I want X","description":"Brief","ac":["Given X When Y Then Z"]}' \
  localhost:50052 fleet.storycoach.v1.StoryCoachService/ScoreStory
```

### Test NATS JetStream

```bash
# Install NATS CLI
go install github.com/nats-io/natscli/nats@latest

# Check streams
nats --server nats://localhost:4222 stream ls
nats --server nats://localhost:4222 stream info AGILE

# Publish a test event
nats --server nats://localhost:4222 pub agile.events \
  '{"event_id":"test-1","case_id":"c-1","event_type":"CASE_CREATED","ts":"2025-10-07T12:00:00Z"}'

# Subscribe to events
nats --server nats://localhost:4222 sub 'agile.events'
```

### Test the UI flow

1. Open http://localhost:3000
2. Create a new story with a title and description
3. Check that it appears in the Stories list with a DoR score
4. Click "Approve" to transition the story
5. Enter the Story ID in Context Viewer to see hydrated context

## Troubleshooting

### "Cannot connect to NATS"

- Check that NATS container is running: `docker ps | grep nats`
- Check logs: `docker logs nats`
- Verify port 4222 is accessible: `nc -zv localhost 4222`

### "gRPC unavailable"

- Check that services are running and listening on correct ports
- For Go services, add debug logging:
  ```go
  log.Printf("Starting service on port %s", port)
  ```

### "UI shows 'Failed to load stories'"

- The UI needs a Gateway service to bridge REST → gRPC
- For now, you can mock the `/api/planner/stories` endpoint or implement the Gateway

### "Permission denied in K8s"

- Check RBAC: `kubectl auth can-i create jobs --as=system:serviceaccount:swe:workspace-runner -n swe`
- Verify ServiceAccount exists: `kubectl get sa workspace-runner -n swe`

### "Docker build fails"

- Ensure you're in the correct directory when building
- Check Dockerfile paths match your project structure
- For multi-stage builds, verify base images are available

## Next Steps

1. **Implement Gateway Service**: Create a Go service that:
   - Exposes REST API (per OpenAPI spec)
   - Calls Planning/Context/StoryCoach via gRPC
   - Streams updates via SSE

2. **Add Mock Mode to UI**: Allow UI to work standalone with mock data

3. **Create docker-compose.yml**: Single command to start all services

4. **Add Observability**: Prometheus metrics, Jaeger tracing

5. **CI/CD**: GitHub Actions to build/test/deploy on push

## Resources

- [Full Architecture Docs](MICROSERVICES_ARCHITECTURE.md)
- [K8s Deployment Guide](deploy/k8s-new/README.md)
- [API Specs](specs/)
- [Contributing Guide](CONTRIBUTING.md)

## Getting Help

- Check existing issues: https://github.com/underpass-ai/swe-ai-fleet/issues
- Create a new issue with logs and environment details
- Join our community (link TBD)

