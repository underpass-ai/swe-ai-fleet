# Decision Impact Model - Architectural Flaws Analysis

**Date**: November 8, 2025
**Author**: Tirso García Ibáñez (Software Architect)
**Status**: CRITICAL - Requires immediate refactoring
**Scope**: Context Service - Decision Impact Tracking

---

## Executive Summary

During the RBAC L3 refactoring and DDD alignment, we identified **critical architectural flaws** in the Decision Impact model. These flaws violate:
- Domain-Driven Design principles
- Single Responsibility Principle
- Open-Closed Principle
- Type safety guarantees
- Naming consistency

**Impact**: HIGH - Affects core context assembly, testability, and future extensibility.

---

## 🚨 Problem 1: Inconsistent Naming (Subtask vs Task)

### Current State (WRONG)
```python
# core/reports/domain/subtask_node.py
@dataclass(frozen=True)
class SubtaskNode:  # ❌ Using obsolete "Subtask" terminology
    id: str
    title: str
    role: str
```

### Context
- The codebase has standardized on `Task` terminology (aligned with Planning/Workflow services)
- `Case` → `Story` (completed)
- `Subtask` → `Task` (in progress, but incomplete)
- However, `SubtaskNode` in `core/reports/domain/` was **NOT renamed**

### Impact
- **Confusion**: Developers see both `Task` and `Subtask` terminology
- **Inconsistency**: Domain language fragmentation
- **Maintenance burden**: Two terms for the same concept
- **Onboarding difficulty**: New developers confused by dual terminology

### Evidence
```python
# core/context/domain/services/decision_selector.py
impacts_by_decision: dict[str, list[SubtaskNode]]  # ❌ Obsolete name

# core/context/domain/services/impact_calculator.py
impacts_by_decision: dict[str, list[SubtaskNode]]  # ❌ Obsolete name

# core/context/session_rehydration.py
from core.reports.domain.subtask_node import SubtaskNode  # ❌ Obsolete import
```

### Required Action
1. Rename `core/reports/domain/subtask_node.py` → `task_node.py`
2. Rename class `SubtaskNode` → `TaskNode`
3. Update all imports across the codebase
4. Update method signatures in domain services
5. Update tests

---

## 🚨 Problem 2: Limited Impact Model (Only Tasks)

### Current Design (TOO NARROW)
```python
# Decisions can ONLY impact Tasks
impacts_by_decision: dict[str, list[SubtaskNode]]
```

### What's Wrong?
The current model assumes **decisions only impact tasks**. This is architecturally incorrect.

### Real-World Decision Impacts

#### Example 1: Architectural Decision
**Decision**: "Use Neo4j instead of PostgreSQL for context storage"

**Impacts**:
- ✅ Tasks: Multiple implementation tasks affected
- ✅ Stories: All database-related stories need revision
- ✅ Epic: "Data Persistence" epic timeline changes
- ✅ Components: Database adapter must be rewritten
- ✅ Tests: All persistence tests need updates
- ✅ Infrastructure: Deployment manifests change

**Current Model**: ❌ Can only track Task impacts, loses all other relationships

#### Example 2: API Contract Decision
**Decision**: "Change from REST to gRPC for inter-service communication"

**Impacts**:
- ✅ Stories: All integration stories affected
- ✅ Tasks: Client/server implementation tasks
- ✅ Epic: "Service Integration" epic
- ✅ Dependencies: All services that call this API
- ✅ Documentation: API specs need updates

**Current Model**: ❌ Only tracks task-level impacts

#### Example 3: Security Decision
**Decision**: "Implement RBAC L3 with data-level access control"

**Impacts**:
- ✅ Epic: New "Security" epic created
- ✅ Stories: Multiple new stories added
- ✅ Tasks: Implementation tasks
- ✅ Existing Stories: All context-reading stories affected
- ✅ Performance: Query patterns change

**Current Model**: ❌ Cannot model multi-level impacts

### Design Limitation Analysis

```python
# CURRENT (LIMITED):
class DecisionNode:
    id: str
    # ... other fields

# Impacts stored as:
impacts: list[tuple[str, SubtaskNode]]  # (decision_id, impacted_task)
#                     ^^^^^^^^^^ ONLY Tasks!
```

