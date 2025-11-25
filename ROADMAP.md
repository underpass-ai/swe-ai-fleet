# Roadmap

**Status**: Beta (Core Services Operational)
**Last Updated**: November 2025

This document tracks the high-level milestones of the SWE AI Fleet project.

---

## 🟢 Completed / Operational

### Core Platform
- [x] **Hexagonal Architecture Foundation**: All services refactored to Ports & Adapters pattern.
- [x] **Knowledge Graph**: Neo4j schema for Projects, Epics, Stories, Tasks, and Decisions.
- [x] **Context Engine**: "Session Rehydration" logic to assemble surgical context.
- [x] **Multi-Agent Deliberation**: Orchestrator service capable of running Councils (Generate-Critique-Revise).
- [x] **RBAC System**: Level 1 (Tool Access), Level 2 (Workflow Action), and Level 3 (Data Access) implemented.

### Services
- [x] **Planning Service**: Story lifecycle management.
- [x] **Workflow Service**: Task FSM and RBAC Level 2/3 enforcement.
- [x] **Ray Executor**: Distributed agent execution on GPU cluster.
- [x] **Monitoring Service**: Real-time dashboard (NATS events).
- [x] **Task Derivation Service**: Automated breakdown of Plans into Tasks (Beta).

### Infrastructure
- [x] **Kubernetes Deployment**: Full manifests for all services.
- [x] **Ray Integration**: GPU time-slicing and worker management.
- [x] **NATS JetStream**: Event backbone setup.

---

## 🟡 In Progress

### Product Owner (PO) Experience
- [ ] **PO UI**: Specialized interface for approving Stories and Plans.
- [ ] **Approval Workflows**: Integration with Workflow Service for human-in-the-loop gates.

### Stability & Performance
- [ ] **End-to-End Testing**: Complete regression suite for the full lifecycle.
- [ ] **Load Testing**: Benchmarking the Ray cluster under heavy deliberation load.

---

## ⚪ Planned (Future)

- [ ] **Community Release**: Public documentation site and installer.
- [ ] **SaaS Control Plane**: Multi-tenant management layer (optional).
- [ ] **Advanced Tool Sandboxing**: gVisor/Kata Containers integration for agent tools.
- [ ] **OpenTelemetry**: Distributed tracing across microservices.

---

## 📊 Service Status Matrix

| Service | Status | Language | Location |
|---------|--------|----------|----------|
| **Planning** | 🟢 Production | Python | `services/planning` |
| **Workflow** | 🟢 Production | Python | `services/workflow` |
| **Orchestrator** | 🟢 Production | Python | `services/orchestrator` |
| **Context** | 🟢 Production | Python | `services/context` |
| **Ray Executor** | 🟢 Production | Python | `services/ray_executor` |
| **Monitoring** | 🟢 Production | Python | `services/monitoring` |
| **Task Derivation** | 🟡 Beta | Python | `services/task_derivation` |
