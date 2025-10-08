# SWE AI Fleet — Microservices Architecture

This document describes the new microservices architecture for SWE AI Fleet, designed with API-first principles, DDD bounded contexts, and event-driven patterns.

## Architecture Overview

### Technology Stack

- **Frontend**: React (no Next.js) + Tailwind CSS + Vite
- **API Design**: OpenAPI 3.1 (REST), AsyncAPI 2.6 (Events), gRPC (sync RPC)
- **Async Messaging**: NATS JetStream (topics & queues, lightweight)
- **Sync RPC**: gRPC with Protocol Buffers
- **Services near frontend**: Go (planning, context, gateway, scoring)
- **Agent execution**: Python (isolated behind NATS/gRPC)
- **High-performance paths**: Go or Rust (where CPU-bound)
- **Methodology**: Domain-Driven Design (DDD) + Event Storming

### Design Principles

1. **API-First**: All contracts (REST, gRPC, AsyncAPI) defined before implementation
2. **Microservice per bounded context**: Each service owns a clear domain boundary
3. **Event-driven**: Domain events propagate state changes via NATS
4. **No spaghetti**: Python isolated to agent execution; Go handles orchestration
5. **Type safety**: Generated clients from specs (OpenAPI, gRPC, AsyncAPI)
6. **Adjustable rigor**: Quality gates configurable per story/feature

## Bounded Contexts (Microservices)

### 1. Planning (Agile Service)
**Technology**: Go + gRPC + NATS  
**Port**: 50051  
**Responsibilities**:
- Story lifecycle FSM (BACKLOG → DRAFT → DESIGN → BUILD → TEST → DOCS → DONE)
- DoR (Definition of Ready) checks with INVEST scoring
- Human gates (PO approvals, QA sign-offs)
- Publishes domain events to `agile.events`

**Key files**:
- `/services/planning/` - Service implementation
- `/config/agile.fsm.yaml` - FSM state machine configuration
- `/specs/planning.proto` - gRPC contract

### 2. Story Coach
**Technology**: Go + gRPC  
**Port**: 50052  
**Responsibilities**:
- Score stories against INVEST + DoR criteria (0-100)
- Suggest improvements (refine title, AC templates)
- Generate story templates from one-line goals

**Key files**:
- `/services/storycoach/` - Service implementation
- `/specs/storycoach.proto` - gRPC contract

### 3. Workspace Scorer
**Technology**: Go + gRPC  
**Port**: 50053  
**Responsibilities**:
- Score workspace execution results (build, tests, coverage, static analysis, e2e)
- Apply rigor profiles (L0–L3) with configurable thresholds
- Gating decisions (pass/warn/block)

**Key files**:
- `/services/workspace/` - Service implementation
- `/config/rigor.yaml` - Rigor profiles configuration
- `/specs/workspace.proto` - gRPC contract

### 4. Workspace Runner
**Technology**: Python + Kubernetes Jobs + NATS  
**Responsibilities**:
- Consume `agent.requests` from NATS (durable pull consumer)
- Create Kubernetes Jobs for containerized agent workspaces
- Each workspace has: git, build tools, test frameworks, SonarQube CLI, e2e runners
- Publish `agent.responses` with results and artifacts
- Stream logs to `workspace.logs.{job_id}`

**Key files**:
- `/workers/workspace_runner.py` - Runner implementation
- `/workers/natsx.py` - NATS SDK wrapper for Python

### 5. Context Service
**Technology**: Go + gRPC + Redis + Neo4j  
**Port**: TBD (50054)  
**Responsibilities**:
- Hydrate context for agent tasks (role + phase scoped)
- Fetch from Redis (timeline) and Neo4j (graph)
- Apply token budgets and prompt scopes
- Publish `context.updated` events

**Status**: Skeleton to be implemented (existing Python code can be migrated)

### 6. Gateway (API)
**Technology**: Go + REST/SSE + gRPC bridge + NATS subscriber  
**Port**: 8080  
**Responsibilities**:
- REST API for React SPA (OpenAPI spec)
- Server-Sent Events (SSE) for live updates
- Calls Planning, Context, StoryCoach, Workspace services via gRPC
- Subscribes to `context.updated`, `agile.events` and forwards via SSE

**Status**: To be implemented

### 7. PO Planner UI
**Technology**: React + Tailwind + Vite  
**Port**: 3000 (dev), 80 (production nginx)  
**Responsibilities**:
- Story creation and management
- DoR score display + improvement suggestions
- FSM state visualization
- Context viewer (role/phase scoped)
- Live updates via SSE

**Key files**:
- `/ui/po-react/` - React SPA
- `/ui/po-react/Dockerfile` - Multi-stage build with nginx

## NATS JetStream Subjects & Streams

