# 🚨 CRITICAL TASK: Orchestrator-Context Coupling

**Created**: October 28, 2025  
**Status**: ⚠️ **HIGH PRIORITY** — Architectural Violation  
**Related Issue**: Bounded Contexts Coupling

---

## ⚠️ Problem Statement

The `orchestrator` bounded context (`core/orchestrator/`) is **directly coupled** to `context` bounded context (`core/context/`) via imports:

```python
# ❌ VIOLATION in core/orchestrator/handler/agent_job_worker.py
from core.context.ports.graph_command_port import GraphCommandPort
from core.context.ports.graph_query_port import GraphQueryPort
from core.context.usecases.rehydrate_context import RehydrateContextUseCase
from core.context.usecases.update_subtask_status import UpdateSubtaskStatusUseCase
```

This violates **Domain-Driven Design (DDD)** principles where bounded contexts must remain independent.

---

## 📋 What Needs to Be Done

### 1. Create gRPC Contract
- **File**: `specs/context.proto`
- **Actions**:
  - Define `ContextService` with methods:
    - `GetContext(ContextRequest) returns ContextResponse`
    - `RehydrateContext(RehydrationRequest) returns RehydrationResponse`
    - `UpdateSubtaskStatus(UpdateRequest) returns UpdateResponse`

### 2. Refactor Core/orchestrator
- **File**: `core/orchestrator/handler/agent_job_worker.py`
- **Actions**:
  - Remove all imports from `core.context.*`
  - Create port `ContextServicePort` in `core/orchestrator/domain/ports/`
  - Use dependency injection to receive context operations
  - Make worker receive context operations as injected dependency

### 3. Implement gRPC Adapter
- **File**: `services/orchestrator/infrastructure/adapters/context_grpc_adapter.py`
- **Actions**:
  - Implement `ContextServicePort` using gRPC client
  - Connect to `context-service:50054` via gRPC
  - Map domain operations to gRPC calls

### 4. Implement Context Service Methods
- **File**: `services/context/server.py`
- **Actions**:
  - Add handlers for gRPC methods defined in proto
  - Call core use cases from handlers
  - Return proper gRPC responses

---

## 🎯 Success Criteria

✅ **Core bounded contexts isolated**:
- `core/orchestrator/` does NOT import from `core/context/`
- `core/context/` does NOT import from `core/orchestrator/`

✅ **Microservices communicate via APIs**:
- `services/orchestrator/` calls `services/context/` via gRPC
- No direct imports between services

✅ **Tests pass**:
- Unit tests for core isolated
- Integration tests for gRPC communication
- E2E tests for full flow

---

## 📚 Detailed Documentation

See: `docs/architecture/BOUNDED_CONTEXTS_COUPLING_ANALYSIS.md`

---

## ⏰ When to Address

**Priority**: HIGH  
**Timeline**: After completing current `agents_and_tools` hexagonal refactor

**Blockers**:
- None (can be tackled immediately after current refactor)

**Dependencies**:
- gRPC contract definitions in `specs/context.proto`
- gRPC code generation (`make gen`)

---

## 🔗 Related Files

- `core/orchestrator/handler/agent_job_worker.py` — Source of violation
- `services/orchestrator/` — Orchestrator microservice
- `services/context/` — Context microservice
- `specs/context.proto` — gRPC contract (to be created/updated)
- `docs/architecture/BOUNDED_CONTEXTS_COUPLING_ANALYSIS.md` — Detailed analysis

---

**Assigned to**: @tirso  
**Estimated effort**: 2-3 hours  
**Risk level**: Medium (well-defined scope)

