# SWE AI Fleet - Detailed Roadmap

## 🎯 Project Vision

Build a fleet of LLM agents specialized in software engineering that simulates a real human team (developers, devops, QA, architect, data engineer). The agents work in a coordinated manner, with atomic context per use case, and with the human as Product Owner (PO) who supervises and approves.

**Key differentiators:**
- **Complete traceability** of decisions and executions
- **Intelligent persistence** in Redis (short term) and Neo4j (long term/graph)
- **Guaranteed minimal context** for each role and subtask
- **Simulation of real software engineering processes**
- **Tool execution** with sandboxing and complete audit

## 🚀 Current Status (M0-M1 Completed)

### ✅ Basic Infrastructure
- [x] CRI‑O manifests for Redis + Neo4j
- [x] Unified Makefile for orchestration
- [x] E2E smoke test validated (kg_smoke.py → neo4j_writer)
- [x] Initial CI/CD (GitHub Actions)
- [x] Helm charts for Kubernetes

### ✅ Memory System
- [x] `RedisStoreImpl` for LLM calls/responses
- [x] TTL + Streams for ephemeral persistence
- [x] `Neo4jDecisionGraphAdapter` with DTOs and constraints
- [x] Partial Redis → Neo4j synchronization

### ✅ Intelligent Context
- [x] Atomic context per use case
- [x] `PromptScopePolicy`: information filtering by role
- [x] `ContextAssembler`: packaging for each agent
- [x] Scope matrix by role and phase (configurable YAML)

### ✅ Implemented Use Cases
- [x] Save LLM calls and responses (Redis)
- [x] Generate technical report for a use case
- [x] Continue ongoing project (context rehydration)
- [x] Task refinement / Sprint Planning

## 🎯 Milestone Roadmap

### M2 - Context and Minimization (In Progress)
**Objective:** Complete the intelligent context system and memory optimization

#### Priority Tasks
- [ ] **Automatic compression** of long sessions
- [ ] **Live context dashboard** (basic UI)
- [ ] **Advanced redactor** for secrets and sensitive data
- [ ] **Query optimization** Neo4j for critical dependencies
- [ ] **Intelligent cache** for frequent queries

#### Deliverables
- Automatic context compression system
- Basic UI for context monitoring
- Configurable redactor for different types of sensitive data
- Optimized queries for dependency analysis

### M3 - Agents and Roles (Next)
**Objective:** Implement the multi-agent system with specialized roles

#### Priority Tasks
- [ ] **Complete role definition**: Dev, DevOps, QA, Architect, Data
- [ ] **Multi-agents per role** with internal consultation (consensus)
- [ ] **Human PO as supervisor/decision maker**
- [ ] **Sprint Planning simulation** → automatically generated subtasks
- [ ] **Permission system** by role and phase

#### Deliverables
- Complete implementation of all roles
- Consensus system between agents of the same role
- Interface for human PO
- Automatic subtask generator

### M4 - Tool Execution (Critical) - 🚧 In Progress
**Objective:** Implement infrastructure to execute development tools

#### ✅ Completed Tasks
- [x] **Runner Contract Protocol**: TaskSpec/TaskResult standardization
- [x] **Containerized Execution**: CRI‑O now; Kubernetes Jobs next
- [x] **agent-task Shim**: Standardized task execution interface
- [x] **MCP Integration**: Model Context Protocol support
- [x] **Testcontainers Integration**: Automated test environment provisioning
- [x] **Security Features**: Non-root execution, resource limits, audit trails
- [x] **Context Integration**: Redis/Neo4j integration for traceability

#### 🚧 In Progress Tasks
- [ ] **Tool Gateway** (HTTP/gRPC) with FastAPI
- [ ] **Policy Engine**: Role-based access control and validation
- [ ] **Advanced Sandboxing**: Enhanced security and isolation
- [ ] **Infrastructure Tools**: Enhanced kubectl, docker, psql, redis-cli integration

Known gap: Runner Kubernetes mode is WIP; migrate local execution to CRI‑O via Jobs/`crictl`.