| Subject | Stream | Retention | Purpose |
|---------|--------|-----------|---------|
| `agile.events` | AGILE | Limits | Domain events from Planning (CASE_CREATED, TRANSITION, etc.) |
| `agent.requests` | AGENT_WORK | WorkQueue | Atomic task requests for agent workers (deleted after ack) |
| `agent.responses` | AGENT_RESP | Limits | Task completion responses from workers |
| `context.updated` | CTX_UPD | Limits | Context change notifications |
| `workspace.logs.{job_id}` | LOGS | Limits | Live logs from workspace pods |
| `deadletter` | DLQ | Limits | Failed messages with diagnostic info |

**Durable consumers**:
- Planning → `agile.events` (durable: `planning-svc`)
- Orchestrator → `agile.events` (durable: `orchestrator`)
- Workspace Runner → `agent.requests` (durable: `workspace_runner`, WorkQueue)
- Context Service → `agent.responses` (durable: `context-svc`)
- Gateway → `context.updated`, `agile.events` (durable per UI session)

## Event Flow Examples

### Story Creation → Approval → Agent Task

```
1. PO creates story via UI
   → POST /api/planner/stories (Gateway REST)
   → CreateStory gRPC call (Planning Service)
   → Compute DoR score
   → Publish agile.events: {event_type: "CASE_CREATED"}

2. PO approves scope
   → POST /api/planner/stories/{id}/transition (Gateway REST)
   → Transition gRPC call (Planning Service)
   → Check guards (dor_ok, po_approved)
   → FSM: DRAFT → DESIGN
   → Publish agile.events: {event_type: "TRANSITION", to: "DESIGN"}

3. Orchestrator consumes agile.events
   → Derive atomic tasks (DEV, QA, DEVOPS)
   → Publish agent.requests for each task

4. Workspace Runner consumes agent.requests
   → Create K8s Job with workspace container
   → Wait for completion
   → Publish agent.responses with WorkspaceReport

5. Workspace Scorer scores the report
   → Apply rigor profile (L1)
   → Return score + gating decision

6. Context Service consumes agent.responses
   → Update Redis timeline + Neo4j graph
   → Publish context.updated

7. Gateway forwards context.updated via SSE
   → UI refreshes Context Viewer in real-time
```

## API Contracts

All contracts are in `/specs/`:

- **planning.proto** — Planning gRPC service
- **context.proto** — Context gRPC service
- **storycoach.proto** — Story Coach gRPC service
- **workspace.proto** — Workspace Scorer gRPC service
- **openapi.yaml** — Gateway REST API (for SPA)
- **asyncapi.yaml** — NATS JetStream events

## Build & Development

### Prerequisites

- Go 1.21+
- Python 3.11+
- Node.js 20+
- Protocol Buffers compiler (`protoc`)
- `protoc-gen-go`, `protoc-gen-go-grpc` (Go plugins)
- `grpcio-tools` (Python)
- Docker + Kubernetes (for deployment)

### Code Generation

Generate all gRPC clients/servers from `.proto` files:

```bash
cd services
make gen          # Generate Go + Python gRPC code
make gen-go       # Generate Go only
make gen-py       # Generate Python only
```

### Build Services

```bash
cd services
make deps         # Install Go dependencies
make build        # Build all services to ./bin/
make test         # Run tests
make lint         # Lint Go code
```

### Run Locally

**1. Start NATS JetStream:**
```bash
docker run -d --name nats -p 4222:4222 nats:2.10-alpine --jetstream
```

**2. Start Planning Service:**
```bash
cd services/planning/cmd
FSM_CONFIG=../../../config/agile.fsm.yaml NATS_URL=nats://localhost:4222 go run main.go
```

**3. Start Story Coach:**
```bash
cd services/storycoach/cmd
go run main.go
```

**4. Start Workspace Scorer:**
```bash
cd services/workspace/cmd
RIGOR_CONFIG=../../../config/rigor.yaml go run main.go
```

**5. Start UI:**
```bash
cd ui/po-react
npm install
npm run dev
```

Visit `http://localhost:3000`

### Docker Images

Build all images:
```bash
cd services
make docker-build
```

Push to registry:
```bash
make docker-push
```

## Deployment

### Kubernetes

Deploy to K8s cluster:

```bash
# Deploy NATS + services + UI
kubectl apply -f deploy/k8s/namespace-swe.yaml
kubectl apply -f deploy/k8s-new/
```

See [`deploy/k8s-new/README.md`](deploy/k8s-new/README.md) for detailed instructions.

### Environment Variables

