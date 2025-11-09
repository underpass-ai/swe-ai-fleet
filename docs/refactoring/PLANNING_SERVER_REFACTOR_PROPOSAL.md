# Planning Server Refactor Proposal
**Date**: 2025-11-09
**Current State**: 784 lines (God Class anti-pattern)
**Target**: Split into modular handlers
**Priority**: MEDIUM (technical debt, not blocking)

---

## 🚨 Current Problems

### 1. God Class Anti-Pattern
```
services/planning/server.py: 784 lines ⚠️

Comparison with other services:
- Workflow:     373 lines ✅
- Ray Executor: 379 lines ✅
- Orchestrator: 898 lines ⚠️ (also needs refactor)
- Context:    1,036 lines 🔥 (worst)
```

**Symptoms**:
- 12 RPC methods in single class
- Hard to test individual handlers
- Hard to reason about (too much scrolling)
- Violation of Single Responsibility Principle (SRP)

### 2. Boilerplate Duplication
Every handler repeats:
```python
try:
    logger.info(...)
    # Business logic (2-3 lines)
    return pb2.Response(...)
except ValueError as e:
    logger.warning(...)
    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
    return pb2.Response(success=False, message=str(e))
except Exception as e:
    logger.error(...)
    context.set_code(grpc.StatusCode.INTERNAL)
    return pb2.Response(success=False, message=str(e))
```

**Impact**: ~30 lines per handler × 12 handlers = 360 lines of boilerplate

### 3. Tight Coupling
- All 8 use cases injected in constructor
- Single servicer knows about ALL operations
- Hard to add new features (modify constructor every time)

---

## ✅ Industry Best Practices (from research)

### Pattern 1: Split by Domain Aggregate (RECOMMENDED)
```
services/planning/
├── infrastructure/
│   ├── grpc/
│   │   ├── handlers/
│   │   │   ├── project_handlers.py      # CreateProject, GetProject, ListProjects
│   │   │   ├── epic_handlers.py         # CreateEpic, GetEpic, ListEpics
│   │   │   ├── story_handlers.py        # CreateStory, TransitionStory, GetStory, ListStories
│   │   │   ├── task_handlers.py         # CreateTask, GetTask, ListTasks
│   │   │   └── decision_handlers.py     # ApproveDecision, RejectDecision
│   │   ├── mappers/
│   │   │   └── response_mapper.py       # Common response mapping
│   │   ├── middleware/
│   │   │   ├── error_interceptor.py     # Centralized error handling
│   │   │   └── logging_interceptor.py   # Centralized logging
│   │   └── servicer.py                  # Main servicer (delegates to handlers)
│   └── ...
├── server.py                             # Main entry point (~100 lines)
```

**Benefits**:
- Each handler file: ~60-100 lines ✅
- Easy to test (one handler file at a time)
- Easy to add new features (add new handler file)
- Clear separation of concerns

### Pattern 2: Handler Classes (Used by Workflow Service)
```python
# services/workflow/infrastructure/grpc_servicer.py (373 lines)
class WorkflowOrchestrationServicer:
    def __init__(self, get_workflow_state, execute_action, get_pending_tasks, ...):
        self._get_workflow_state = get_workflow_state
        self._execute_action = execute_action
        # ...

    async def GetWorkflowState(self, request, context):
        # Delegates to use case
        # Uses GrpcWorkflowMapper for conversions
```

**Why Workflow is Cleaner**:
1. Uses separate mappers (`GrpcWorkflowMapper`)
2. Error constants defined (`_INTERNAL_SERVER_ERROR`)
3. Focused on 4 RPCs (not 12)

### Pattern 3: Error Interceptors (Industry Standard)
```python
# services/planning/infrastructure/grpc/middleware/error_interceptor.py
class ErrorInterceptor(grpc.aio.ServerInterceptor):
    """Centralized error handling for all gRPC methods."""

    async def intercept_service(self, continuation, handler_call_details):
        try:
            return await continuation(handler_call_details)
        except ValueError as e:
            # Validation errors → INVALID_ARGUMENT
            handler_call_details.context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return ErrorResponse(message=str(e))
        except NotFoundError as e:
            # Not found → NOT_FOUND
            handler_call_details.context.set_code(grpc.StatusCode.NOT_FOUND)
            return ErrorResponse(message=str(e))
        except Exception as e:
            # Everything else → INTERNAL
            logger.error(f"Unexpected error", exc_info=True)
            handler_call_details.context.set_code(grpc.StatusCode.INTERNAL)
            return ErrorResponse(message="Internal server error")
```

