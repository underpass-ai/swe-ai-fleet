# NEXT STEPS - Project Hierarchy Implementation
**Date**: 2025-11-09  
**Branch**: `feature/project-entity-mandatory-hierarchy`  
**Session**: Complete Hierarchy Project → Epic → Story → Plan → Task

---

## ✅ COMPLETED THIS SESSION

### 1. Domain Layer (Core/Context) ✅
- [x] Created `Project` entity with `ProjectId` and `ProjectStatus`
- [x] Updated `Epic` entity to require `project_id` (mandatory parent)
- [x] Updated `Story` entity to require `epic_id` (mandatory parent)
- [x] Added hierarchy to ALL domain events for traceability:
  - `DecisionMadeEvent`: project_id + epic_id + story_id + task_id
  - `StoryCreatedEvent`: project_id + epic_id
  - `TaskCreatedEvent`: project_id + epic_id + story_id + plan_id
  - `TaskStatusChangedEvent`: project_id + epic_id + story_id + plan_id
  - `PlanVersionedEvent`: project_id + epic_id + story_id
- [x] **Eliminated ALL reflection** (`object.__setattr__`) from events ✅
- [x] Fixed dataclass field ordering (required fields first, defaults last)

### 2. Planning Service (Application Layer) ✅
- [x] Created `Project`, `Epic`, `Task` entities in Planning Service
- [x] Created `ProjectCreatedEvent`, `EpicCreatedEvent`, `TaskCreatedEvent`
- [x] Implemented `CreateProjectUseCase`, `CreateEpicUseCase`, `CreateTaskUseCase`
- [x] Updated `CreateStoryUseCase` to validate parent epic exists
- [x] Extended `StoragePort` with Project/Epic/Task methods
- [x] Created event mappers: `ProjectEventMapper`, `EpicEventMapper`, `TaskEventMapper`
- [x] **Added structured logging** with hierarchy traceability in all mappers

### 3. API Layer ✅
- [x] Extended `planning.proto` v2 with:
  - Project RPCs: `CreateProject`, `GetProject`, `ListProjects`
  - Epic RPCs: `CreateEpic`, `GetEpic`, `ListEpics`
  - Task RPCs: `CreateTask`, `GetTask`, `ListTasks`
  - Updated `CreateStoryRequest` to require `epic_id`

### 4. Infrastructure Layer ✅
- [x] Created Neo4j constraints file (`neo4j_constraints.cypher`)
- [x] Updated `GraphCommandPort` and `Neo4jCommandStore`
- [x] Created `ProjectMapper`, updated `EpicMapper`, `StoryMapper`

### 5. Quality Assurance ✅
- [x] Created unit tests for domain invariants
- [x] 589 tests passing ✅
- [x] **Complete EVENT AUDIT** (docs/audits/EVENT_AUDIT_2025-11-09.md)
- [x] Identified 4 orphan events, 2 ghost consumers

### 6. Commits ✅
- [x] 5 commits on branch:
  1. Domain entities + mandatory hierarchy
  2. Persistence layer for Project
  3. API v2 extensions (proto)
  4. Complete hierarchy in Planning Service
  5. Domain events with hierarchy (removed reflection)

---

## 🎯 IMMEDIATE NEXT STEPS (Priority Order)

### PHASE 1: Complete Planning Service Implementation (HIGH PRIORITY)

#### Task 1.1: Implement gRPC Handlers 🔴
**Status**: BLOCKED - Need these for API to work  
**File**: `services/planning/server.py`  
**Estimate**: 2-3 hours

**Actions**:
```python
# Implement in PlanningServicer:
async def CreateProject(self, request, context):
    # Call CreateProjectUseCase
    # Return ProjectResponse

async def GetProject(self, request, context):
    # Call storage.get_project()
    
async def ListProjects(self, request, context):
    # Call storage.list_projects()

# Same for Epic and Task
```

**Dependencies**: None  
**Blocks**: E2E testing, client integration

---

#### Task 1.2: Unit Tests for New Use Cases 🟡
**Status**: PENDING  
**Files**: 
- `tests/unit/services/planning/usecases/test_create_project_usecase.py`
- `tests/unit/services/planning/usecases/test_create_epic_usecase.py`
- `tests/unit/services/planning/usecases/test_create_task_usecase.py`

**Estimate**: 2 hours

**Actions**:
- Test happy path (valid parent exists)
- Test failure (parent not found → ValueError)
- Test event publication
- Mock storage and messaging ports

---

#### Task 1.3: Integration Tests for Hierarchy Validation 🟡
**Status**: PENDING  
**File**: `tests/integration/planning/test_hierarchy_validation.py`

**Estimate**: 1 hour

**Actions**:
- Test creating Epic without Project → Should fail
- Test creating Story without Epic → Should fail
- Test creating Task without Plan → Should fail
- Verify cascade: Project → Epic → Story → Plan → Task

---

### PHASE 2: Event Consumers (HIGH PRIORITY)