**Limitations**:
1. ❌ Cannot track impacts to Stories
2. ❌ Cannot track impacts to Epics
3. ❌ Cannot track impacts to other Decisions (decision dependencies exist separately)
4. ❌ Cannot track impacts to Architecture components
5. ❌ Cannot track impacts to Infrastructure
6. ❌ Cannot model cascading impacts (Decision → Story → Tasks)

---

## 🚨 Problem 3: Type Safety Violations

### Current Code
```python
# core/context/domain/services/decision_selector.py (BEFORE FIX)
def select_for_role(
    self,
    role_tasks: list[TaskPlan],
    impacts_by_decision: dict[str, list],        # ❌ list of what?
    decisions_by_id: dict[str, Any],             # ❌ Any is NOT type-safe
    all_decisions: list,                         # ❌ list of what?
) -> list:  # ❌ Returns what?
```

### Problems
- `dict[str, list]` - IDE cannot infer what's in the list
- `dict[str, Any]` - Any defeats the purpose of type hints
- `list` without type parameter - What does the list contain?
- Return type `list` - What are we returning?

### After DDD Fix
```python
def select_for_role(
    self,
    role_tasks: list[TaskPlan],
    impacts_by_decision: dict[str, list[TaskNode]],  # ✅ Explicit
    decisions_by_id: dict[str, DecisionNode],        # ✅ Type-safe
    all_decisions: list[DecisionNode],               # ✅ Clear
) -> list[DecisionNode]:  # ✅ Explicit return type
```

---

## 🚨 Problem 4: Cross-Bounded-Context Coupling

### Issue
`SubtaskNode` (and soon `TaskNode`) lives in `core/reports/domain/` but is heavily used by `core/context/`:

```
core/reports/domain/subtask_node.py  ← Definition
     ↑
     └─── core/context/session_rehydration.py  ← Consumer
     └─── core/context/domain/services/decision_selector.py  ← Consumer
     └─── core/context/domain/services/impact_calculator.py  ← Consumer
```

### Problems
1. **Tight coupling** between bounded contexts
2. **Violation of Bounded Context isolation**
3. **Unclear ownership**: Who owns `TaskNode`? Reports or Context?
4. **Dependency direction**: Context depends on Reports (should be independent)

### Questions
- Is `TaskNode` a shared kernel?
- Should it be in a separate `core/shared/` module?
- Should Context have its own `TaskNode` representation?
- Are we missing an Anti-Corruption Layer?

---

## 🎯 Proposed Solutions

### Solution A: Rename Only (Short-term, MINIMAL)

**Actions**:
1. Rename `SubtaskNode` → `TaskNode`
2. Update all imports
3. Keep current impact model (`list[TaskNode]`)

**Pros**:
- ✅ Quick fix (1 hour)
- ✅ Restores naming consistency
- ✅ Low risk

**Cons**:
- ❌ Doesn't solve limited impact model
- ❌ Doesn't solve bounded context coupling
- ❌ Technical debt remains

**Recommendation**: **DO THIS NOW** (prerequisite for Solution B)

---

### Solution B: Extensible Impact Model (Medium-term)

**Design**: Use union types for multi-entity impacts

```python
from typing import Union
from core.context.domain.task import Task
from core.context.domain.story import Story
from core.context.domain.epic import Epic

# Define impact target types
ImpactedEntity = Union[TaskNode, StoryNode, EpicNode]

# Updated impact structure
@dataclass(frozen=True)
class DecisionImpact:
    """Represents an impact relationship from a decision to an entity."""

    decision_id: DecisionId
    impacted_entity: ImpactedEntity
    impact_type: ImpactType  # DIRECT, CASCADING, ARCHITECTURAL
    severity: ImpactSeverity  # LOW, MEDIUM, HIGH, CRITICAL
    description: str

# Updated index
impacts_by_decision: dict[str, list[DecisionImpact]]
```

**Pros**:
- ✅ Supports multiple entity types
- ✅ Type-safe (union types)
- ✅ Extensible (add new entity types easily)
- ✅ Rich metadata (impact_type, severity)