**Benefits**:
- Remove 20 lines from EACH handler
- Consistent error handling across ALL RPCs
- Single place to add monitoring/tracing

---

## 🎯 Proposed Refactor (Phase 1: Minimal Changes)

### Step 1: Extract Handler Classes (~2 hours)

```python
# services/planning/infrastructure/grpc/handlers/project_handlers.py
from dataclasses import dataclass

@dataclass
class ProjectHandlers:
    """Handlers for Project-related RPCs."""

    create_project_uc: CreateProjectUseCase

    async def create_project(self, request, context):
        """Create a new project."""
        project = await self.create_project_uc.execute(
            name=request.name,
            description=request.description,
            owner=request.owner,
        )

        return planning_pb2.CreateProjectResponse(
            success=True,
            message=f"Project created: {project.project_id.value}",
            project=self._to_protobuf(project),
        )

    def _to_protobuf(self, project):
        """Convert Project to protobuf."""
        return planning_pb2.Project(
            project_id=project.project_id.value,
            name=project.name,
            # ...
        )
```

```python
# services/planning/server.py (AFTER refactor: ~150 lines)
from planning.infrastructure.grpc.handlers import (
    ProjectHandlers,
    EpicHandlers,
    StoryHandlers,
    TaskHandlers,
    DecisionHandlers,
)

class PlanningServiceServicer(planning_pb2_grpc.PlanningServiceServicer):
    """Main gRPC servicer - delegates to specialized handlers."""

    def __init__(self, handlers: dict):
        self.project = handlers['project']
        self.epic = handlers['epic']
        self.story = handlers['story']
        self.task = handlers['task']
        self.decision = handlers['decision']

    async def CreateProject(self, request, context):
        return await self.project.create_project(request, context)

    async def CreateEpic(self, request, context):
        return await self.epic.create_epic(request, context)

    # ... (12 delegations, ~5 lines each = 60 lines total)
```

**Result**:
- server.py: 784 → 150 lines ✅
- 5 handler files × ~100 lines = 500 lines
- Total: 650 lines (vs 784), but MUCH more maintainable

---

## 🎯 Proposed Refactor (Phase 2: Error Interceptor)

### Step 2: Add Error Interceptor (~1 hour)

```python
# services/planning/infrastructure/grpc/middleware/error_interceptor.py
class ErrorInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(self, continuation, handler_call_details):
        try:
            return await continuation(handler_call_details)
        except ValueError as e:
            return self._validation_error(handler_call_details.context, e)
        except NotFoundError as e:
            return self._not_found_error(handler_call_details.context, e)
        except Exception as e:
            return self._internal_error(handler_call_details.context, e)
```

```python
# services/planning/server.py - with interceptor
server = grpc.aio.server(
    futures.ThreadPoolExecutor(max_workers=10),
    interceptors=[ErrorInterceptor()],  # ← Centralized error handling
)
```

**Result**:
- Remove try/except from ALL handlers
- Each handler: 30 lines → 10 lines
- 12 handlers × 20 lines saved = 240 lines saved ✅

---

## 🎯 Proposed Refactor (Phase 3: Response Builders)

### Step 3: Unified Response Builders (~1 hour)

```python
# services/planning/infrastructure/grpc/mappers/response_builder.py
class ResponseBuilder:
    """Builds protobuf responses from domain entities."""

    @staticmethod
    def project_response(project: Project) -> planning_pb2.Project:
        return planning_pb2.Project(
            project_id=project.project_id.value,
            name=project.name,
            description=project.description,
            status=project.status.value,
            owner=project.owner,
            created_at=project.created_at.isoformat() + "Z",
            updated_at=project.updated_at.isoformat() + "Z",
        )

    @staticmethod
    def success(message: str, **kwargs) -> dict:
        return {"success": True, "message": message, **kwargs}
```

**Result**:
- DRY: Don't repeat isoformat + "Z" 30 times
- Testable: Test mappers independently
- Type-safe: Centralized conversion logic

---

## 📊 Final Structure (After All Phases)