#### Deliverables
- ✅ Runner Contract Protocol implementation
- ✅ Containerized task execution system
- ✅ MCP Runner Tool with async execution
- 🚧 Enhanced Tool Gateway with policy engine
- 🚧 Complete audit and monitoring system

#### Tool Architecture
```
Tool Gateway (FastAPI) → Policy Engine → Sandbox Executor → Audit Log
     ↓
Redis Streams → Neo4j (complete traceability)
```

#### Security and Isolation
- Ephemeral rootless containers
- Outbound network blocked by default
- CPU/Memory/PID limits
- Audit of each execution

### M5 - Simulated E2E Flow (Planned)
**Objective:** Complete end-to-end use case

#### Priority Tasks
- [ ] **Complete flow**: Design → Decisions → Implementation → Test → Report
- [ ] **Technical report generation** from Neo4j graph
- [ ] **Continuation of previous projects** (context rehydration)
- [ ] **Complete traceability** (who decided what and when)
- [ ] **Quality and performance metrics**

#### Deliverables
- Complete development pipeline
- Automatic reporting system
- Performance and quality metrics
- Use case documentation

### M6 - Community and Open Source
**Objective:** Prepare the project for the community

#### Priority Tasks
- [ ] **Landing page** (Next.js + Tailwind)
- [ ] **Clear documentation** and use case examples
- [ ] **Guide for extending** with new tools
- [ ] **GitHub publication** + OSS forum outreach
- [ ] **Contribution system** and governance

#### Deliverables
- Professional landing page
- Complete documentation
- Contribution guides
- Active community

## 🔧 Technical Implementation

### Technology Stack
- **Backend**: Python 3.13+, FastAPI, Redis, Neo4j
- **Infrastructure**: CRI‑O (local), Kubernetes + Ray/KubeRay (next phase)
- **Frontend**: Next.js + Tailwind (M6)
- **Testing**: pytest, e2e tests
- **CI/CD**: GitHub Actions

### Component Architecture
```
UI/PO → Orchestrator → Context Assembler → Agents → Tools → Memory (Redis + Neo4j)
```

### Design Patterns
- **Clean Architecture** with ports/adapters
- **Event Sourcing** with Redis Streams
- **CQRS** for complex queries
- **Policy-based** for access control
- **Sandbox pattern** for secure execution

## 📊 Success Metrics

### Technical
- [ ] **Response time** < 2s for context queries
- [ ] **Context compression** > 60% for long sessions
- [ ] **Test coverage** > 90%
- [ ] **Traceability** 100% of decisions and executions

### Functional
- [ ] **Complete use cases** implemented and working
- [ ] **Integration with real development tools**
- [ ] **Coordinated and efficient multi-agent system**
- [ ] **Clear and complete documentation**

## 🚨 Risks and Mitigations

### Technical Risks
- **Neo4j graph complexity**: Implement optimized queries and cache
- **Tool security**: Strict sandboxing and complete audit
- **Performance**: Continuous monitoring and incremental optimizations

### Project Risks
- **Scope creep**: Maintain focus on M4 (tools) as priority
- **External dependencies**: Contingency plan for LLMs and tools
- **Community**: Start early engagement in M3-M4

## 🎯 Immediate Next Steps

1. **Complete M2** (Context and Minimization)
2. **Start M4** (Tool Execution) - **CRITICAL**
3. **Prepare architecture** for M3 (Agents and Roles)
4. **Validate existing use cases**
5. **Optimize Neo4j queries**

## 📝 Implementation Notes

### Critical Priority: M4 (Tools)
The jump from M3 to M4 is fundamental because it transforms the system from "talk and reason" to "execute, validate and learn" autonomously, closing the complete cycle of real software engineering.

### Integration with Existing Tools
- **kubectl_tool.py**: Base for infrastructure tools
- **helm_tool.py**: Helm integration
- **psql_tool.py**: Database tools
- **validators.py**: Tool validation

### Extensibility
The system is designed to be extensible:
- New roles through YAML configuration
- New tools through the tool system
- New memory types through adapters
- New use cases through the orchestrator