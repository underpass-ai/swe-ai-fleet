# SWE AI Fleet

<div align="center">
  <img src="logo.svg" alt="SWE AI Fleet Logo" width="200" height="200">
  <h3>Multi-Agent Software Engineering at the Edge</h3>
</div>

[![CI](https://github.com/underpass-ai/swe-ai-fleet/actions/workflows/ci.yml/badge.svg)](https://github.com/underpass-ai/swe-ai-fleet/actions/workflows/ci.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=underpass-ai-swe-ai-fleet&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=underpass-ai-swe-ai-fleet)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=underpass-ai-swe-ai-fleet&metric=coverage)](https://sonarcloud.io/summary/new_code?id=underpass-ai-swe-ai-fleet)

## 🎯 Overview

**SWE AI Fleet** is an open-source, multi-agent system for software development and systems architecture. It orchestrates role-based LLM agents (developers, devops, data, QA, architect) with Ray/KubeRay, provides safe tool wrappers (kubectl, helm, psql, etc.), and maintains a long-term knowledge graph (Neo4j) plus a short-term memory (Redis).

## 🚀 Key Features

### 🤖 Multi-Agent Orchestration
- **Role-based LLM Agents**: Developers, DevOps, QA, Architects, Data Engineers
- **Intelligent Task Routing**: Automatic assignment based on role and expertise
- **Collaborative Decision Making**: Agent councils for complex problem-solving
- **Human-in-the-Loop**: Approval workflows and oversight

### 🧠 Intelligent Context Management
- **Domain-Driven Design**: Clean, maintainable architecture
- **Context Assembly**: Intelligent prompt building with scope enforcement
- **Session Rehydration**: Persistent context across sessions
- **Analytics Integration**: Graph analytics for decision insights

### 🔧 Containerized Tool Execution
- **Runner Contract**: Standardized TaskSpec/TaskResult protocol for agent-container interaction
- **Multi-Runtime Support**: Podman, Docker, and Kubernetes execution modes
- **Secure Sandboxing**: Isolated execution with resource limits and audit trails
- **Testcontainers Integration**: Automated test environment provisioning
- **MCP Integration**: Model Context Protocol support for seamless agent communication

### 📊 Advanced Analytics & Reporting
- **Decision Graph Analytics**: Critical decision identification and cycle detection
- **Topological Analysis**: Dependency layering and impact assessment
- **Implementation Reports**: Comprehensive project documentation
- **Real-time Insights**: Live analytics integration

### 🛡️ Safe Tool Execution
- **Sandboxed Environment**: Secure tool execution with validation
- **Kubernetes Integration**: kubectl and Helm tool wrappers
- **Database Operations**: PostgreSQL tool with safety checks
- **Audit Logging**: Complete execution traceability

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   UI/PO Human   │───▶│   Orchestrator   │───▶│  Context        │
│                 │    │                  │    │  Assembler     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Agent Router   │    │  Prompt Scope   │
                       │                  │    │  Policy         │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  LLM Councils    │    │   Tools         │
                       │  (Dev, DevOps,   │───▶│   Gateway       │
                       │   QA, Arch,      │    │   (Sandbox)     │
                       │   Data)          │    │                 │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Memory Layer   │    │   Analytics     │
                       │  Redis + Neo4j   │    │   Engine        │
                       └──────────────────┘    └─────────────────┘
```

## 📁 Repository Structure

```
src/swe_ai_fleet/
├── cli/                    # Command line interface
├── context/               # Intelligent context system
│   ├── adapters/         # Data source adapters
│   ├── domain/           # Domain models (DDD)
│   │   ├── scopes/       # Scope management
├── tools/                 # Tool execution system
│   ├── runner/           # Containerized task runner
│   │   ├── agent-task    # Standardized task execution shim
│   │   ├── runner_tool.py # MCP Runner Tool implementation
│   │   ├── examples/     # TaskSpec/TaskResult examples
│   │   └── Containerfile # Multi-tool container image
│   ├── adapters/         # Tool adapters (kubectl, helm, psql)
│   ├── domain/           # Tool domain models
│   ├── ports/            # Tool interfaces
│   └── services/          # Tool services
│   │   └── context_sections.py  # Context organization
│   ├── ports/            # Interfaces/Protocols
│   ├── context_assembler.py    # Main assembler
│   ├── session_rehydration.py  # Session rehydration
│   └── utils.py
├── memory/               # Memory system
│   ├── redis_store.py    # Redis store implementation
│   ├── neo4j_store.py    # Neo4j store (base)
│   ├── cataloger.py      # Memory catalog
│   └── summarizer.py     # Automatic summaries
├── models/               # Data models
├── orchestrator/         # Agent orchestration
│   ├── architect.py      # Architect agent
│   ├── council.py        # Agent council
│   ├── router.py         # Task router
│   └── config.py         # Configuration
├── reports/              # Report generation
│   ├── adapters/         # Analytics adapters
│   ├── domain/           # Report domain models
│   ├── ports/            # Report interfaces
│   └── report_usecase.py # Implementation reports
├── tools/                # Execution tools
│   ├── kubectl_tool.py   # kubectl tool
│   ├── helm_tool.py      # Helm tool
│   ├── psql_tool.py      # PostgreSQL tool
│   └── validators.py     # Validators
└── evaluators/           # Quality evaluators
```

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- Docker
- kind (Kubernetes in Docker)
- kubectl
- helm

### Local Development Setup

1. **Clone and Setup**
   ```bash
   git clone https://github.com/underpass-ai/swe-ai-fleet.git
   cd swe-ai-fleet
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

2. **Start Local Stack**
   ```bash
   # Start Redis and Neo4j
   ./scripts/dev.sh
   
   # Run tests
   python -m pytest tests/unit/ -v
   ```

3. **Deploy to Kubernetes**
   ```bash
   # Deploy with Helm
   helm install swe-ai-fleet deploy/helm/
   
   # Run E2E tests
   ./scripts/e2e.sh
   ```

## 📊 Analytics Features

### Decision Graph Analytics
- **Critical Decision Identification**: Find high-impact decisions using indegree analysis
- **Cycle Detection**: Identify dependency cycles in decision graphs
- **Topological Layering**: Understand decision dependencies and execution order
- **Impact Assessment**: Analyze decision impacts on project timeline

### Implementation Reports
- **Comprehensive Documentation**: Auto-generated implementation reports
- **Analytics Integration**: Optional graph analytics sections
- **Real-time Updates**: Live report generation with latest data
- **Export Capabilities**: Markdown and structured data export

## 🧪 Testing

### Test Coverage
- **Unit Tests**: Comprehensive unit test coverage (69+ tests)
- **Integration Tests**: End-to-end integration testing
- **E2E Tests**: Full workflow testing with Redis and Neo4j
- **Code Quality**: Ruff linting and type checking

### Running Tests
```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# E2E tests (requires Redis/Neo4j)
python -m pytest tests/e2e/ -v

# Code quality
ruff check .
```

## 📚 Documentation

- **[Context Architecture](CONTEXT_ARCHITECTURE.md)**: Detailed system architecture
- **[Contributing](CONTRIBUTING.md)**: Development guidelines
- **[RFCs](docs/)**: Technical specifications and design decisions
- **[Roadmap](ROADMAP.md)**: Development roadmap and milestones

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:
- Code style and standards
- Testing requirements
- Pull request process
- Development setup

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/underpass-ai/swe-ai-fleet/issues)
- **Discussions**: [GitHub Discussions](https://github.com/underpass-ai/swe-ai-fleet/discussions)
- **Documentation**: [Project Wiki](https://github.com/underpass-ai/swe-ai-fleet/wiki)