```
services/planning/
├── infrastructure/
│   ├── grpc/
│   │   ├── __init__.py
│   │   ├── servicer.py                     (~150 lines) - Main servicer
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── project_handlers.py         (~80 lines)
│   │   │   ├── epic_handlers.py            (~80 lines)
│   │   │   ├── story_handlers.py           (~100 lines)
│   │   │   ├── task_handlers.py            (~90 lines)
│   │   │   └── decision_handlers.py        (~60 lines)
│   │   ├── mappers/
│   │   │   ├── __init__.py
│   │   │   └── response_builder.py         (~150 lines)
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── error_interceptor.py        (~80 lines)
│   │       └── logging_interceptor.py      (~60 lines)
│   └── ...
└── server.py                                (~100 lines) - Entry point only
```

**Total Lines**: ~950 lines (vs 784 monolithic)
**Complexity**: MUCH LOWER (each file ~100 lines)
**Testability**: MUCH HIGHER (test handler classes independently)
**Maintainability**: EXCELLENT (clear separation of concerns)

---

## 🎓 Lessons from Industry

### Google's gRPC Practices
1. **One Service Per File**: Break large servicers into modules
2. **Interceptors for Cross-Cutting Concerns**: Logging, auth, errors
3. **Separate Mappers**: Don't mix protobuf logic with business logic

### Hexagonal Architecture in gRPC
From research + this codebase:
1. **Servicer = Infrastructure Adapter**: Thin translation layer
2. **Handlers = Infrastructure Logic**: Request/response conversion
3. **Use Cases = Application Logic**: Orchestration
4. **Mappers = Infrastructure Utilities**: Protobuf ↔ Domain

### Real-World Examples
- **Uber**: Splits servicers by domain aggregate (similar to our proposal)
- **Netflix**: Uses interceptors for all cross-cutting concerns
- **Spotify**: Handler classes with dependency injection

---

## 📋 Refactor Implementation Plan

### Phase 1: Extract Handlers (NO breaking changes)
**Effort**: 4-6 hours
**Risk**: LOW (tests verify behavior)
**Steps**:
1. Create `infrastructure/grpc/handlers/` directory
2. Extract ProjectHandlers class
3. Extract EpicHandlers class
4. Extract StoryHandlers class
5. Extract TaskHandlers class
6. Extract DecisionHandlers class
7. Update servicer to delegate
8. Run tests → Should all pass

### Phase 2: Add Error Interceptor (NO breaking changes)
**Effort**: 2 hours
**Risk**: LOW (interceptor wraps existing logic)
**Steps**:
1. Create `infrastructure/grpc/middleware/error_interceptor.py`
2. Add interceptor to server initialization
3. Remove try/except from handlers
4. Run tests → Should all pass

### Phase 3: Unified Response Builder (NO breaking changes)
**Effort**: 2 hours
**Risk**: LOW (pure refactor)
**Steps**:
1. Create `infrastructure/grpc/mappers/response_builder.py`
2. Migrate protobuf conversions from handlers
3. Update handlers to use builder
4. Run tests → Should all pass

**Total Effort**: 8-10 hours
**Total Lines Saved**: ~240 lines of boilerplate
**Complexity Reduction**: ~60%

---

## 🚫 What NOT to Do

### ❌ Anti-Pattern 1: Business Logic in Handlers
```python
# BAD:
async def CreateProject(self, request, context):
    if not request.name:
        return Error("name required")

    project_id = generate_id()  # ← Business logic in handler
    project = Project(...)
    storage.save(project)  # ← Direct storage access
```

**Why Bad**: Violates Hexagonal Architecture, bypasses use cases

### ❌ Anti-Pattern 2: God Interceptor
```python
# BAD:
class MegaInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(self, ...):
        # 500 lines of logic
        # Auth, logging, validation, caching, etc.
```

**Why Bad**: Just moves the God Class problem elsewhere

### ❌ Anti-Pattern 3: Over-Abstraction
```python
# BAD:
class GenericHandler[T]:
    async def handle(self, request: Any) -> Any:
        # Reflection-based generic handler
```

**Why Bad**: Violates Rule #4 (NO reflection), loses type safety

---

## 💡 Recommended: Phased Approach

### Immediate (This Session):
✅ DONE: Implement 9 handlers inline (functional, not perfect)
✅ Tests passing
✅ Deploy to cluster
✅ Verify functionality

### Next Sprint (After Deploy):
1. Phase 1: Extract handlers (4-6 hours)
2. Phase 2: Error interceptor (2 hours)
3. Tests still passing
4. Deploy again

