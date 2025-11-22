# Monitoring Service (Beta)

> **Status**: 🚧 Beta. Active development.

The **Monitoring Service** provides a real-time dashboard for observing the SWE AI Fleet. It aggregates events from the multi-agent system, visualizes council deliberations, tracks agent status, and provides administrative controls.

It is built using a **Hexagonal Architecture** with a **FastAPI** backend and a **React** frontend.

## 🏗 Architecture

The service follows Domain-Driven Design (DDD) and Hexagonal Architecture principles:

- **Domain Layer** (`domain/`): Core entities (`MonitoringEvent`, `OrchestratorInfo`) and Ports (interfaces).
- **Application Layer** (`application/`): Use cases orchestrating business logic (e.g., `GetOrchestratorInfoUseCase`).
- **Infrastructure Layer** (`infrastructure/`): Adapters for external systems:
  - **NATS JetStream**: For event streaming (`NATSConnectionAdapter`).
  - **gRPC**: For querying the Orchestrator (`GrpcOrchestratorInfoAdapter`).
  - **FastAPI**: The driving adapter exposing the REST API and WebSockets.
  - **Environment**: For configuration (`EnvironmentConfigurationAdapter`).
- **Frontend** (`frontend/`): React SPA consuming the API.

## 🚀 Features

- **Real-time Event Stream**: Live feed of system events via NATS (Planning, Orchestration, Context, Agent Results).
- **System Overview**: Health status of NATS, Orchestrator, Context (Neo4j), and Ray Executor.
- **Council Visualization**: Active councils, agent roles, and statuses.
- **Deliberation Tracking**: Recent multi-agent deliberations and their outcomes.
- **Ray & vLLM Monitoring**: GPU usage, active jobs, and real-time LLM token streaming.
- **Admin Controls**: Tools to clear NATS streams, kill Ray jobs, or reset databases.

## 📡 API Reference

### WebSocket Endpoints

- `ws://<host>:<port>/ws`: Main event stream. Broadcasts `MonitoringEvent` JSON objects.
- `ws://<host>:<port>/ws/vllm-stream`: Real-time LLM generation stream.

### REST Endpoints

**Status & Info**
- `GET /api/health`: Service health check.
- `GET /api/system/status`: Status of all connected subsystems.
- `GET /api/councils`: Active councils and agents from Orchestrator.
- `GET /api/events`: Recent event history.

**Statistics**
- `GET /api/neo4j/stats`: Graph database node/relationship counts.
- `GET /api/valkey/stats`: Cache hit/miss stats.
- `GET /api/ray/cluster`: Ray cluster resource usage.
- `GET /api/ray/jobs`: Active Ray jobs.
- `GET /api/vllm/active-streams`: Currently streaming LLM tasks.

**Admin Operations**
- `POST /api/admin/nats/clear`: Delete all NATS streams.
- `POST /api/admin/ray/kill-jobs`: Terminate all Ray jobs.
- `POST /api/admin/valkey/clear`: Flush ValKey cache.
- `POST /api/admin/neo4j/clear`: Detach and delete all Neo4j nodes.
- `POST /api/admin/test-cases/execute`: Trigger a predefined test case (basic/medium/complex).

## ⚙️ Configuration

The service is configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `NATS_URL` | NATS JetStream connection URL | `nats://nats.swe-ai-fleet.svc.cluster.local:4222` |
| `ORCHESTRATOR_ADDRESS` | gRPC address of the Orchestrator | `orchestrator.swe-ai-fleet.svc.cluster.local:50055` |
| `PORT` | HTTP Server Port | `8080` |

## 🛠 Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Access to NATS and Orchestrator (or mocks)

### Backend (Python)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server**:
   ```bash
   python server.py
   ```

### Frontend (React)

1. **Navigate to frontend**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Run dev server**:
   ```bash
   npm run dev
   ```
   Access at `http://localhost:5173`.

4. **Build for production**:
   ```bash
   npm run build
   ```
   The backend serves the built artifacts from `frontend/dist` at the root URL `/`.

## 📦 Deployment

The service is deployed as a containerized application in Kubernetes.

- **Dockerfile**: Multi-stage build (Python backend + Node.js frontend build).
- **K8s Resources**: Typically deployed with a `Deployment`, `Service`, and `Ingress`.

See `deploy/k8s-integration/40-monitoring/` for deployment manifests.

## 🧪 Testing

Run unit tests with pytest:

```bash
pytest tests/
```

Tests cover:
- Domain entities and validation.
- Use cases (logic in isolation).
- Infrastructure adapters (using mocks).

