# Planning Service Documentation

**Version:** 1.0.0  
**Status:** ✅ Production Ready (Task Derivation migrated to separate service)  
**Architecture:** DDD + Hexagonal  
**Last Updated:** November 15, 2025

---

## 📚 Documentation Overview

This directory previously contained extensive audit and proposal documents related to the Planning Service implementation and the Task Derivation migration. All critical information has been consolidated into:

### Primary References

1. **Architecture Documentation**: See `services/planning/ARCHITECTURE.md`
   - Hexagonal architecture (domain, application, infrastructure layers)
   - DDD compliance and domain model
   - Data persistence (Neo4j + Valkey)
   - Event contracts and integrations

2. **Task Derivation Service**: See `services/task-derivation/README.md`
   - Complete task derivation flow (now separate microservice)
   - Event-driven integration between services
   - gRPC contracts with Planning Service

---

## ✅ Completed Refactoring

### Phase 1: Task Derivation Migration
The Planning Service underwent a major refactoring to extract Task Derivation logic into a dedicated microservice. This separation provides:

- **Single Responsibility Principle**: Planning Service now focuses only on story lifecycle management
- **Independent Scaling**: Task Derivation Service can scale with GPU cluster separately
- **Clear Event Contracts**: Defined async communication via NATS JetStream
- **Improved Testability**: Smaller, focused services

### Phase 2: Architecture Documentation
- Planning Service architecture properly documented in `ARCHITECTURE.md`
- Task Derivation Service architecture fully documented in its own `README.md`
- Cross-service integration documented in both services

---

## 🏗️ Planning Service Core Responsibilities

1. **Entity Management**: Project → Epic → Story → Task hierarchy
2. **Story Lifecycle**: FSM state machine (DRAFT → DONE)
3. **Decision Workflow**: Approval/rejection with human-in-the-loop
4. **Event Publishing**: Domain events for orchestrator integration
5. **Task Derivation Trigger**: Publishes `task.derivation.requested` events

---

## 📡 Integration Points

### Planning Service → Task Derivation Service
- **Event**: `task.derivation.requested` (NATS)
- **Trigger**: When plan is approved
- **Purpose**: Initiate automated task generation

### Task Derivation Service → Planning Service
- **gRPC**: GetPlanContext, CreateTasks, SaveTaskDependencies
- **Timing**: After LLM generates tasks
- **Purpose**: Store generated tasks in Planning Service

---

## 🧪 Quality Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Test Coverage | >90% | ✅ |
| Use Cases | 15+ | ✅ |
| Domain Entities | 4 | ✅ |
| Event Consumers | 2 | ✅ |
| Events Published | 8 | ✅ |
| No Reflection | ✅ | ✅ |
| DDD Compliant | ✅ | ✅ |

---

## 📖 How to Read This Documentation

1. **First Time**: Start with `services/planning/ARCHITECTURE.md` for the big picture
2. **Task Derivation**: Read `services/task-derivation/README.md` for complete flow
3. **Implementation Details**: Check the source code with inline comments
4. **Integration**: Reference both README.md files for cross-service contracts

---

## 🚀 Getting Started

```bash
# Install Planning Service
cd services/planning
pip install -e .

# Run tests
make test-unit

# Run server
python server.py
```

---

## 📝 Notes

**Archived Documentation**: Previous analysis documents (audit trails, proposals, state snapshots) have been consolidated. For historical context:

- ❌ `PENDING_TASKS.md` - Tasks completed with Task Derivation migration
- ❌ `PLANNING_SERVICE_STATE.md` - See ARCHITECTURE.md instead
- ❌ `TASK_DERIVATION_SERVICE_PROPOSAL.md` - Implemented; see services/task-derivation/README.md
- ❌ `AUDIT_*` files - Architectural compliance validated
- ❌ `RBAC_REVIEW.md` - Integrated into ARCHITECTURE.md

---

**Architecture**: DDD + Hexagonal  
**Pattern**: Event-Driven Microservices  
**Deployment**: Kubernetes  
**Status**: ✅ Production Ready