### Future (If Time):
3. Phase 3: Response builder (2 hours)
4. Apply same pattern to Context Service (1,036 lines → needs it more)

---

## 📈 Expected Benefits

### Code Quality
- **Before**: 784-line God Class, hard to test
- **After**: 6 files × ~100 lines, easy to test

### Test Strategy
```python
# Before (testing servicer):
servicer = PlanningServiceServicer(uc1, uc2, uc3, uc4, uc5, uc6, uc7, uc8)  # 😱
await servicer.CreateProject(...)

# After (testing handler):
handler = ProjectHandlers(create_project_uc=mock_uc)  # ✅ Clean
await handler.create_project(...)
```

### Adding New Features
```python
# Before: Modify servicer __init__ (breaks all tests)
def __init__(self, uc1, uc2, ..., uc9):  # ← Broke 50 tests

# After: Add new handler file (no impact on existing)
# Create new file: infrastructure/grpc/handlers/report_handlers.py
# Add to servicer delegation: self.report = handlers['report']
```

---

## 🎯 Decision Matrix

| Approach | Effort | Risk | Benefits | Recommendation |
|----------|--------|------|----------|----------------|
| **Keep As-Is** | 0h | Low | None | ❌ Technical debt grows |
| **Extract Handlers** | 4-6h | Low | High | ✅ Do next sprint |
| **Full Refactor** | 10h+ | Medium | Very High | ⚠️ Do later |
| **Rewrite from Scratch** | 20h+ | High | Unknown | ❌ Not worth it |

---

## ✅ Recommendation

**Short-term** (This week):
- ✅ Keep current implementation (784 lines)
- ✅ Deploy and verify functionality
- ✅ Document as technical debt

**Medium-term** (Next sprint):
- 🔄 Refactor Phase 1 (extract handlers)
- 🔄 Refactor Phase 2 (error interceptor)
- ✅ Tests still passing
- ✅ Deploy again

**Long-term** (Q1 2026):
- Apply pattern to Context Service (1,036 lines → biggest problem)
- Apply pattern to Orchestrator (898 lines)
- Standardize across all services

---

## 📚 References

