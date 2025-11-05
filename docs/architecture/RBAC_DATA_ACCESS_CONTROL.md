# RBAC - Data Access Control (Graph Queries by Role)

**Date:** 2025-11-04
**Type:** RBAC Extension - Context Visibility by Role
**Status:** 🔵 DESIGN PHASE

---

## 🎯 Problem Statement

**User Insight:**
> "El dev puede acceder al contexto de la historia de usuario y de la épica para entender su tarea.
> El arquitecto podrá acceder a la historia, a todas las tareas de la historia, a la épica y a todas las historias de la épica.
> El QA podrá solo ver historias?"

**Key Realization:** Different roles need **different levels of visibility** in the context graph.

---

## 📊 Data Access Hierarchy by Role

### Visual Representation:

```
Epic (E-001)
├── Story (US-101)
│   ├── Task (T-001) ← Current task
│   ├── Task (T-002)
│   └── Task (T-003)
├── Story (US-102)
│   ├── Task (T-004)
│   └── Task (T-005)
└── Story (US-103)
    └── Task (T-006)

ROLE VISIBILITY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Developer (T-001):
  ✅ Task (T-001)           → Para entender QUÉ hacer
  ✅ Story (US-101)         → Para entender CONTEXTO de la task
  ✅ Epic (E-001)           → Para entender OBJETIVO general
  ❌ Other tasks (T-002+)   → NO necesita ver otras tasks
  ❌ Other stories (US-102+)→ NO necesita ver otras stories

Architect (T-001):
  ✅ Task (T-001)           → Tarea a validar
  ✅ Story (US-101)         → Historia completa
  ✅ All tasks in US-101    → Ver todas las tasks (T-001, T-002, T-003)
  ✅ Epic (E-001)           → Épica completa
  ✅ All stories in E-001   → Ver todas las stories (US-101, US-102, US-103)
  ✅ Decisions across epic  → Decisiones arquitecturales del epic

QA (T-001):
  ✅ Task (T-001)           → Tarea a testear
  ✅ Story (US-101)         → Historia para entender acceptance criteria
  ✅ All tasks in US-101    → Ver tasks relacionadas para integration testing
  ✅ Epic (E-001)           → Para entender quality goals
  ❌ Other stories (US-102+)→ Solo si son dependencies?

PO (T-001):
  ✅ Story (US-101)         → Historia completa (business value)
  ✅ Epic (E-001)           → Épica (product vision)
  ✅ All stories in E-001   → Roadmap y priorización
  ❌ Individual tasks       → Abstracción técnica, no business concern

DevOps (T-001):
  ✅ Task (T-001)           → Deployment task
  ✅ Story (US-101)         → Para entender deployment context
  ✅ All tasks in US-101    → Coordination con Dev tasks
  ❌ Epic level             → No necesario para deployment

Data Engineer (T-001):
  ✅ Task (T-001)           → Schema/migration task
  ✅ Story (US-101)         → Data requirements
  ✅ All tasks in US-101    → Data dependencies entre tasks
  ✅ Epic (E-001)           → Data model consistency
```

---

## 🗄️ Neo4j Query Patterns by Role

### Developer Query (Narrow Scope):

```cypher
// Get context for Developer on task T-001

MATCH (task:Task {id: $task_id})
MATCH (task)-[:BELONGS_TO]->(story:Story)
MATCH (story)-[:PART_OF]->(epic:Epic)

// Get decisions relevant to this story
OPTIONAL MATCH (story)<-[:RELATES_TO]-(decision:Decision)

// Get subtasks only for THIS task (direct dependencies)
OPTIONAL MATCH (task)-[:DEPENDS_ON]->(dependency:Task)

RETURN {
  task: task,
  story: story,
  epic: epic,
  decisions: collect(DISTINCT decision),
  dependencies: collect(DISTINCT dependency)
} AS context

// Scope: Task + Story + Epic (no sibling tasks)
```