| Service | Variable | Default | Description |
|---------|----------|---------|-------------|
| Planning | `NATS_URL` | `nats://nats:4222` | NATS connection URL |
| Planning | `FSM_CONFIG` | `config/agile.fsm.yaml` | FSM configuration path |
| Planning | `PORT` | `50051` | gRPC port |
| StoryCoach | `PORT` | `50052` | gRPC port |
| Workspace | `RIGOR_CONFIG` | `config/rigor.yaml` | Rigor profiles path |
| Workspace | `PORT` | `50053` | gRPC port |
| Workspace Runner | `NATS_URL` | `nats://nats:4222` | NATS connection URL |
| Workspace Runner | `K8S_NAMESPACE` | `swe` | K8s namespace for Jobs |

## Configuration

### FSM (Agile Lifecycle)

Edit `/config/agile.fsm.yaml` to customize:
- States (BACKLOG, DRAFT, DESIGN, BUILD, TEST, DOCS, DONE)
- Transitions with guards
- Human gates (which transitions require human approval)
- DoR thresholds per rigor level

### Rigor Profiles

Edit `/config/rigor.yaml` to customize:
- L0 (Experimental), L1 (Standard), L2 (High Quality), L3 (Mission Critical)
- Weights per dimension (build, unit, coverage, static, e2e, lint)
- Thresholds (pass rates, coverage %, SonarQube gates, etc.)
- Gating thresholds (pass: 90, warn: 70, block: <70)

## Workspace Containers

Agent workspaces run in ephemeral Kubernetes Jobs with a fully-tooled container image:

**Base image** (example): `ghcr.io/underpass-ai/agent-workspace:tooling-2025.10`

**Includes**:
- git, build toolchains (Go, Rust, Node, Python)
- Test frameworks (pytest, jest, cargo test)
- SonarQube Scanner CLI
- Playwright/Cypress for e2e
- golangci-lint, cargo clippy
- trivy (security scanning)

**Lifecycle**:
1. Clone repo + checkout branch
2. Apply patch/diff
3. Run build
4. Run unit tests + coverage
5. Run static analysis (SonarQube)
6. Run e2e tests
7. Create/update PR with status
8. Publish WorkspaceReport to `agent.responses`

**RBAC**: `workspace-runner` ServiceAccount can create Jobs, read Pod logs

## Testing Strategy

- **Unit tests**: Go services (in-memory FSM, scorer logic)
- **Integration tests**: NATS pub/sub flows (requires NATS container)
- **E2E tests**: Full flow via Gateway REST API (requires K8s cluster)
- **Contract tests**: gRPC proto validation, AsyncAPI message schema validation

Run tests:
```bash
cd services
make test
```

## Observability

- **Logs**: Structured JSON logs from all Go services
- **Traces**: OpenTelemetry spans with `trace_id` propagated in events
- **Metrics**: Prometheus endpoints (TODO: add to services)
- **NATS Monitoring**: `http://nats:8222` (JetStream dashboard)

## Security

- **ServiceAccounts**: Least-privilege RBAC per microservice
- **Secrets**: K8s Secrets for Git PAT, SonarQube token, etc.
- **NetworkPolicies**: Restrict workspace Pods to internal traffic only
- **Image scanning**: trivy scans in CI/CD
- **TLS**: cert-manager for Ingress TLS

## Migration from Existing Python Architecture

The existing Python orchestrator and context code can coexist with this new architecture:

1. **Phase 1** (current): New Go services + UI deployed alongside Python
2. **Phase 2**: Gradually migrate orchestration logic from Python to Go Orchestrator service
3. **Phase 3**: Migrate Context Python code to Go Context service (or keep Python with gRPC wrapper)
4. **Phase 4**: Python remains only for agent execution (Ray workers)

## References

- **NATS JetStream**: https://docs.nats.io/nats-concepts/jetstream
- **gRPC**: https://grpc.io/docs/languages/go/ and https://grpc.io/docs/languages/python/
- **OpenAPI**: https://swagger.io/specification/
- **AsyncAPI**: https://www.asyncapi.com/docs/reference/specification/v2.6.0
- **DDD**: https://www.domainlanguage.com/ddd/
- **Event Storming**: https://www.eventstorming.com/
- **INVEST**: https://en.wikipedia.org/wiki/INVEST_(mnemonic)
- **Gherkin/BDD**: https://cucumber.io/docs/gherkin/reference/

## Next Steps

1. Implement Gateway service (Go REST/SSE + gRPC bridge)
2. Implement Context service (migrate from Python or wrap existing)
3. Implement Orchestrator service (consumes `agile.events`, produces `agent.requests`)
4. Add OpenTelemetry instrumentation
5. Add Prometheus metrics
6. Add Helm chart for easier deployment
7. CI/CD pipeline for automated builds + deployments
8. Integration tests with real NATS + K8s

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

See [LICENSE](LICENSE).



