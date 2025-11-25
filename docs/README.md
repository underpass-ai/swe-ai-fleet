# SWE AI Fleet Documentation

Welcome to the documentation for **SWE AI Fleet**, an autonomous multi-agent software engineering platform.

## 📚 Documentation Map

### 🏢 Business & Vision

Understanding the mission, value proposition, and strategic direction.

- **[Investor One Pager](business/INVESTOR_ONE_PAGER.md)**: Concise summary of the problem, solution, and market opportunity.

### 🏗️ Architecture

Understanding the system design, patterns, and core concepts.

- **[System Overview](architecture/OVERVIEW.md)**: High-level architecture, "Decision-Centric" AI, and key technologies.
- **[Core Bounded Contexts](architecture/CORE_CONTEXTS.md)**: Deep dive into the domain logic (Agents, Context, Orchestrator, Workflow).
- **[Microservices](architecture/MICROSERVICES.md)**: Details on the deployed services (Planning, Monitoring, Ray Executor, etc.).

### 📜 Normative Standards & Guidelines

The "Laws" of the project that must be followed.

- **[Hexagonal Architecture](normative/HEXAGONAL_ARCHITECTURE.md)**: The normative guide for our code structure (Ports & Adapters).
- **[API-First Strategy](../specs/API_FIRST_STRATEGY.md)**: Strategy for defining contracts before implementation.
- **[Human-in-the-Loop](normative/HUMAN_IN_THE_LOOP.md)**: Our philosophy on AI-human collaboration and approval gates.
- **[Testing Architecture](TESTING_ARCHITECTURE.md)**: Testing pyramid, mandatory requirements, and tooling strategy.
- **[Mermaid Style Guide](MERMAID_STYLE_GUIDE.md)**: Standards for creating consistent diagrams.

### 🚀 Getting Started

Guides for deploying and running the fleet.

- **[Getting Started Guide](getting-started/README.md)**: Entry point for new users.
- **[Prerequisites](getting-started/prerequisites.md)**: Hardware and software requirements.
- **[Deployment Guide](../deploy/k8s/README.md)**: Detailed instructions for Kubernetes deployment.

### 🛠️ Operational Guides

- **[Infrastructure](../deploy/k8s/README.md)**: Kubernetes, NATS, Neo4j, and Ray setup.
- **[Monitoring](../services/monitoring/README.md)**: Using the dashboard and observability tools.

### 📖 Reference

- **[API Specifications](../specs/)**: gRPC and AsyncAPI definitions.
- **[Glossary](reference/GLOSSARY.md)**: Common terms (Council, Deliberation, Rehydration).

---

## 🔍 Where is the code?

The codebase is organized by **Bounded Contexts** and **Services**. Each module has its own documentation.

### 🧠 Core Domain (`core/`)

Reusable domain logic, entities, and use cases.

- **[Agents & Tools](../core/agents_and_tools/README.md)**: Agent definitions and tool implementations.
- **[Context](../core/context/README.md)**: Context management and knowledge graph logic.
- **[Orchestrator](../core/orchestrator/README.md)**: Multi-agent deliberation and orchestration logic.
- **[Ray Jobs](../core/ray_jobs/README.md)**: Remote execution logic for Ray.

### 🚢 Services (`services/`)

Deployable gRPC microservices wrapping the core logic.

- **[Context Service](../services/context/README.md)**: Exposes context operations via gRPC.
- **[Monitoring Service](../services/monitoring/README.md)**: Dashboard and observability.
- **[Orchestrator Service](../services/orchestrator/README.md)**: Runs the agent councils.
- **[Planning Service](../services/planning/README.md)**: Project management and story mapping.
- **[Ray Executor](../services/ray_executor/README.md)**: Gateway to the GPU cluster.
- **[Task Derivation](../services/task_derivation/README.md)**: Auto-generates tasks from stories.
- **[Workflow Service](../services/workflow/README.md)**: Manages state transitions and FSMs.

### 📦 Other Directories

| Area | Directory | Description |
|------|-----------|-------------|
| **Deployment** | [`deploy/`](../deploy/) | K8s manifests and infrastructure scripts. |
| **Specs** | [`specs/`](../specs/) | Protobuf and AsyncAPI definitions. |