### Architect Query (Wide Scope):

```cypher
// Get context for Architect reviewing task T-001

MATCH (task:Task {id: $task_id})
MATCH (task)-[:BELONGS_TO]->(story:Story)
MATCH (story)-[:PART_OF]->(epic:Epic)

// Get ALL tasks in the story (not just current task)
MATCH (story)<-[:BELONGS_TO]-(all_story_tasks:Task)

// Get ALL stories in the epic
MATCH (epic)<-[:PART_OF]-(all_epic_stories:Story)

// Get ALL decisions in the epic (architectural decisions)
OPTIONAL MATCH (epic)<-[:RELATES_TO]-(epic_decisions:Decision)
WHERE epic_decisions.scope = 'TECHNICAL'

// Get ALL decisions in the story
OPTIONAL MATCH (story)<-[:RELATES_TO]-(story_decisions:Decision)

// Get cross-cutting concerns (architectural patterns)
OPTIONAL MATCH (epic)-[:USES_PATTERN]->(pattern:ArchitecturalPattern)

RETURN {
  task: task,
  story: story,
  epic: epic,
  all_story_tasks: collect(DISTINCT all_story_tasks),
  all_epic_stories: collect(DISTINCT all_epic_stories),
  epic_decisions: collect(DISTINCT epic_decisions),
  story_decisions: collect(DISTINCT story_decisions),
  architectural_patterns: collect(DISTINCT pattern)
} AS context

// Scope: Epic-wide view (full architectural context)
```

### QA Query (Story + Integration Scope):

```cypher
// Get context for QA testing task T-001

MATCH (task:Task {id: $task_id})
MATCH (task)-[:BELONGS_TO]->(story:Story)
MATCH (story)-[:PART_OF]->(epic:Epic)

// Get ALL tasks in story (for integration testing)
MATCH (story)<-[:BELONGS_TO]-(story_tasks:Task)

// Get quality criteria for story
OPTIONAL MATCH (story)-[:HAS_ACCEPTANCE_CRITERIA]->(criteria:AcceptanceCriteria)

// Get test coverage requirements
OPTIONAL MATCH (epic)-[:HAS_QUALITY_GATE]->(quality_gate:QualityGate)

// Get related test cases
OPTIONAL MATCH (task)-[:HAS_TEST_CASE]->(test_case:TestCase)

RETURN {
  task: task,
  story: story,
  epic: epic,
  story_tasks: collect(DISTINCT story_tasks),
  acceptance_criteria: collect(DISTINCT criteria),
  quality_gates: collect(DISTINCT quality_gate),
  existing_test_cases: collect(DISTINCT test_case)
} AS context

// Scope: Story-level + quality metadata
```

### PO Query (Business Scope):

```cypher
// Get context for PO approving story US-101

MATCH (story:Story {id: $story_id})
MATCH (story)-[:PART_OF]->(epic:Epic)

// Get ALL stories in epic (roadmap view)
MATCH (epic)<-[:PART_OF]-(epic_stories:Story)

// Get business value and metrics
OPTIONAL MATCH (story)-[:HAS_VALUE]->(value:BusinessValue)
OPTIONAL MATCH (epic)-[:HAS_OKR]->(okr:OKR)

// Get stakeholder feedback
OPTIONAL MATCH (story)<-[:GAVE_FEEDBACK]-(stakeholder:Stakeholder)

RETURN {
  story: story,
  epic: epic,
  all_epic_stories: collect(DISTINCT epic_stories),
  business_value: value,
  okrs: collect(DISTINCT okr),
  stakeholder_feedback: collect(DISTINCT stakeholder)
} AS context

// Scope: Epic-level business view (NO technical tasks)
```

---

## 🔧 Implementation in Context Service

### Context Query Port (Domain)