#### Task 2.1: Context Service - Consume Hierarchy Events 🔴
**Status**: CRITICAL for graph completeness  
**File**: `services/context/consumers/planning_consumer.py`

**Estimate**: 4-6 hours

**Actions**:
```python
# Add to PlanningEventsConsumer:
async def start(self):
    # Existing subscriptions...
    
    # NEW: Subscribe to hierarchy events
    self._project_sub = await self.js.pull_subscribe(
        subject="planning.project.created",
        durable="context-planning-project-created",
        stream="PLANNING_EVENTS",
    )
    
    self._epic_sub = await self.js.pull_subscribe(
        subject="planning.epic.created",
        durable="context-planning-epic-created",
        stream="PLANNING_EVENTS",
    )
    
    # ... task and story
```

**Implementation**:
1. Add polling methods for each event type
2. Deserialize events using mappers
3. Create Neo4j nodes: `Project`, `Epic`, `Task`, `Story`
4. Create relationships: `HAS_EPIC`, `CONTAINS`, `HAS_TASK`
5. Add Valkey cache entries

**Benefits**:
- Complete graph representation
- Hierarchy queries work end-to-end
- Analytics on Project/Epic level

---

#### Task 2.2: Remove Ghost Consumers 🟢
**Status**: CLEANUP - Low risk  
**Files**:
- `services/context/consumers/planning_consumer.py` (remove `planning.plan.approved`)
- `services/orchestrator/infrastructure/handlers/planning_consumer.py` (remove `planning.plan.approved`)
- `services/orchestrator/infrastructure/handlers/agent_response_consumer.py` (remove `agent.response.progress`)

**Estimate**: 30 minutes

**Justification**:
- `planning.plan.approved` → Nobody publishes this event
- `agent.response.progress` → VLLMAgent doesn't report progress

**Actions**:
1. Remove subscriptions
2. Remove polling methods
3. Update tests
4. Add comment explaining removal

---

#### Task 2.3: Orchestrator - Decision Approval/Rejection 🟡
**Status**: PENDING - Completes human-in-the-loop flow  
**File**: `services/orchestrator/infrastructure/handlers/planning_consumer.py`

**Estimate**: 3-4 hours

**Actions**:
```python
# Add to OrchestratorPlanningConsumer:
self._decision_approved_sub = await self.messaging.pull_subscribe(
    subject="planning.decision.approved",
    durable="orch-planning-decision-approved",
    stream="PLANNING_EVENTS",
)

async def _poll_decision_approved(self):
    while True:
        messages = await self._decision_approved_sub.fetch(batch=10)
        for msg in messages:
            payload = json.loads(msg.data)
            # Trigger execution flow
            await self._trigger_execution(
                story_id=payload["story_id"],
                decision_id=payload["decision_id"],
            )
            await msg.ack()
```

**Benefits**:
- Completes PO approval → execution flow
- Rejection → re-deliberation flow
- Full human-in-the-loop implementation

---

### PHASE 3: Database & Constraints (MEDIUM PRIORITY)

#### Task 3.1: Apply Neo4j Constraints 🟡
**Status**: PENDING  
**File**: `core/context/infrastructure/neo4j_constraints.cypher`

**Estimate**: 30 minutes + testing

**Actions**:
```bash
# Connect to Neo4j pod
kubectl exec -it neo4j-0 -n swe-ai-fleet -- cypher-shell

# Run constraints file
:source /path/to/neo4j_constraints.cypher

# Verify
SHOW CONSTRAINTS;
```

**Constraints to Apply**:
1. `task_must_have_story` → Task MUST have Story relationship
2. `story_must_have_epic` → Story MUST have Epic relationship
3. `epic_must_have_project` → Epic MUST have Project relationship

**Testing**:
```cypher
// Should FAIL:
CREATE (e:Epic {epic_id: "orphan"})

// Should SUCCEED:
CREATE (p:Project {project_id: "P1"})
CREATE (e:Epic {epic_id: "E1"})
CREATE (p)-[:HAS_EPIC]->(e)
```

---

### PHASE 4: Documentation (LOW PRIORITY)

#### Task 4.1: Update Domain Invariants Doc 🟢
**Status**: PENDING  
**File**: `docs/architecture/DOMAIN_INVARIANTS_BUSINESS_RULES.md`

**Actions**:
- Document mandatory hierarchy rule
- Add examples of valid/invalid hierarchies
- Reference Neo4j constraints
- Add decision tree for validation flow

---

#### Task 4.2: Create Architecture Decision Record 🟢
**Status**: PENDING  
**File**: `docs/architecture/decisions/2025-11-09/ADR_PROJECT_HIERARCHY.md`

**Content**:
- Decision: Mandatory Project → Epic → Story → Task hierarchy
- Context: Traceability, RBAC, analytics requirements
- Consequences: Domain invariants, breaking changes
- Alternatives considered: Optional hierarchy (rejected)

---

## 📊 PROGRESS METRICS