**Cons**:
- ⚠️ Requires creating `StoryNode`, `EpicNode`, `ImpactType`, `ImpactSeverity`
- ⚠️ More complex than current model
- ⚠️ Requires updating Neo4j queries
- ⚠️ Migration needed for existing data

**Effort**: 2-3 days
**Recommendation**: **DO THIS in RBAC L3 Phase 1** (aligns with Epic entity creation)

---

### Solution C: Separate Bounded Context Representation (Long-term)

**Design**: Create Context-specific representations with Anti-Corruption Layer

```python
# core/context/domain/impact_tracking/
├── impacted_task.py      # Context's view of impacted tasks
├── impacted_story.py     # Context's view of impacted stories
├── impacted_epic.py      # Context's view of impacted epics
└── impact_mapper.py      # ACL: Reports domain → Context domain
```

**Pros**:
- ✅ Complete bounded context isolation
- ✅ Context owns its representations
- ✅ No cross-context coupling
- ✅ Each context can evolve independently

**Cons**:
- ⚠️ More code (duplicate representations)
- ⚠️ Requires Anti-Corruption Layer
- ⚠️ Mapping overhead

**Effort**: 1 week
**Recommendation**: **CONSIDER** if Reports and Context evolve differently

---

## 📊 Decision Matrix

| Solution | Effort | Risk | Extensibility | Coupling | Timeline |
|----------|--------|------|---------------|----------|----------|
| A: Rename | 1 hour | LOW | LOW | HIGH | **NOW** |
| B: Union Types | 2-3 days | MEDIUM | HIGH | MEDIUM | Phase 1 |
| C: ACL | 1 week | HIGH | VERY HIGH | NONE | Future |

---

## 🎯 Recommended Approach

### Phase 0 (NOW - Hours):
✅ **Solution A**: Rename `SubtaskNode` → `TaskNode`
- Restores naming consistency
- Prerequisite for all other solutions
- Low risk, high value

### Phase 1 (RBAC L3 - Days):
⚠️ **Solution B**: Implement extensible impact model
- Aligns with Epic entity creation
- Supports multi-level impacts
- Enables better decision tracking

### Phase 2 (Future - Weeks):
💭 **Solution C**: Evaluate need for ACL
- Only if Reports and Context diverge significantly
- Monitor coupling metrics
- Decide based on actual pain points

---

## 🔥 Immediate Actions Required

### 1. Complete Subtask→Task Rename (CRITICAL)
- [ ] Rename `SubtaskNode` → `TaskNode`
- [ ] Update `core/context/domain/services/decision_selector.py`
- [ ] Update `core/context/domain/services/impact_calculator.py`
- [ ] Update `core/context/domain/services/data_indexer.py`
- [ ] Update `core/context/session_rehydration.py`
- [ ] Update `core/reports/domain/__init__.py`
- [ ] Run tests to verify no breakage

### 2. Add Type Safety (CRITICAL)
- [x] Remove `Any` from method signatures
- [x] Add explicit types: `DecisionNode`, `TaskNode`, `DecisionEdges`
- [x] Update `IndexedStoryData` with correct types

### 3. Document Decision (THIS FILE)
- [x] Create this architectural decision record
- [ ] Link from RBAC_L3_UPDATED_PLAN.md
- [ ] Add to technical debt backlog

---

## 📚 References

- `core/reports/domain/subtask_node.py` → `task_node.py` (renamed)
- `core/reports/domain/decision_node.py` (existing)
- `core/reports/domain/decision_edges.py` (existing)
- `core/context/domain/services/` (all services affected)
- `docs/architecture/decisions/2025-11-07/RBAC_L3_UPDATED_PLAN.md`
- `.cursorrules` - DDD principles section

---

## 🔍 Root Cause Analysis

### Why did this happen?

1. **Incremental refactoring**: `Case` → `Story` was done first, `Subtask` → `Task` second
2. **Separate bounded contexts**: `core/reports/` evolved independently
3. **Lack of grep**: Didn't search for ALL occurrences of "Subtask"
4. **Missing type hints**: Original code used `list` and `Any`, hiding the problem

### Prevention