```python
# core/context/domain/ports/context_query_port.py

from typing import Protocol
from ..entities import ContextScope, RoleEnum

class ContextQueryPort(Protocol):
    """Port for querying context based on role-specific access control."""

    async def get_context_for_task(
        self,
        task_id: str,
        role: RoleEnum,
        workflow_state: str | None = None
    ) -> dict:
        """Get role-appropriate context for a task.

        Different roles get different scopes:
        - Developer: Task + Story + Epic (narrow)
        - Architect: Epic-wide view (broad)
        - QA: Story-level + quality metadata
        - PO: Business view (no technical details)

        Args:
            task_id: Task to get context for
            role: Role requesting context (determines scope)
            workflow_state: Current workflow state (for additional context)

        Returns:
            Role-filtered context dict
        """
        ...
```

### Neo4j Adapter with Role-Based Queries

```python
# core/context/infrastructure/adapters/neo4j_context_adapter.py

class Neo4jContextAdapter(ContextQueryPort):
    """Adapter for querying Neo4j with role-based access control."""

    # Query templates by role
    QUERIES = {
        RoleEnum.DEVELOPER: """
            MATCH (task:Task {id: $task_id})
            MATCH (task)-[:BELONGS_TO]->(story:Story)
            MATCH (story)-[:PART_OF]->(epic:Epic)
            OPTIONAL MATCH (story)<-[:RELATES_TO]-(decision:Decision)
            OPTIONAL MATCH (task)-[:DEPENDS_ON]->(dependency:Task)

            RETURN {
                scope: 'developer',
                task: task,
                story: story,
                epic: epic,
                decisions: collect(DISTINCT decision),
                dependencies: collect(DISTINCT dependency)
            }
        """,

        RoleEnum.ARCHITECT: """
            MATCH (task:Task {id: $task_id})
            MATCH (task)-[:BELONGS_TO]->(story:Story)
            MATCH (story)-[:PART_OF]->(epic:Epic)
            MATCH (story)<-[:BELONGS_TO]-(all_story_tasks:Task)
            MATCH (epic)<-[:PART_OF]-(all_epic_stories:Story)
            OPTIONAL MATCH (epic)<-[:RELATES_TO]-(decisions:Decision)
            WHERE decisions.scope = 'TECHNICAL'
            OPTIONAL MATCH (epic)-[:USES_PATTERN]->(pattern:ArchitecturalPattern)

            RETURN {
                scope: 'architect',
                task: task,
                story: story,
                epic: epic,
                all_story_tasks: collect(DISTINCT all_story_tasks),
                all_epic_stories: collect(DISTINCT all_epic_stories),
                decisions: collect(DISTINCT decisions),
                patterns: collect(DISTINCT pattern)
            }
        """,

        RoleEnum.QA: """
            MATCH (task:Task {id: $task_id})
            MATCH (task)-[:BELONGS_TO]->(story:Story)
            MATCH (story)-[:PART_OF]->(epic:Epic)
            MATCH (story)<-[:BELONGS_TO]-(story_tasks:Task)
            OPTIONAL MATCH (story)-[:HAS_ACCEPTANCE_CRITERIA]->(criteria:AcceptanceCriteria)
            OPTIONAL MATCH (epic)-[:HAS_QUALITY_GATE]->(quality_gate:QualityGate)

            RETURN {
                scope: 'qa',
                task: task,
                story: story,
                epic: epic,
                story_tasks: collect(DISTINCT story_tasks),
                acceptance_criteria: collect(DISTINCT criteria),
                quality_gates: collect(DISTINCT quality_gate)
            }
        """,

        RoleEnum.PO: """
            MATCH (story:Story {id: $story_id})
            MATCH (story)-[:PART_OF]->(epic:Epic)
            MATCH (epic)<-[:PART_OF]-(epic_stories:Story)
            OPTIONAL MATCH (story)-[:HAS_VALUE]->(value:BusinessValue)
            OPTIONAL MATCH (epic)-[:HAS_OKR]->(okr:OKR)

            RETURN {
                scope: 'po',
                story: story,
                epic: epic,
                all_epic_stories: collect(DISTINCT epic_stories),
                business_value: value,
                okrs: collect(DISTINCT okr)
            }
        """,
    }

    async def get_context_for_task(
        self,
        task_id: str,
        role: RoleEnum,
        workflow_state: str | None = None
    ) -> dict:
        """Execute role-appropriate query to get context."""

        # Select query based on role
        query = self.QUERIES.get(role)
        if not query:
            raise ValueError(f"No context query defined for role: {role}")

        # Execute role-specific query
        result = await self.neo4j.run_query(
            query,
            parameters={"task_id": task_id}
        )

        # Enrich with workflow state if provided
        if workflow_state:
            result["workflow"] = await self._get_workflow_context(
                task_id, role, workflow_state
            )

        return result
```