### Industry Patterns:
- [gRPC Best Practices](https://grpc.io/docs/guides/performance/)
- Clean Architecture in Microservices (Martin Fowler)
- Hexagonal Architecture (Alistair Cockburn)

### Similar Patterns in This Codebase:
- `services/workflow/infrastructure/grpc_servicer.py` (373 lines) ✅ Good example
- `services/ray_executor/server.py` (379 lines) ✅ Good example

### Anti-Patterns to Avoid:
- `services/context/server.py` (1,036 lines) 🔥 Needs refactor urgently
- `services/orchestrator/server.py` (898 lines) ⚠️ Needs refactor

---

## 🔄 BONUS: Event Consumers Refactor

### Current Problem: Monolithic Consumers

**Context Service** `planning_consumer.py`:
```python
class PlanningEventsConsumer:
    async def start(self):
        # 4 different subscriptions in ONE class
        self._story_sub = await self.js.pull_subscribe("planning.story.transitioned", ...)
        self._plan_sub = await self.js.pull_subscribe("planning.plan.approved", ...)
        self._project_sub = await self.js.pull_subscribe("planning.project.created", ...)  # NEW
        self._epic_sub = await self.js.pull_subscribe("planning.epic.created", ...)  # NEW

        # 4 polling methods
        asyncio.create_task(self._poll_story_transitions())
        asyncio.create_task(self._poll_plan_approvals())
        asyncio.create_task(self._poll_project_created())
        asyncio.create_task(self._poll_epic_created())

    async def _poll_story_transitions(self): ...  # 30 lines
    async def _poll_plan_approvals(self): ...      # 30 lines
    async def _poll_project_created(self): ...     # 30 lines
    async def _poll_epic_created(self): ...        # 30 lines
```

**Result**: 200+ lines, 4 responsibilities → Violates SRP

---

### Proposed: Event Handler Pattern

```
services/context/
├── consumers/
│   ├── __init__.py
│   ├── base_event_consumer.py           # Base class with common logic
│   └── planning/
│       ├── __init__.py
│       ├── project_created_consumer.py  # Handles planning.project.created
│       ├── epic_created_consumer.py     # Handles planning.epic.created
│       ├── story_created_consumer.py    # Handles planning.story.created
│       ├── task_created_consumer.py     # Handles planning.task.created
│       └── story_transitioned_consumer.py  # Handles planning.story.transitioned
```

**Each consumer (~50 lines)**:
```python
# services/context/consumers/planning/project_created_consumer.py
@dataclass
class ProjectCreatedConsumer:
    """Consumes planning.project.created events.

    Responsibility: Create Project nodes in Neo4j graph.
    """

    js: JetStreamContext
    graph_command: GraphCommandPort

    async def start(self):
        """Start consuming planning.project.created events."""
        self._sub = await self.js.pull_subscribe(
            subject="planning.project.created",
            durable="context-project-created-v1",
            stream="PLANNING_EVENTS",
        )

        asyncio.create_task(self._poll_messages())

    async def _poll_messages(self):
        """Poll and process messages."""
        while True:
            try:
                messages = await self._sub.fetch(batch=10, timeout=1.0)
                for msg in messages:
                    await self._handle_message(msg)
                    await msg.ack()
            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error polling: {e}", exc_info=True)

    async def _handle_message(self, msg):
        """Handle single project.created message."""
        payload = json.loads(msg.data.decode())

        # Create Project node in Neo4j
        await self.graph_command.save_project(
            project_id=payload["project_id"],
            name=payload["name"],
            # ...
        )

        logger.info(f"Project node created: {payload['project_id']}")
```

**Benefits**:
1. ✅ Single Responsibility: Each consumer handles ONE event type
2. ✅ Easy to test: Mock one dependency, test one consumer
3. ✅ Easy to add: New event → New consumer file (no modifications to existing)
4. ✅ Easy to disable: Comment out one consumer registration
5. ✅ Parallel Processing: Each consumer runs independently

---

### Coordinated Refactor Plan

#### Phase A: gRPC Handlers (Planning Service)
**Effort**: 8-10 hours
**Files**: Split `server.py` (784 lines) → 6 files
**Pattern**: Handler classes by domain aggregate

#### Phase B: Event Consumers (Context Service)
**Effort**: 6-8 hours
**Files**: Split `planning_consumer.py` → 5 consumer files
**Pattern**: One consumer per event type

#### Phase C: Apply to Other Services
**Effort**: 12-16 hours
**Services**:
- Context Service: `server.py` (1,036 lines) 🔥 URGENT
- Orchestrator: `server.py` (898 lines) ⚠️
- Orchestrator: `planning_consumer.py` (similar split needed)

**Total Effort**: 26-34 hours (~1 sprint)
**Total Complexity Reduction**: ~70%

---

### Consumer Registration Pattern

```python
# services/context/server.py (after refactor)
async def start_consumers(js, graph_command):
    """Start all event consumers."""

    consumers = [
        ProjectCreatedConsumer(js=js, graph_command=graph_command),
        EpicCreatedConsumer(js=js, graph_command=graph_command),
        StoryCreatedConsumer(js=js, graph_command=graph_command),
        TaskCreatedConsumer(js=js, graph_command=graph_command),
        StoryTransitionedConsumer(js=js, graph_command=graph_command),
    ]

    for consumer in consumers:
        await consumer.start()
        logger.info(f"✓ {consumer.__class__.__name__} started")
```

**Advantages**:
- Declarative: List of consumers clearly visible
- Easy to disable: Comment out one line
- Easy to test: Test each consumer independently
- Easy to monitor: Log each consumer's health

---

### Testing Pattern for Consumers

```python
# tests/unit/context/consumers/planning/test_project_created_consumer.py
@pytest.mark.asyncio
async def test_project_created_consumer_creates_node():
    """Test that consumer creates Project node in Neo4j."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ProjectCreatedConsumer(js=mock_js, graph_command=mock_graph)

    message = Mock()
    message.data = json.dumps({
        "project_id": "PROJ-123",
        "name": "Test Project",
    }).encode()

    # Act
    await consumer._handle_message(message)

    # Assert
    mock_graph.save_project.assert_awaited_once()
    call_args = mock_graph.save_project.call_args
    assert call_args[1]["project_id"] == "PROJ-123"
```

**Benefits**:
- Test ONE consumer at a time
- No need to mock 4+ dependencies
- Fast test execution
- Clear failure messages

---

**Priority**: MEDIUM (not blocking merge)
**Effort**: 14-18 hours total (handlers + consumers)
**Impact**: Very High (maintainability, testability, extensibility)
**Recommended Timeline**: Next sprint (after deploy verification)