- ✅ **Comprehensive search**: Use `rg -i "subtask|case" --type py` before claiming "done"
- ✅ **Type safety**: Always use explicit types, NEVER `Any` or bare `list`
- ✅ **Cross-context review**: Check dependencies before refactoring
- ✅ **Architectural validation**: Run full test suite after terminology changes

---

## 🎓 Lessons Learned

### DDD Violations Found

1. **Primitive Obsession** (still present):
   - `id: str` instead of `TaskId`
   - `role: str` instead of `Role` enum
   - `decision_id: str` instead of `DecisionId`

2. **Serialization in Domain Entities**:
   - `TaskNode.to_dict()` doesn't exist, but should use mapper pattern

3. **Bounded Context Leakage**:
   - Context service depends on Reports domain entities
   - No clear ownership of shared concepts

4. **Type Safety**:
   - Use of `Any`, bare `list`, bare `dict` without type parameters

### Correct DDD Patterns

✅ **Value Objects for IDs**: `TaskId`, `DecisionId` (already created in `core/context/domain/entity_ids/`)
✅ **Enums for Categories**: `Role`, `TaskType`, `ImpactType` (Role already created)
✅ **Mappers in Infrastructure**: Keep serialization out of domain
✅ **Explicit Types**: NEVER use `Any` or bare collections
✅ **Fail-Fast Validation**: Validate in `__post_init__`

---

## 🚧 Migration Path

### Step 1: Immediate (TODAY)
```bash
# Rename files
mv core/reports/domain/subtask_node.py core/reports/domain/task_node.py

# Update class
sed -i 's/class SubtaskNode/class TaskNode/g' core/reports/domain/task_node.py

# Update imports
rg -l "from.*subtask_node import SubtaskNode" --type py | \
  xargs sed -i 's/from.*subtask_node import SubtaskNode/from core.reports.domain.task_node import TaskNode/g'

# Update usage
rg -l "SubtaskNode" --type py | xargs sed -i 's/SubtaskNode/TaskNode/g'

# Run tests
pytest tests/unit/core/context/ -v
```

### Step 2: RBAC L3 Phase 1 (NEXT SPRINT)
- Create `ImpactedEntity` union type
- Create `EpicNode`, `StoryNode` representations
- Create `DecisionImpact` rich entity
- Update Neo4j schema to support multi-entity impacts
- Migrate existing data

### Step 3: Future (IF NEEDED)
- Evaluate need for Anti-Corruption Layer
- Create Context-specific representations
- Implement impact mappers

---

## ✅ Acceptance Criteria

This issue is resolved when:

1. ✅ ALL occurrences of `SubtaskNode` renamed to `TaskNode`
2. ✅ ALL domain services use explicit types (NO `Any`, NO bare `list`)
3. ✅ Naming consistency verified: `rg -i "subtask" --type py` returns 0 domain files
4. ✅ All unit tests pass: `pytest tests/unit/core/context/ -v`
5. ✅ Type checking passes: `mypy core/context/domain/services/`
6. ✅ This document added to ADR registry

---

## 🔗 Related Documents

- [RBAC L3 Updated Plan](../2025-11-07/RBAC_L3_UPDATED_PLAN.md)
- [Hexagonal Architecture Principles](../../HEXAGONAL_ARCHITECTURE_PRINCIPLES.md)
- [.cursorrules](../../../../.cursorrules) - DDD requirements

---

## 📝 Notes

### For Future Epic Implementation
When implementing the `Epic` entity (FASE 0 - TODO), remember to:
- Create `EpicNode` for impact tracking
- Update impact model to support `ImpactedEntity = TaskNode | StoryNode | EpicNode`
- Add `ImpactType` enum (DIRECT, CASCADING, ARCHITECTURAL)
- Update Neo4j queries to handle multi-entity impacts

### For Code Reviewers
Red flags to watch for:
- ❌ `Any` in method signatures
- ❌ Bare `list` or `dict` without type parameters
- ❌ `hasattr()` checks instead of proper Ports
- ❌ `to_dict()` in domain entities (use mappers)
- ❌ Inconsistent terminology (Case/Story, Subtask/Task)

---

**END OF REPORT**

Status: OPEN
Priority: P0 (Critical)
Assignee: Software Architect
Next Review: After Solution A implementation