---

## 📊 Context Scope by Role

### Summary Table:

| Role | Task | Story | Epic | All Story Tasks | All Epic Stories | Decisions | Quality | Business |
|------|------|-------|------|-----------------|------------------|-----------|---------|----------|
| **Developer** | ✅ | ✅ | ✅ | ❌ | ❌ | Story-level | ❌ | ❌ |
| **Architect** | ✅ | ✅ | ✅ | ✅ | ✅ | Epic-level | ❌ | ❌ |
| **QA** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| **PO** | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ |
| **DevOps** | ✅ | ✅ | ❌ | ✅ | ❌ | Deployment | ❌ | ❌ |
| **Data** | ✅ | ✅ | ✅ | ✅ | ❌ | Data model | ❌ | ❌ |

---

## 🎯 Rationale by Role

### Developer (Narrow + Focused):

**Needs:**
- Current task details
- Story context (why this task exists)
- Epic vision (overall goal)

**Doesn't Need:**
- Other tasks in story (isolation, focus)
- Other stories in epic (noise)

**Query Scope:** `Task → Story → Epic` (vertical slice)

**Example Context:**
```yaml
task:
  id: T-001
  description: "Implement JWT token generation"

story:
  id: US-101
  title: "As user, I want secure authentication"
  acceptance_criteria: [...]

epic:
  id: E-001
  title: "Authentication & Authorization System"
  vision: "Secure, scalable auth"

decisions:
  - Decision-042: "Use JWT tokens" (Architect)
  - Decision-051: "Store in Redis" (Data)
```

---

### Architect (Wide + Holistic):

**Needs:**
- Current task (for validation)
- **ALL tasks in story** (to see full implementation)
- **ALL stories in epic** (for consistency across features)
- Epic-level architectural decisions
- Architectural patterns in use

**Why Broad Scope:**
- Ensures consistency across implementations
- Validates cross-cutting concerns
- Maintains architectural integrity

**Query Scope:** `Epic → All Stories → All Tasks` (full epic view)

**Example Context:**
```yaml
task:
  id: T-001
  description: "Implement JWT token generation"

story:
  id: US-101
  all_tasks:
    - T-001: "JWT generation"
    - T-002: "JWT validation"
    - T-003: "Token refresh"

epic:
  id: E-001
  all_stories:
    - US-101: "Secure authentication"
    - US-102: "Role-based access control"  # Related story
    - US-103: "Session management"

  architectural_decisions:
    - Decision-042: "JWT tokens" (for US-101, US-102, US-103)
    - Decision-055: "Stateless auth" (for US-101, US-103)

  patterns:
    - Pattern: "OAuth 2.0 + JWT"
    - Pattern: "Layered security"
```

---

### QA (Story-Level + Quality):

**Needs:**
- Current task (what to test)
- Story (acceptance criteria)
- **ALL tasks in story** (for integration testing)
- Quality gates and coverage requirements

**Why Story-Level:**
- Integration testing requires seeing all story tasks
- Acceptance criteria at story level
- Quality gates defined per story/epic

