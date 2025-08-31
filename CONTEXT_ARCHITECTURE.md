# SWE AI Fleet - Context Architecture

## 🎯 Project Description

**SWE AI Fleet** is an open-source multi-agent system for software development and systems engineering. It simulates a real development team with specialized LLM agents (developers, devops, QA, architect, data engineer) that work in a coordinated manner under human supervision.

## 🏗️ System Architecture

### Core Components

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
                       │   Memory Layer   │    │   Audit Log      │
                       │  Redis + Neo4j   │    │   (Streams)      │
                       └──────────────────┘    └─────────────────┘
```

### Memory Layers

1. **Redis (Tier-0)**: Ephemeral working memory with TTL
   - Streams for LLM events
   - Cache for frequent context
   - Automatic TTL for cleanup

2. **Neo4j (Tier-2)**: Decision and dependency graph
   - Nodes: Decisions, Tasks, Dependencies, Milestones
   - Relationships: DECIDES, DEPENDS_ON, IMPACTS, APPROVED_BY
   - Complete use case traceability

## 📁 Code Structure

### Module Organization

```
src/swe_ai_fleet/
├── __init__.py
├── cli/                    # Command line interface
├── context/               # Intelligent context system
│   ├── adapters/         # Data source adapters
│   ├── domain/           # Domain models
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
├── tools/                # Execution tools
│   ├── kubectl_tool.py   # kubectl tool
│   ├── helm_tool.py      # Helm tool
│   ├── psql_tool.py      # PostgreSQL tool
│   └── validators.py     # Validators
└── evaluators/           # Quality evaluators
```

## 🔧 Current Implementation Status

### ✅ Completed (M0-M1)

- **Infrastructure**: Docker Compose for Redis + Neo4j
- **Redis Memory**: `RedisStoreImpl` with Streams and TTL
- **Context**: `ContextAssembler` and `PromptScopePolicy`
- **Use cases**: LLM event persistence, session rehydration
- **Testing**: E2E tests for core components

### 🚧 In Progress (M2)

- **Context optimization**: Automatic compression of long sessions
- **Advanced redaction**: For secrets and sensitive data
- **Context dashboard**: Basic UI for monitoring

### 📋 Next (M3-M4)

- **Multi-agent system**: Complete role implementation
- **Tool Gateway**: Secure execution of development tools
- **Sandboxing**: Execution isolation

## 🎨 Design Patterns and Conventions

### Clean Architecture

- **Ports/Adapters**: Clear interfaces between layers
- **Protocols**: Use of `typing.Protocol` for contracts
- **DTOs**: Immutable transfer objects
- **Use Cases**: Encapsulated business logic

### Code Conventions

- **Python 3.13+**: Use of modern features
- **Type hints**: Complete throughout the code
- **Dataclasses**: For simple data structures
- **Async/await**: For I/O intensive operations
- **Ruff**: Configured linter and formatter

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
└── e2e/           # End-to-end tests
    ├── test_redis_store_e2e.py
    ├── test_context_assembler_e2e.py
    ├── test_session_rehydration_e2e.py
    └── test_decision_enriched_report_e2e.py
```

## 🚀 Development Guidelines

### Adding New Features

1. **Define the Protocol/Port** in the corresponding module
2. **Implement the functionality** following existing patterns
3. **Add tests** for unit and integration
4. **Update documentation** and use cases

### Example: Adding New Tool

```python
# 1. Define the protocol
class TerraformTool(Protocol):
    def validate_config(self, config_path: str) -> tuple[bool, str]: ...
    def plan_changes(self, config_path: str) -> tuple[bool, str]: ...

# 2. Implement
class TerraformToolImpl:
    def validate_config(self, config_path: str) -> tuple[bool, str]:
        # Implementation with subprocess
        pass

# 3. Add to role configuration
TERRAFORM_ALLOWLIST = ["terraform", "tf"]
```

### Error Handling

- **Specific exceptions**: Create domain exceptions when necessary
- **Structured logging**: Use logging with context
- **Fallbacks**: Implement fallback strategies for critical operations

## 🔒 Security and Isolation

### Security Principles

1. **Principle of least privilege**: Each agent only accesses what's necessary
2. **Sandboxing**: Isolated tool execution
3. **Complete audit**: Log of all operations
4. **Secret redaction**: Automatic removal of sensitive data

### Access Control

- **RBAC by role**: Different permissions based on agent role
- **Scope policies**: Granular control of available context
- **Tool allowlists**: Whitelists of allowed commands by role

## 📊 Monitoring and Observability

### Key Metrics

- **Response time**: For context queries
- **Context compression**: Minimization efficiency
- **Memory usage**: Redis and Neo4j
- **Traceability**: Coverage of audited events

### Logging

- **Structured logging**: JSON with structured context
- **Correlation IDs**: For tracking complete flows
- **Log levels**: Configurable by component

## 🧪 Testing and Quality

### Testing Strategy

- **Unit tests**: For business logic
- **Integration tests**: For adapters and services
- **E2E tests**: For complete flows
- **Performance tests**: For critical operations

### Coverage Goals

- **Code coverage**: > 90%
- **Use case coverage**: 100%
- **Regression tests**: Automated in CI/CD

## 🚀 Deployment and Operations

### Local Environment (Mac M2)

```bash
# Start infrastructure
make redis-up

# Run tests
make test-e2e

# Development
source scripts/dev.sh
```

### Production Environment

- **Kubernetes**: With Ray/KubeRay for scalability
- **Helm charts**: For automated deployment
- **Monitoring**: Prometheus + Grafana
- **Logging**: Centralized with ELK stack

## 📚 Resources and References

### Documentation

- **README.md**: Project overview
- **ROADMAP.md**: Basic roadmap
- **ROADMAP_DETAILED.md**: Detailed roadmap (this document)
- **docs/**: Detailed technical documentation

### Use Cases

1. **Save LLM events**: Persistence in Redis
2. **Session rehydration**: Context recovery
3. **Report generation**: From Neo4j graph
4. **Sprint Planning**: Automatic subtask generation

### Development Tools

- **Makefile**: Orchestration commands
- **Docker Compose**: Local infrastructure
- **Helm**: Charts for Kubernetes
- **GitHub Actions**: CI/CD pipeline

## 🎯 Next Steps for Cursor

### Immediate Priorities

1. **Complete M2**: Context and minimization
2. **Start M4**: Tool Gateway implementation
3. **Optimize queries**: Neo4j for critical dependencies
4. **Improve testing**: Coverage and edge cases

### Focus Areas

- **Performance**: Query and cache optimization
- **Security**: Sandboxing and access control
- **Testing**: Automation and coverage
- **Documentation**: Usage and contribution guides

### Tool Integration

- **Local LLMs**: Qwen, Llama, Mistral
- **Development tools**: Git, Docker, kubectl
- **Testing frameworks**: pytest, JUnit, Go test
- **CI/CD**: GitHub Actions, GitLab CI

---

**Note**: This document is updated regularly. For the most recent information, consult the source code and GitHub issues.