### Code Quality
- [x] 0 uses of reflection (`object.__setattr__`) ✅
- [x] All domain events immutable (`frozen=True`) ✅
- [x] Fail-fast validation in all entities ✅
- [x] 100% type hints coverage ✅
- [ ] gRPC handlers implemented (0/9)
- [ ] Event consumers implemented (0/4)

### Test Coverage
- [x] Core/Context unit tests: 311 passing ✅
- [x] Planning Service tests: Need update for `epic_id`
- [ ] Integration tests: 0/3 implemented
- [ ] E2E tests: 0/1 implemented

### Event System Health
- ✅ 7 events with active consumers
- ❌ 4 orphan events (new hierarchy - expected)
- ⚠️ 2 ghost consumers (need cleanup)
- ⚠️ 2 legacy events (decision approved/rejected - need consumers)

---

## 🚀 DEPLOYMENT CHECKLIST (Before Merge to Main)

### Pre-Merge Requirements
- [ ] All unit tests passing (Planning Service)
- [ ] Integration tests passing (hierarchy validation)
- [ ] gRPC handlers implemented and tested
- [ ] Event consumers implemented (Context Service)
- [ ] Neo4j constraints applied and tested
- [ ] Documentation updated
- [ ] Code review completed
- [ ] Linter passing (no E402, E501 errors)

### Deployment Steps
1. **Database Migration** (Neo4j constraints)
   ```bash
   kubectl exec -it neo4j-0 -- cypher-shell < neo4j_constraints.cypher
   ```

2. **Deploy Services** (rolling update)
   - Context Service first (consumers ready)
   - Planning Service second (publishers active)
   - Workflow/Orchestrator last (no changes)

3. **Verify Event Flow**
   ```bash
   # Monitor events
   kubectl exec -it nats-0 -- nats stream view PLANNING_EVENTS
   
   # Test hierarchy creation
   grpcurl -d '{"name":"Test Project"}' planning:50053 \
     fleet.planning.v2.PlanningService/CreateProject
   ```

4. **Smoke Tests**
   - Create Project → Verify in Neo4j
   - Create Epic under Project → Verify relationship
   - Create Story under Epic → Verify constraint enforced
   - Attempt orphan Epic → Should fail

---

## ⚠️ KNOWN ISSUES & RISKS

### High Risk
1. **Breaking Change**: `CreateStoryRequest` now requires `epic_id`
   - **Impact**: Existing clients will fail
   - **Mitigation**: Update all clients before deployment
   - **Rollback**: Revert to previous planning.proto version

2. **Data Migration**: Existing Stories/Epics in Neo4j lack parent IDs
   - **Impact**: Queries will fail for old data
   - **Mitigation**: Run migration script to assign default Project/Epic
   - **Script**: TODO - Create `migrate_existing_hierarchy.cypher`

### Medium Risk
3. **Event Replay**: Old events don't have hierarchy fields
   - **Impact**: Event consumers will crash on old messages
   - **Mitigation**: Add backward compatibility in mappers (default values)

4. **Performance**: Additional Neo4j constraint checks on writes
   - **Impact**: Slight write latency increase (~5-10ms)
   - **Mitigation**: Monitor metrics, acceptable trade-off for data integrity

### Low Risk
5. **Orphan Events**: New events published but not consumed yet
   - **Impact**: Events accumulate in NATS stream
   - **Mitigation**: Implement consumers in Phase 2
   - **Workaround**: Events have retention, will be processed when consumers ready

---

## 🎯 RECOMMENDED EXECUTION ORDER

### Week 1: Core Implementation
**Day 1-2**: Phase 1 (Tasks 1.1, 1.2, 1.3)  
**Day 3-4**: Phase 2 (Task 2.1 - Context Service consumers)  
**Day 5**: Phase 3 (Task 3.1 - Neo4j constraints)

### Week 2: Cleanup & Integration
**Day 1**: Phase 2 (Tasks 2.2, 2.3 - Ghost cleanup, Orchestrator)  
**Day 2-3**: Integration testing, E2E testing  
**Day 4**: Documentation (Phase 4)  
**Day 5**: Code review, deployment preparation

### Week 3: Deployment
**Day 1**: Deploy to staging  
**Day 2-3**: Staging validation  
**Day 4**: Deploy to production (rolling)  
**Day 5**: Monitor, fix issues

**Total Estimated Effort**: 10-12 days (with buffer)

---

## 🤝 COLLABORATION POINTS

### Need Input From:
- **Product Owner**: Approval for breaking changes in API
- **DevOps**: Neo4j constraint application strategy
- **Frontend Team**: Update clients for new `epic_id` requirement
- **QA**: E2E test scenarios for hierarchy validation

### Code Review Focus:
1. Domain invariants enforcement (fail-fast)
2. Event consumer error handling
3. Neo4j constraint correctness
4. Backward compatibility in mappers

---

**Next Session**: Start with Task 1.1 (gRPC handlers implementation)  
**Branch Status**: Ready for continued development  
**Merge Readiness**: 40% (core done, handlers and consumers pending)