**Query Scope:** `Story → All Tasks + Quality Metadata`

**Example Context:**
```yaml
task:
  id: T-001
  description: "Implement JWT token generation"

story:
  id: US-101
  acceptance_criteria:
    - "User can login with email/password"
    - "JWT token issued on successful login"
    - "Token expires after 24 hours"

  all_tasks:
    - T-001: "JWT generation" (current)
    - T-002: "JWT validation"
    - T-003: "Token refresh"

quality_requirements:
  test_coverage: ">= 90%"
  security_scan: "no critical vulnerabilities"
  performance: "login < 500ms"
```

---

### PO (Business-Level Only):

**Needs:**
- Story (business value, acceptance criteria)
- Epic (product vision, OKRs)
- **ALL stories in epic** (roadmap, prioritization)

**Doesn't Need:**
- Individual tasks (technical abstraction)
- Code-level decisions

**Query Scope:** `Epic → All Stories (business view, no tasks)`

**Example Context:**
```yaml
story:
  id: US-101
  title: "Secure authentication"
  business_value: "Reduce unauthorized access by 95%"
  user_impact: "All 10K users"

epic:
  id: E-001
  title: "Auth System"
  okrs:
    - "Reduce security incidents by 80%"
    - "Improve login success rate to 99.5%"

  all_stories:
    - US-101: "Secure authentication" (current)
    - US-102: "RBAC" (dependency)
    - US-103: "Session management"

  roadmap:
    - US-101: Sprint 5 (current)
    - US-102: Sprint 6 (next)
    - US-103: Sprint 7
```

---

## 🔐 RBAC Integration: 3 Levels

```
┌─────────────────────────────────────────────────────────────┐
│ Level 1: TOOL ACCESS CONTROL (Implemented ✅)               │
│   • Which tools can each role use?                          │
│   • Developer: files, git, tests                            │
│   • Architect: files, git, db, http (read-only)             │
├─────────────────────────────────────────────────────────────┤
│ Level 2: DATA ACCESS CONTROL (Design Phase 🔵)             │
│   • Which data can each role see in graph?                  │
│   • Developer: Task + Story + Epic                          │
│   • Architect: Epic + All Stories + All Tasks               │
│   • QA: Story + All Tasks + Quality metadata                │
│   • PO: Epic + All Stories (business view)                  │
├─────────────────────────────────────────────────────────────┤
│ Level 3: WORKFLOW ACTION CONTROL (Design Phase 🔵)         │
│   • Which actions can each role perform?                    │
│   • Developer: COMMIT_CODE, REQUEST_REVIEW                  │
│   • Architect: APPROVE_DESIGN, REJECT_DESIGN                │
│   • QA: APPROVE_TESTS, REJECT_TESTS                         │
│   • PO: APPROVE_STORY, REJECT_STORY                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Context Service Enhancement

### Updated GetContext API:

```protobuf
// specs/context.proto

message GetContextRequest {
  string task_id = 1;
  string role = 2;  // developer, architect, qa, po, devops, data
  string workflow_state = 3;  // Optional: implementing, pending_review, etc.
  bool include_workflow_context = 4;  // Include workflow responsibilities
}

message ContextResponse {
  string scope = 1;  // "developer", "architect", "qa", "po"

  // Always included
  TaskContext task = 2;
  StoryContext story = 3;

  // Role-dependent (may be null based on role)
  EpicContext epic = 4;
  repeated TaskContext related_tasks = 5;  // Empty for Developer, populated for Architect/QA
  repeated StoryContext related_stories = 6;  // Empty for Dev/QA, populated for Architect/PO

  // Role-specific metadata
  ArchitecturalContext architectural = 7;  // Only for Architect
  QualityContext quality = 8;  // Only for QA
  BusinessContext business = 9;  // Only for PO

  // Workflow context (if requested)
  WorkflowContext workflow = 10;
}
```

---

## 💡 Benefits of Role-Based Context Scoping

### 1. **Precision**
```python
# Developer gets:
context_size = 2-3K tokens  # Task + Story + Epic

