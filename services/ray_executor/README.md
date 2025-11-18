# Services: Ray Executor Bounded Context

## Overview

`services/ray_executor` is the **Gateway Microservice** for the Ray Cluster. It acts as the bridge between the standard Kubernetes microservices ecosystem (Orchestrator, Planning, etc.) and the high-performance distributed computing environment of Ray.

Its primary responsibility is to receive gRPC requests for AI tasks (deliberations, executions) and submit them as **Ray Jobs** using the logic defined in `core/ray_jobs`.

It follows **Hexagonal Architecture (Ports & Adapters)** to ensure the domain logic is decoupled from the specific Ray client implementation and transport mechanisms.

---

## 🏗 Architecture

### Layers

1.  **Domain Layer** (`domain/`)
    *   **Entities**: `DeliberationRequest`, `DeliberationResult`.
    *   **Ports (Interfaces)**:
        *   `RayClusterPort`: Contract for submitting jobs to Ray.
        *   `NATSPublisherPort`: Contract for publishing lifecycle events.
    *   *Responsibility*: Pure business logic for validation and task modeling.

2.  **Application Layer** (`application/`)
    *   **Use Cases**:
        *   `ExecuteDeliberationUseCase`: Orchestrates the submission of a task. Generates IDs, submits to Ray, and publishes initial events.
        *   `GetDeliberationStatusUseCase`: Checks the status of running jobs.
        *   `GetActiveJobsUseCase`: Lists all currently running Ray tasks.
    *   *Responsibility*: Coordination of domain objects and ports.

3.  **Infrastructure Layer** (`infrastructure/`)
    *   **Adapters**:
        *   `RayClusterAdapter`: Implements `RayClusterPort`. It uses the Ray Client SDK to connect to the Ray Head node and submit tasks using `core.ray_jobs.RayAgentExecutor`.
        *   `NATSPublisherAdapter`: Implements `NATSPublisherPort` to send events to NATS JetStream.
        *   `RayExecutorServiceServicer`: The **gRPC Entry Point**. Translates Protobuf messages into Domain Entities.
    *   *Responsibility*: Technology-specific implementations.

### Relationship with `core/ray_jobs`

This service is tightly coupled with the `core/ray_jobs` bounded context:

*   **`services/ray_executor`**: The **Submitter**. It runs as a standard K8s pod, connects to Ray via Client, and *triggers* execution.
*   **`core/ray_jobs`**: The **Payload**. It contains the code (`RayAgentExecutor`, `VLLMAgent`) that is serialized (pickled) and *executed* on the Ray Workers.

The `RayClusterAdapter` imports `RayAgentFactory` and `RayAgentExecutor` from `core.ray_jobs` to construct the job payload.

---

## 🔌 API Interface

The service exposes a **gRPC API** defined in `specs/fleet/ray_executor/v1/ray_executor.proto`.

### Key RPCs

*   `ExecuteDeliberation`: Submit a new multi-agent deliberation task.
*   `GetDeliberationStatus`: Poll for the result of a specific deliberation.
*   `GetActiveJobs`: List all active jobs on the cluster.
*   `GetStatus`: Health check and service statistics.

---

## ⚙️ Configuration

The service is configured via Environment Variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GRPC_PORT` | `50056` | Port for the gRPC server. |
| `RAY_ADDRESS` | `ray://ray-gpu-head-svc...:10001` | Address of the Ray Cluster Head Node (Client Port). |
| `NATS_URL` | `nats://nats...:4222` | URL for NATS JetStream connection. |
| `ENABLE_NATS` | `true` | Whether to publish events to NATS. |

---

## 🚀 Development & Deployment

### Running Locally (with remote Ray)

To run the service locally but connect to a remote Ray cluster (e.g., via port-forward):

```bash
# 1. Port forward Ray Head
kubectl port-forward -n ray svc/ray-gpu-head-svc 10001:10001

# 2. Set Env Vars
export RAY_ADDRESS="ray://localhost:10001"
export NATS_URL="nats://localhost:4222" # If NATS is local

# 3. Run Server
python services/ray_executor/server.py
```

### Docker / K8s

The service is deployed as a standard Deployment in Kubernetes. It requires access to the Ray Client port (10001) and NATS.

```bash
# Build
make build-ray-executor

# Deploy
kubectl apply -f deploy/k8s/services/ray-executor.yaml
```