# Architect gets:
context_size = 8-12K tokens  # Epic + All Stories + All Tasks + Decisions

# ✅ Each role gets EXACTLY what they need
```

### 2. **Security**
```python
# Developer NO ve:
- Otras tasks de la story (aislamiento)
- Business metrics (no concern)

# PO NO ve:
- Individual tasks (abstracción técnica)
- Code-level details (no concern)

# ✅ Principle of Least Privilege
```

### 3. **Performance**
```python
# Developer query:
# MATCH task → story → epic
# ✅ Fast, small result set

# Architect query:
# MATCH epic → all stories → all tasks
# ⚠️ Larger, but necessary for validation

# ✅ Each query optimized for role's needs
```

---

## 🎯 Implementation Roadmap

### Phase 1: Define Queries (Week 1)
- [ ] Define Cypher queries for each role
- [ ] Test queries in Neo4j browser
- [ ] Measure query performance
- [ ] Document scope per role

### Phase 2: Context Service Update (Week 2)
- [ ] Add role parameter to GetContext API
- [ ] Implement query selection by role
- [ ] Update context.proto
- [ ] Add tests for role-based queries

### Phase 3: LLM Prompt Enhancement (Week 3)
- [ ] Update prompts with scope awareness
- [ ] Add "What you can see" section
- [ ] Add "Your responsibilities" based on scope
- [ ] Test with different roles

### Phase 4: Integration (Week 4)
- [ ] Update Orchestrator to pass role to Context Service
- [ ] Update VLLMAgent to use enhanced context
- [ ] E2E tests with different roles
- [ ] Performance testing

---

## 📝 Example Enhanced LLM Prompt

### Developer Prompt (Narrow Scope):

```
You are an expert software developer.

CONTEXT SCOPE:
- Task: T-001 "Implement JWT generation"
- Story: US-101 "Secure authentication"
- Epic: E-001 "Auth System"
- Relevant Decisions: 2
- Dependencies: 1 task

WORKFLOW:
- Implement this specific task
- Your work will be reviewed by ARCHITECT
- Focus on this task only (other tasks isolated)

Tools: [files, git, tests]
```

### Architect Prompt (Wide Scope):

```
You are a senior software architect.

CONTEXT SCOPE:
- Task: T-001 "Implement JWT generation" (to review)
- Story: US-101 with 3 tasks (T-001, T-002, T-003)
- Epic: E-001 with 3 stories (US-101, US-102, US-103)
- Architectural Decisions: 5 across epic
- Patterns: OAuth 2.0 + JWT, Layered Security

WORKFLOW:
- Review Developer's implementation
- Validate consistency with architectural decisions
- Check cross-cutting concerns across ALL story tasks
- Ensure patterns are followed across ALL epic stories

RESPONSIBILITIES:
- APPROVE_DESIGN if consistent
- REJECT_DESIGN with feedback if issues found
- Consider impact on US-102 (RBAC) and US-103 (Sessions)

Tools: [files, git, db, http] (read-only)
```

---

## 🎯 Summary

**Key Insight:** Context scope = function(Role)

| Role | Scope Level | Query Complexity | Token Count |
|------|-------------|------------------|-------------|
| Developer | Narrow | Simple | 2-3K |
| Architect | Wide | Complex | 8-12K |
| QA | Story-level | Medium | 4-6K |
| PO | Business | Simple | 3-5K |

**Integration:**
- Context Service: Role-based queries ✅
- VLLMAgent: Receives role-appropriate context ✅
- LLM Prompt: Knows scope limitations ✅

**Status:** 🔵 Design complete, ready for implementation

---

**Author:** AI Assistant + Tirso García
**Date:** 2025-11-04
**Next:** Implement role-based queries in Context Service

