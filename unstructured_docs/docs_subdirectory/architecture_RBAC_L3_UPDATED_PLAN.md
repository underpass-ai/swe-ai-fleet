# RBAC Level 3 Implementation Plan - UPDATED

**Date:** November 7, 2025
**Status:** 🚀 READY TO IMPLEMENT
**Architect:** Tirso García
**Context:** Post-documentation audit, post-architectural clarification

---

## 🎯 **ARCHITECTURAL DECISIONS (CONFIRMED)**

### 1. **Model Unification**
- ✅ `Case` = `Story` (refactor all references)
- ✅ `Subtask` = `Task` (refactor all references)
- ✅ Add `Epic` entity to graph model
- **Rationale:** Bounded contexts must use the same ubiquitous language. Context Service aligns with Planning/Workflow terminology.

### 2. **Epic → Story → Task Hierarchy**
```
Epic (E-001) "Authentication System"
├── Story (US-101) "Implement JWT auth"
│   ├── Task (T-001) "Create JWT middleware"
│   ├── Task (T-002) "Add token validation"
│   └── Task (T-003) "Write integration tests"
├── Story (US-102) "Add OAuth2 support"
│   ├── Task (T-004) "Research OAuth2 providers"
│   └── Task (T-005) "Implement Google OAuth"
└── Story (US-103) "Setup refresh tokens"
    └── Task (T-006) "Implement token refresh endpoint"
```

### 3. **YAML-Based Visibility Matrix**
- ✅ `config/context_visibility.yaml` defines what each role can see
- ✅ `config/context_columns.yaml` defines column-level filtering
- ❌ NO hardcoded role checks in code
- **Rationale:** Parametrizable security policies, easy to audit and modify without code changes.

### 4. **PO Role = Full Access**
- ✅ PO (Product Owner) is HUMAN user of po-ui
- ✅ PO can see EVERYTHING (no restrictions)
- **Rationale:** PO needs complete visibility to manage backlog, priorities, and team work.

### 5. **Testing Strategy**
- ✅ Unit tests (>90% coverage) - NOW
- ✅ Integration tests (Neo4j queries) - NOW
- ✅ Performance tests (query benchmarks) - NOW
- ❌ E2E tests - POSTPONED until po-ui is complete
- ✅ Security audit (data leak prevention) - NOW
- **Rationale:** Ensure RBAC L3 is correct, fast, and secure before exposing to po-ui.

---

## 📊 **VISIBILITY MATRIX (YAML-Based)**

### `config/context_visibility.yaml`

```yaml
# Context Service - Role-Based Data Access Control
# Version: 1.0
# Last Updated: 2025-11-07

roles:
  developer:
    description: "Software engineer implementing features"
    visibility:
      epic: read_metadata        # Can see Epic title, description (not other stories)
      story: read_assigned       # Can see Story for current task
      task: read_assigned_only   # Can ONLY see assigned task (T-001)
      other_tasks: false         # Cannot see sibling tasks (T-002, T-003)
      other_stories: false       # Cannot see other stories in Epic
      decisions: read_relevant   # Only decisions affecting current task
    columns:
      story:
        - id
        - title
        - description
        - acceptance_criteria
        # business_notes excluded (PO-only)
      task:
        - id
        - title
        - description
        - status
        - dependencies
        # estimated_hours excluded

  architect:
    description: "System architect validating designs and reviewing code"
    visibility:
      epic: read_full            # Can see entire Epic
      story: read_all_in_epic    # Can see ALL stories in Epic
      task: read_all_in_story    # Can see ALL tasks in Story
      decisions: read_all_in_epic # All decisions in Epic
    columns:
      story:
        - id
        - title
        - description
        - acceptance_criteria
        - business_notes          # Architect sees business context
        - created_by
      task:
        - id
        - title
        - description
        - status
        - dependencies
        - assigned_to
        - estimated_hours

  qa:
    description: "Quality assurance engineer testing features"
    visibility:
      epic: read_metadata
      story: read_all_in_epic    # QA sees all stories to understand test scope
      task: read_all_in_story    # QA sees all tasks to create test plan
      decisions: read_relevant   # Only test-impacting decisions
    columns:
      story:
        - id
        - title
        - description
        - acceptance_criteria
        # business_notes excluded
      task:
        - id
        - title
        - description
        - status
        - test_status             # QA-specific field
        - dependencies

  po:
    description: "Product Owner (HUMAN) managing backlog and priorities"
    visibility:
      epic: read_full
      story: read_all_in_epic
      task: read_all_in_story
      decisions: read_all
    columns:
      story: all                  # PO sees ALL columns
      task: all                   # PO sees ALL columns
      decision: all               # PO sees ALL columns
    restrictions: none            # PO has ZERO restrictions

  devops:
    description: "DevOps engineer managing infrastructure and deployments"
    visibility:
      epic: read_metadata
      story: read_assigned
      task: read_assigned_only
      decisions: read_infra_only  # Only infrastructure decisions
    columns:
      story:
        - id
        - title
        - deployment_notes
      task:
        - id
        - title
        - deployment_status
        - infrastructure_requirements

  data:
    description: "Data engineer managing schemas and migrations"
    visibility:
      epic: read_metadata
      story: read_assigned
      task: read_assigned_only
      decisions: read_data_only   # Only data/schema decisions
    columns:
      story:
        - id
        - title
        - data_requirements
      task:
        - id
        - title
        - schema_changes
        - migration_plan
```

---

## 🏗️ **IMPLEMENTATION PHASES**

### **PHASE 0: Model Refactoring (CRITICAL - DO FIRST)**

**Goal:** Unify terminology across bounded contexts.

#### Tasks:

1. **Rename `Case` → `Story` in core/context**
   - `core/context/domain/case.py` → `story.py`
   - `core/context/domain/case_header.py` → `story_header.py`
   - Update all imports and references
   - Update Neo4j labels: `Case` → `Story`

2. **Rename `Subtask` → `Task` in core/context**
   - `core/context/domain/subtask.py` → `task.py`
   - Update all imports and references
   - Update Neo4j labels: `Subtask` → `Task`

3. **Add `Epic` entity to model**
   - Create `core/context/domain/epic.py`
   - Add Neo4j label: `Epic`
   - Add relationships:
     - `(Epic)-[:CONTAINS]->(Story)`
   - Update `SessionRehydrationUseCase` to include Epic data

4. **Update protobuf**
   - `specs/fleet/context/v1/context.proto`:
     - `case_id` → `story_id`
     - `subtask_id` → `task_id`
     - Add `epic_id` field
   - Regenerate Python stubs

5. **Update all Neo4j queries**
   - `core/context/adapters/neo4j_query_store.py`
   - `core/reports/adapters/neo4j_decision_graph_read_adapter.py`
   - Replace `Case` → `Story`, `Subtask` → `Task`
   - Add Epic queries

**Deliverables:**
- [ ] All tests passing after refactor
- [ ] No references to `Case` or `Subtask` in codebase
- [ ] Epic entity fully integrated

**Estimated Time:** 3-4 hours

---

### **PHASE 1: RBAC L3 Core Implementation**

**Goal:** Implement role-based data access control with YAML configuration.

#### Task 1: Configuration Files

**File:** `config/context_visibility.yaml`
```yaml
# (See YAML above)
```

**File:** `config/context_columns.yaml`
```yaml
# Column-level filtering rules
entities:
  story:
    columns:
      id: { always_visible: true }
      title: { always_visible: true }
      description: { always_visible: true }
      acceptance_criteria: { roles: [developer, architect, qa, po] }
      business_notes: { roles: [architect, po] }  # Developer CANNOT see
      created_by: { roles: [architect, po] }
      estimated_hours: { roles: [architect, po] }

  task:
    columns:
      id: { always_visible: true }
      title: { always_visible: true }
      description: { always_visible: true }
      status: { always_visible: true }
      dependencies: { roles: [developer, architect, qa, po] }
      assigned_to: { roles: [architect, qa, po] }
      estimated_hours: { roles: [architect, po] }
      test_status: { roles: [qa, po] }
      deployment_status: { roles: [devops, po] }

  decision:
    columns:
      id: { always_visible: true }
      title: { always_visible: true }
      rationale: { roles: [architect, po] }
      alternatives_considered: { roles: [architect, po] }
```

#### Task 2: Domain Value Objects

**File:** `core/context/domain/role_visibility_policy.py`

```python
"""Role-based visibility policy loaded from YAML configuration."""

from dataclasses import dataclass
from typing import Any
import yaml


@dataclass(frozen=True)
class VisibilityRules:
    """Visibility rules for a specific role."""

    role: str
    can_see_epic_full: bool
    can_see_all_stories_in_epic: bool
    can_see_all_tasks_in_story: bool
    can_see_other_tasks: bool
    can_see_other_stories: bool
    decision_scope: str  # "relevant", "all_in_epic", "all", "infra_only", "data_only"


@dataclass(frozen=True)
class RoleVisibilityPolicy:
    """Policy that defines what data each role can access."""

    rules: dict[str, VisibilityRules]

    @staticmethod
    def load_from_yaml(config_path: str) -> "RoleVisibilityPolicy":
        """Load visibility policy from YAML configuration."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        rules = {}
        for role_name, role_config in config["roles"].items():
            visibility = role_config["visibility"]
            rules[role_name] = VisibilityRules(
                role=role_name,
                can_see_epic_full=(visibility.get("epic") == "read_full"),
                can_see_all_stories_in_epic=(visibility.get("story") in ["read_all_in_epic", "read_full"]),
                can_see_all_tasks_in_story=(visibility.get("task") in ["read_all_in_story", "read_all_in_epic"]),
                can_see_other_tasks=(visibility.get("other_tasks", False)),
                can_see_other_stories=(visibility.get("other_stories", False)),
                decision_scope=visibility.get("decisions", "relevant"),
            )

        return RoleVisibilityPolicy(rules=rules)

    def get_rules_for_role(self, role: str) -> VisibilityRules:
        """Get visibility rules for a specific role."""
        if role not in self.rules:
            raise ValueError(f"Unknown role: {role}")
        return self.rules[role]
```

#### Task 3: Column Filtering Service

**File:** `core/context/domain/column_filter_service.py`

```python
"""Service for filtering columns based on role permissions."""

from dataclasses import dataclass
from typing import Any
import yaml


@dataclass(frozen=True)
class ColumnFilterService:
    """Service that filters entity columns based on role."""

    column_rules: dict[str, dict[str, dict[str, Any]]]

    @staticmethod
    def load_from_yaml(config_path: str) -> "ColumnFilterService":
        """Load column filtering rules from YAML."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return ColumnFilterService(column_rules=config["entities"])

    def filter_entity(
        self,
        entity_type: str,
        entity_data: dict[str, Any],
        role: str,
    ) -> dict[str, Any]:
        """Filter entity columns based on role permissions.

        Args:
            entity_type: Type of entity (story, task, decision)
            entity_data: Full entity data
            role: Current user role

        Returns:
            Filtered entity data with only allowed columns
        """
        if entity_type not in self.column_rules:
            return entity_data  # No rules defined, return all

        entity_rules = self.column_rules[entity_type]["columns"]
        filtered = {}

        for column_name, column_value in entity_data.items():
            if column_name not in entity_rules:
                # Column not in rules → include by default
                filtered[column_name] = column_value
                continue

            rule = entity_rules[column_name]

            # Check if always visible
            if rule.get("always_visible", False):
                filtered[column_name] = column_value
                continue

            # Check if role has access
            allowed_roles = rule.get("roles", [])
            if role in allowed_roles:
                filtered[column_name] = column_value
            # else: column is excluded

        return filtered

    def filter_entities(
        self,
        entity_type: str,
        entities: list[dict[str, Any]],
        role: str,
    ) -> list[dict[str, Any]]:
        """Filter multiple entities."""
        return [
            self.filter_entity(entity_type, entity, role)
            for entity in entities
        ]
```

#### Task 4: Role-Based Context Use Case

**File:** `core/context/usecases/get_role_based_context_usecase.py`

```python
"""Use case for retrieving context filtered by role permissions."""

from dataclasses import dataclass
from typing import Any

from core.context.domain.role_visibility_policy import RoleVisibilityPolicy
from core.context.domain.column_filter_service import ColumnFilterService
from core.context.ports.decisiongraph_read_port import DecisionGraphReadPort
from core.context.session_rehydration import SessionRehydrationUseCase, RehydrationRequest


@dataclass(frozen=True)
class GetRoleBasedContextUseCase:
    """Use case for getting context filtered by role.

    This use case enforces RBAC Level 3 (Data Access Control) by:
    1. Filtering which Stories/Tasks/Decisions a role can see
    2. Filtering which columns within those entities are visible
    3. Logging data access for audit trail
    """

    rehydration_usecase: SessionRehydrationUseCase
    visibility_policy: RoleVisibilityPolicy
    column_filter: ColumnFilterService
    graph_store: DecisionGraphReadPort

    def execute(
        self,
        story_id: str,
        task_id: str | None,
        role: str,
        include_audit: bool = True,
    ) -> dict[str, Any]:
        """Get context for a specific task, filtered by role.

        Args:
            story_id: Story identifier
            task_id: Task identifier (optional, if None returns story-level context)
            role: Role requesting context (developer, architect, qa, po, devops, data)
            include_audit: Whether to log this data access

        Returns:
            Filtered context data based on role permissions

        Raises:
            ValueError: If role is unknown or task not found
        """
        # Get visibility rules for role
        rules = self.visibility_policy.get_rules_for_role(role)

        # Special case: PO sees everything
        if role == "po":
            return self._get_full_context(story_id, task_id)

        # Get Epic/Story/Task hierarchy from graph
        epic_id = self.graph_store.get_epic_for_story(story_id)

        # Filter visible data based on role
        context = {
            "role": role,
            "story_id": story_id,
            "task_id": task_id,
        }

        # Epic data (metadata only for most roles)
        if epic_id:
            epic_data = self.graph_store.get_epic(epic_id)
            if rules.can_see_epic_full:
                context["epic"] = self.column_filter.filter_entity("epic", epic_data, role)
            else:
                context["epic"] = {
                    "id": epic_data["id"],
                    "title": epic_data["title"],
                }

        # Story data
        story_data = self.graph_store.get_story(story_id)
        context["story"] = self.column_filter.filter_entity("story", story_data, role)

        # Task data
        if task_id:
            task_data = self.graph_store.get_task(task_id)
            context["task"] = self.column_filter.filter_entity("task", task_data, role)

        # Other tasks in story (based on visibility rules)
        if rules.can_see_all_tasks_in_story:
            all_tasks = self.graph_store.get_tasks_for_story(story_id)
            context["other_tasks"] = self.column_filter.filter_entities("task", all_tasks, role)
        elif not rules.can_see_other_tasks:
            context["other_tasks"] = []  # Explicitly hide

        # Other stories in epic (based on visibility rules)
        if rules.can_see_all_stories_in_epic and epic_id:
            all_stories = self.graph_store.get_stories_for_epic(epic_id)
            context["other_stories"] = self.column_filter.filter_entities("story", all_stories, role)
        elif not rules.can_see_other_stories:
            context["other_stories"] = []  # Explicitly hide

        # Decisions (filtered by scope)
        decisions = self._get_filtered_decisions(
            story_id=story_id,
            task_id=task_id,
            epic_id=epic_id,
            decision_scope=rules.decision_scope,
        )
        context["decisions"] = self.column_filter.filter_entities("decision", decisions, role)

        # Audit logging
        if include_audit:
            self._log_data_access(role=role, story_id=story_id, task_id=task_id, context_keys=list(context.keys()))

        return context

    def _get_full_context(self, story_id: str, task_id: str | None) -> dict[str, Any]:
        """Get full context without filtering (for PO role)."""
        epic_id = self.graph_store.get_epic_for_story(story_id)

        context = {
            "role": "po",
            "story_id": story_id,
            "task_id": task_id,
        }

        if epic_id:
            context["epic"] = self.graph_store.get_epic(epic_id)
            context["other_stories"] = self.graph_store.get_stories_for_epic(epic_id)

        context["story"] = self.graph_store.get_story(story_id)
        context["other_tasks"] = self.graph_store.get_tasks_for_story(story_id)

        if task_id:
            context["task"] = self.graph_store.get_task(task_id)

        context["decisions"] = self.graph_store.list_decisions(epic_id or story_id)

        return context

    def _get_filtered_decisions(
        self,
        story_id: str,
        task_id: str | None,
        epic_id: str | None,
        decision_scope: str,
    ) -> list[dict[str, Any]]:
        """Get decisions filtered by scope."""
        if decision_scope == "all":
            return self.graph_store.list_decisions(epic_id or story_id)
        elif decision_scope == "all_in_epic" and epic_id:
            return self.graph_store.list_decisions(epic_id)
        elif decision_scope == "relevant" and task_id:
            # Only decisions that AFFECT current task
            return self.graph_store.get_decisions_affecting_task(task_id)
        elif decision_scope == "infra_only":
            # Only infrastructure/deployment decisions
            all_decisions = self.graph_store.list_decisions(story_id)
            return [d for d in all_decisions if d.get("category") == "infrastructure"]
        elif decision_scope == "data_only":
            # Only data/schema decisions
            all_decisions = self.graph_store.list_decisions(story_id)
            return [d for d in all_decisions if d.get("category") == "data"]
        else:
            return []

    def _log_data_access(
        self,
        role: str,
        story_id: str,
        task_id: str | None,
        context_keys: list[str],
    ) -> None:
        """Log data access for audit trail.

        This could write to:
        - Neo4j (create DataAccessEvent nodes)
        - Structured logs (JSON)
        - External audit system
        """
        # TODO: Implement based on audit requirements
        # For now, just log to stdout
        import json
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            "DATA_ACCESS",
            extra={
                "event": "context.data_access",
                "role": role,
                "story_id": story_id,
                "task_id": task_id,
                "context_keys": context_keys,
            },
        )
```

#### Task 5: Neo4j Queries (Role-Filtered)

**File:** `core/context/adapters/neo4j_rbac_queries.py`

```python
"""Neo4j queries for RBAC Level 3 data access control."""

from typing import Any


class Neo4jRBACQueries:
    """Neo4j Cypher queries filtered by role."""

    @staticmethod
    def get_epic_for_story(story_id: str) -> str:
        """Get Epic ID for a Story."""
        return """
        MATCH (e:Epic)-[:CONTAINS]->(s:Story {id: $story_id})
        RETURN e.id AS epic_id
        """

    @staticmethod
    def get_context_for_developer(task_id: str) -> str:
        """Get context for Developer role.

        Developer can see:
        - Current task (T-001)
        - Parent story (US-101)
        - Parent epic (E-001) - metadata only
        - Decisions affecting current task

        Developer CANNOT see:
        - Other tasks in story
        - Other stories in epic
        """
        return """
        MATCH (t:Task {id: $task_id})<-[:HAS_TASK]-(s:Story)<-[:CONTAINS]-(e:Epic)
        OPTIONAL MATCH (d:Decision)-[:AFFECTS]->(t)
        RETURN
            e.id AS epic_id,
            e.title AS epic_title,
            s.id AS story_id,
            s.title AS story_title,
            s.description AS story_description,
            s.acceptance_criteria AS story_acceptance_criteria,
            t.id AS task_id,
            t.title AS task_title,
            t.description AS task_description,
            t.status AS task_status,
            t.dependencies AS task_dependencies,
            collect(DISTINCT {
                id: d.id,
                title: d.title,
                summary: d.summary
            }) AS decisions
        """

    @staticmethod
    def get_context_for_architect(task_id: str) -> str:
        """Get context for Architect role.

        Architect can see:
        - Current task
        - ALL tasks in story
        - Parent story
        - ALL stories in epic
        - Parent epic (full)
        - ALL decisions in epic
        """
        return """
        MATCH (t:Task {id: $task_id})<-[:HAS_TASK]-(s:Story)<-[:CONTAINS]-(e:Epic)
        MATCH (s)-[:HAS_TASK]->(all_tasks:Task)
        MATCH (e)-[:CONTAINS]->(all_stories:Story)
        OPTIONAL MATCH (d:Decision)-[:RELATES_TO]->(e)
        RETURN
            e.id AS epic_id,
            e.title AS epic_title,
            e.description AS epic_description,
            e.business_notes AS epic_business_notes,
            s.id AS story_id,
            s.title AS story_title,
            s.description AS story_description,
            s.acceptance_criteria AS story_acceptance_criteria,
            s.business_notes AS story_business_notes,
            t.id AS task_id,
            t.title AS task_title,
            t.description AS task_description,
            t.status AS task_status,
            t.dependencies AS task_dependencies,
            t.assigned_to AS task_assigned_to,
            t.estimated_hours AS task_estimated_hours,
            collect(DISTINCT {
                id: all_tasks.id,
                title: all_tasks.title,
                description: all_tasks.description,
                status: all_tasks.status,
                dependencies: all_tasks.dependencies,
                assigned_to: all_tasks.assigned_to,
                estimated_hours: all_tasks.estimated_hours
            }) AS all_tasks_in_story,
            collect(DISTINCT {
                id: all_stories.id,
                title: all_stories.title,
                description: all_stories.description,
                status: all_stories.status
            }) AS all_stories_in_epic,
            collect(DISTINCT {
                id: d.id,
                title: d.title,
                rationale: d.rationale,
                alternatives_considered: d.alternatives_considered
            }) AS decisions
        """

    @staticmethod
    def get_context_for_qa(task_id: str) -> str:
        """Get context for QA role.

        QA can see:
        - Current task
        - ALL tasks in story (to create test plan)
        - Parent story
        - ALL stories in epic (to understand test scope)
        - Parent epic (metadata)
        - Decisions affecting tests
        """
        return """
        MATCH (t:Task {id: $task_id})<-[:HAS_TASK]-(s:Story)<-[:CONTAINS]-(e:Epic)
        MATCH (s)-[:HAS_TASK]->(all_tasks:Task)
        MATCH (e)-[:CONTAINS]->(all_stories:Story)
        OPTIONAL MATCH (d:Decision)-[:AFFECTS]->(all_tasks)
        WHERE d.category IN ['testing', 'quality', 'architecture']
        RETURN
            e.id AS epic_id,
            e.title AS epic_title,
            s.id AS story_id,
            s.title AS story_title,
            s.description AS story_description,
            s.acceptance_criteria AS story_acceptance_criteria,
            t.id AS task_id,
            t.title AS task_title,
            t.description AS task_description,
            t.status AS task_status,
            t.test_status AS task_test_status,
            t.dependencies AS task_dependencies,
            collect(DISTINCT {
                id: all_tasks.id,
                title: all_tasks.title,
                description: all_tasks.description,
                status: all_tasks.status,
                test_status: all_tasks.test_status,
                dependencies: all_tasks.dependencies
            }) AS all_tasks_in_story,
            collect(DISTINCT {
                id: all_stories.id,
                title: all_stories.title,
                status: all_stories.status
            }) AS all_stories_in_epic,
            collect(DISTINCT {
                id: d.id,
                title: d.title,
                summary: d.summary
            }) AS decisions
        """

    @staticmethod
    def get_context_for_po(epic_id: str | None, story_id: str, task_id: str | None) -> str:
        """Get context for PO role.

        PO can see EVERYTHING (no restrictions).
        """
        return """
        MATCH (t:Task {id: $task_id})<-[:HAS_TASK]-(s:Story)<-[:CONTAINS]-(e:Epic)
        MATCH (s)-[:HAS_TASK]->(all_tasks:Task)
        MATCH (e)-[:CONTAINS]->(all_stories:Story)
        OPTIONAL MATCH (d:Decision)-[:RELATES_TO]->(e)
        RETURN
            e AS epic,
            s AS story,
            t AS task,
            collect(DISTINCT all_tasks) AS all_tasks_in_story,
            collect(DISTINCT all_stories) AS all_stories_in_epic,
            collect(DISTINCT d) AS decisions
        """

    @staticmethod
    def get_context_for_devops(task_id: str) -> str:
        """Get context for DevOps role (infrastructure focus)."""
        return """
        MATCH (t:Task {id: $task_id})<-[:HAS_TASK]-(s:Story)<-[:CONTAINS]-(e:Epic)
        OPTIONAL MATCH (d:Decision)-[:AFFECTS]->(t)
        WHERE d.category IN ['infrastructure', 'deployment', 'devops']
        RETURN
            e.id AS epic_id,
            e.title AS epic_title,
            s.id AS story_id,
            s.title AS story_title,
            s.deployment_notes AS story_deployment_notes,
            t.id AS task_id,
            t.title AS task_title,
            t.deployment_status AS task_deployment_status,
            t.infrastructure_requirements AS task_infrastructure_requirements,
            collect(DISTINCT {
                id: d.id,
                title: d.title,
                summary: d.summary,
                category: d.category
            }) AS decisions
        """

    @staticmethod
    def get_context_for_data(task_id: str) -> str:
        """Get context for Data Engineer role (schema/migration focus)."""
        return """
        MATCH (t:Task {id: $task_id})<-[:HAS_TASK]-(s:Story)<-[:CONTAINS]-(e:Epic)
        OPTIONAL MATCH (d:Decision)-[:AFFECTS]->(t)
        WHERE d.category IN ['data', 'schema', 'migration']
        RETURN
            e.id AS epic_id,
            e.title AS epic_title,
            s.id AS story_id,
            s.title AS story_title,
            s.data_requirements AS story_data_requirements,
            t.id AS task_id,
            t.title AS task_title,
            t.schema_changes AS task_schema_changes,
            t.migration_plan AS task_migration_plan,
            collect(DISTINCT {
                id: d.id,
                title: d.title,
                summary: d.summary,
                category: d.category
            }) AS decisions
        """
```

**Deliverables:**
- [ ] YAML config files created and validated
- [ ] RoleVisibilityPolicy value object implemented
- [ ] ColumnFilterService implemented
- [ ] GetRoleBasedContextUseCase implemented
- [ ] 6 role-specific Neo4j queries implemented
- [ ] DataAccessAuditLogger implemented

**Estimated Time:** 4-6 hours

---

### **PHASE 2: Testing & Validation**

#### Unit Tests

**File:** `core/context/tests/unit/test_role_visibility_policy.py`

```python
"""Unit tests for RoleVisibilityPolicy."""

import pytest
from pathlib import Path

from core/context.domain.role_visibility_policy import RoleVisibilityPolicy, VisibilityRules


def test_load_from_yaml():
    """Test loading visibility policy from YAML."""
    # Use test fixture
    config_path = Path(__file__).parent / "fixtures" / "test_visibility.yaml"
    policy = RoleVisibilityPolicy.load_from_yaml(str(config_path))

    assert "developer" in policy.rules
    assert "architect" in policy.rules
    assert "po" in policy.rules


def test_developer_visibility_rules():
    """Test that Developer has restricted visibility."""
    config_path = "config/context_visibility.yaml"
    policy = RoleVisibilityPolicy.load_from_yaml(config_path)

    dev_rules = policy.get_rules_for_role("developer")

    assert dev_rules.role == "developer"
    assert not dev_rules.can_see_epic_full
    assert not dev_rules.can_see_all_stories_in_epic
    assert not dev_rules.can_see_all_tasks_in_story
    assert not dev_rules.can_see_other_tasks
    assert not dev_rules.can_see_other_stories
    assert dev_rules.decision_scope == "relevant"


def test_architect_visibility_rules():
    """Test that Architect has full visibility."""
    config_path = "config/context_visibility.yaml"
    policy = RoleVisibilityPolicy.load_from_yaml(config_path)

    arch_rules = policy.get_rules_for_role("architect")

    assert arch_rules.role == "architect"
    assert arch_rules.can_see_epic_full
    assert arch_rules.can_see_all_stories_in_epic
    assert arch_rules.can_see_all_tasks_in_story
    assert arch_rules.decision_scope == "all_in_epic"


def test_po_visibility_rules():
    """Test that PO has unrestricted visibility."""
    config_path = "config/context_visibility.yaml"
    policy = RoleVisibilityPolicy.load_from_yaml(config_path)

    po_rules = policy.get_rules_for_role("po")

    assert po_rules.role == "po"
    assert po_rules.can_see_epic_full
    assert po_rules.can_see_all_stories_in_epic
    assert po_rules.can_see_all_tasks_in_story
    assert po_rules.decision_scope == "all"


def test_unknown_role_raises_error():
    """Test that unknown role raises ValueError."""
    config_path = "config/context_visibility.yaml"
    policy = RoleVisibilityPolicy.load_from_yaml(config_path)

    with pytest.raises(ValueError, match="Unknown role"):
        policy.get_rules_for_role("hacker")
```

**File:** `core/context/tests/unit/test_column_filter_service.py`

```python
"""Unit tests for ColumnFilterService."""

import pytest
from core.context.domain.column_filter_service import ColumnFilterService


def test_filter_story_for_developer():
    """Test that Developer cannot see business_notes."""
    config_path = "config/context_columns.yaml"
    filter_service = ColumnFilterService.load_from_yaml(config_path)

    story_data = {
        "id": "US-101",
        "title": "Implement JWT auth",
        "description": "Add JWT authentication to API",
        "acceptance_criteria": "User can login with JWT",
        "business_notes": "HIGH PRIORITY - Revenue impact",  # Developer should NOT see this
        "created_by": "po@example.com",
    }

    filtered = filter_service.filter_entity("story", story_data, "developer")

    assert "id" in filtered
    assert "title" in filtered
    assert "description" in filtered
    assert "acceptance_criteria" in filtered
    assert "business_notes" not in filtered  # ✅ Filtered out
    assert "created_by" not in filtered  # ✅ Filtered out


def test_filter_story_for_architect():
    """Test that Architect CAN see business_notes."""
    config_path = "config/context_columns.yaml"
    filter_service = ColumnFilterService.load_from_yaml(config_path)

    story_data = {
        "id": "US-101",
        "title": "Implement JWT auth",
        "business_notes": "HIGH PRIORITY - Revenue impact",
    }

    filtered = filter_service.filter_entity("story", story_data, "architect")

    assert "business_notes" in filtered  # ✅ Visible to Architect


def test_filter_story_for_po():
    """Test that PO can see ALL columns."""
    config_path = "config/context_columns.yaml"
    filter_service = ColumnFilterService.load_from_yaml(config_path)

    story_data = {
        "id": "US-101",
        "title": "Implement JWT auth",
        "business_notes": "HIGH PRIORITY",
        "created_by": "po@example.com",
        "estimated_hours": 40,
    }

    filtered = filter_service.filter_entity("story", story_data, "po")

    assert len(filtered) == len(story_data)  # ✅ No columns filtered


def test_filter_multiple_entities():
    """Test filtering list of entities."""
    config_path = "config/context_columns.yaml"
    filter_service = ColumnFilterService.load_from_yaml(config_path)

    tasks = [
        {"id": "T-001", "title": "Task 1", "estimated_hours": 10},
        {"id": "T-002", "title": "Task 2", "estimated_hours": 20},
    ]

    filtered = filter_service.filter_entities("task", tasks, "developer")

    assert len(filtered) == 2
    assert "estimated_hours" not in filtered[0]  # ✅ Filtered out for Developer
    assert "estimated_hours" not in filtered[1]
```

**File:** `core/context/tests/integration/test_rbac_neo4j_queries.py`

```python
"""Integration tests for RBAC Neo4j queries."""

import pytest
from core.context.adapters.neo4j_query_store import Neo4jQueryStore
from core.context.adapters.neo4j_rbac_queries import Neo4jRBACQueries


@pytest.fixture
def neo4j_with_test_data(neo4j_config):
    """Seed Neo4j with test data."""
    store = Neo4jQueryStore(config=neo4j_config)

    # Create Epic → Story → Task hierarchy
    store.execute("""
        CREATE (e:Epic {id: 'E-001', title: 'Authentication System'})
        CREATE (s1:Story {id: 'US-101', title: 'JWT auth'})
        CREATE (s2:Story {id: 'US-102', title: 'OAuth2 support'})
        CREATE (t1:Task {id: 'T-001', title: 'Create middleware'})
        CREATE (t2:Task {id: 'T-002', title: 'Add validation'})
        CREATE (t3:Task {id: 'T-003', title: 'Write tests'})
        CREATE (e)-[:CONTAINS]->(s1)
        CREATE (e)-[:CONTAINS]->(s2)
        CREATE (s1)-[:HAS_TASK]->(t1)
        CREATE (s1)-[:HAS_TASK]->(t2)
        CREATE (s1)-[:HAS_TASK]->(t3)
    """)

    yield store

    # Cleanup
    store.execute("MATCH (n) WHERE n.id STARTS WITH 'E-001' OR n.id STARTS WITH 'US-' OR n.id STARTS WITH 'T-' DETACH DELETE n")
    store.close()


def test_developer_cannot_see_other_tasks(neo4j_with_test_data):
    """Test that Developer CANNOT see sibling tasks."""
    query = Neo4jRBACQueries.get_context_for_developer("T-001")
    result = neo4j_with_test_data.query(query, {"task_id": "T-001"})

    assert len(result) == 1
    context = result[0]

    # Developer can see current task
    assert context["task_id"] == "T-001"

    # Developer can see story
    assert context["story_id"] == "US-101"

    # Developer can see epic (metadata only)
    assert context["epic_id"] == "E-001"
    assert context["epic_title"] == "Authentication System"

    # Developer CANNOT see other tasks
    # (other_tasks should not be in result for developer query)
    assert "all_tasks_in_story" not in context


def test_architect_sees_all_tasks(neo4j_with_test_data):
    """Test that Architect CAN see all tasks in story."""
    query = Neo4jRBACQueries.get_context_for_architect("T-001")
    result = neo4j_with_test_data.query(query, {"task_id": "T-001"})

    assert len(result) == 1
    context = result[0]

    # Architect can see all tasks
    all_tasks = context["all_tasks_in_story"]
    assert len(all_tasks) == 3
    task_ids = [t["id"] for t in all_tasks]
    assert "T-001" in task_ids
    assert "T-002" in task_ids
    assert "T-003" in task_ids


def test_po_sees_everything(neo4j_with_test_data):
    """Test that PO sees complete context."""
    query = Neo4jRBACQueries.get_context_for_po(epic_id="E-001", story_id="US-101", task_id="T-001")
    result = neo4j_with_test_data.query(query, {"task_id": "T-001"})

    assert len(result) == 1
    context = result[0]

    # PO sees Epic (full)
    assert context["epic"]["id"] == "E-001"

    # PO sees all stories in Epic
    all_stories = context["all_stories_in_epic"]
    assert len(all_stories) == 2
    story_ids = [s["id"] for s in all_stories]
    assert "US-101" in story_ids
    assert "US-102" in story_ids

    # PO sees all tasks
    all_tasks = context["all_tasks_in_story"]
    assert len(all_tasks) == 3
```

**File:** `core/context/tests/performance/test_query_performance.py`

```python
"""Performance tests for RBAC context queries."""

import pytest
import time
from core.context.adapters.neo4j_query_store import Neo4jQueryStore
from core.context.adapters.neo4j_rbac_queries import Neo4jRBACQueries


@pytest.fixture
def neo4j_with_large_dataset(neo4j_config):
    """Seed Neo4j with large test dataset."""
    store = Neo4jQueryStore(config=neo4j_config)

    # Create 10 Epics, 100 Stories, 1000 Tasks
    store.execute("""
        UNWIND range(1, 10) AS epic_num
        CREATE (e:Epic {
            id: 'E-' + epic_num,
            title: 'Epic ' + epic_num
        })
        WITH e, epic_num
        UNWIND range(1, 10) AS story_num
        CREATE (s:Story {
            id: 'US-' + (epic_num * 100 + story_num),
            title: 'Story ' + story_num,
            description: 'Long description...',
            acceptance_criteria: 'AC...',
            business_notes: 'Business notes...'
        })
        CREATE (e)-[:CONTAINS]->(s)
        WITH s
        UNWIND range(1, 10) AS task_num
        CREATE (t:Task {
            id: 'T-' + (s.id + '-' + task_num),
            title: 'Task ' + task_num,
            description: 'Task description...',
            status: 'todo'
        })
        CREATE (s)-[:HAS_TASK]->(t)
    """)

    yield store

    # Cleanup
    store.execute("MATCH (n:Epic) WHERE n.id STARTS WITH 'E-' DETACH DELETE n")
    store.execute("MATCH (n:Story) WHERE n.id STARTS WITH 'US-' DETACH DELETE n")
    store.execute("MATCH (n:Task) WHERE n.id STARTS WITH 'T-' DETACH DELETE n")
    store.close()


def test_developer_query_performance(neo4j_with_large_dataset):
    """Test that Developer query completes in <100ms."""
    query = Neo4jRBACQueries.get_context_for_developer("T-101-1")

    start = time.perf_counter()
    result = neo4j_with_large_dataset.query(query, {"task_id": "T-101-1"})
    duration_ms = (time.perf_counter() - start) * 1000

    assert len(result) == 1
    assert duration_ms < 100, f"Query took {duration_ms:.2f}ms (expected <100ms)"


def test_architect_query_performance(neo4j_with_large_dataset):
    """Test that Architect query completes in <200ms."""
    query = Neo4jRBACQueries.get_context_for_architect("T-101-1")

    start = time.perf_counter()
    result = neo4j_with_large_dataset.query(query, {"task_id": "T-101-1"})
    duration_ms = (time.perf_counter() - start) * 1000

    assert len(result) == 1
    assert duration_ms < 200, f"Query took {duration_ms:.2f}ms (expected <200ms)"


def test_po_query_performance(neo4j_with_large_dataset):
    """Test that PO query (largest) completes in <500ms."""
    query = Neo4jRBACQueries.get_context_for_po(epic_id="E-1", story_id="US-101", task_id="T-101-1")

    start = time.perf_counter()
    result = neo4j_with_large_dataset.query(query, {"task_id": "T-101-1"})
    duration_ms = (time.perf_counter() - start) * 1000

    assert len(result) == 1
    assert duration_ms < 500, f"Query took {duration_ms:.2f}ms (expected <500ms)"


@pytest.mark.benchmark
def test_query_scalability(neo4j_with_large_dataset):
    """Benchmark queries with increasing dataset sizes."""
    results = {}

    for num_tasks in [10, 100, 1000]:
        query = Neo4jRBACQueries.get_context_for_architect("T-101-1")

        start = time.perf_counter()
        neo4j_with_large_dataset.query(query, {"task_id": "T-101-1"})
        duration_ms = (time.perf_counter() - start) * 1000

        results[num_tasks] = duration_ms

    # Verify O(log n) or O(1) performance (not O(n))
    # With indexes, query time should not scale linearly
    assert results[1000] < results[100] * 5, "Query performance degrades linearly (missing indexes?)"
```

**File:** `core/context/tests/security/test_rbac_security.py`

```python
"""Security tests for RBAC L3 data access control."""

import pytest
from core.context.usecases.get_role_based_context_usecase import GetRoleBasedContextUseCase


def test_developer_cannot_bypass_restrictions():
    """Test that Developer cannot access other tasks by manipulating queries."""
    # TODO: Implement security tests
    # - Try to inject task IDs in filters
    # - Try to access other stories via graph traversal
    # - Verify no data leaks via decisions
    pass


def test_column_filtering_is_enforced():
    """Test that column filtering cannot be bypassed."""
    # TODO: Implement
    # - Verify business_notes is NEVER returned to Developer
    # - Test with malicious column names
    pass


def test_audit_logging_cannot_be_disabled():
    """Test that audit logging is mandatory."""
    # TODO: Implement
    # - Verify all GetRoleBasedContextUseCase calls are logged
    # - Test log tampering detection
    pass


def test_po_role_cannot_be_spoofed():
    """Test that PO role requires proper authentication."""
    # TODO: Implement (depends on authentication system)
    pass
```

**Deliverables:**
- [ ] 25-35 unit tests (>90% coverage)
- [ ] 10-15 integration tests (Neo4j queries)
- [ ] 5-10 performance tests (query benchmarks)
- [ ] 5-10 security tests (bypass attempts)
- [ ] All tests passing

**Estimated Time:** 4-6 hours

---

### **PHASE 3: Integration & Documentation**

#### Task 1: Update Orchestrator

**File:** `services/orchestrator/application/usecases/execute_agent_task_usecase.py`

Update to include `role` when calling Context Service:

```python
# Before:
context = await self.context_service.GetContext(
    story_id=task.story_id,
    task_id=task.task_id,
)

# After:
context = await self.context_service.GetContext(
    story_id=task.story_id,
    task_id=task.task_id,
    role=agent.role,  # ← Pass agent role
)
```

#### Task 2: Update Context Service gRPC Handler

**File:** `services/context/server.py`

```python
async def GetContext(self, request, context):
    """Get context filtered by role (RBAC L3)."""
    try:
        # Use GetRoleBasedContextUseCase instead of SessionRehydrationUseCase
        filtered_context = self.get_role_based_context_usecase.execute(
            story_id=request.story_id,
            task_id=request.task_id if request.task_id else None,
            role=request.role,
            include_audit=True,
        )

        # Convert to protobuf response
        return context_pb2.GetContextResponse(
            context=json.dumps(filtered_context),
            token_count=len(json.dumps(filtered_context).split()),
            scopes=filtered_context.get("scopes", []),
            version=self._generate_version_hash(filtered_context),
        )
    except ValueError as e:
        logger.warning(f"Invalid GetContext request: {e}")
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
    except Exception as e:
        logger.error(f"GetContext failed: {e}")
        context.abort(grpc.StatusCode.INTERNAL, "Internal error")
```

#### Task 3: Update Documentation

**File:** `docs/architecture/RBAC_DATA_ACCESS_CONTROL.md`

Update with:
- Epic → Story → Task hierarchy
- Visibility matrix (from YAML)
- Column filtering rules
- Performance benchmarks
- Security audit results

**File:** `docs/architecture/decisions/2025-11-07/ADR_RBAC_L3.md`

Create ADR documenting:
- Decision to use YAML-based configuration
- Rationale for Case→Story, Subtask→Task refactor
- Addition of Epic entity
- PO role with full access
- Performance requirements (<100ms for Developer queries)

**Deliverables:**
- [ ] Orchestrator updated to pass role
- [ ] Context Service gRPC handler updated
- [ ] Documentation updated
- [ ] ADR created

**Estimated Time:** 2-3 hours

---

## 📊 **SUMMARY**

| Phase | Tasks | Estimated Time | Status |
|-------|-------|----------------|--------|
| **Phase 0: Model Refactor** | 5 tasks | 3-4 hours | ⏳ Pending |
| **Phase 1: RBAC L3 Core** | 8 tasks | 4-6 hours | ⏳ Pending |
| **Phase 2: Testing** | 4 test suites | 4-6 hours | ⏳ Pending |
| **Phase 3: Integration & Docs** | 3 tasks | 2-3 hours | ⏳ Pending |
| **TOTAL** | 20 tasks | **13-19 hours** | ⏳ Pending |

---

## ✅ **SUCCESS CRITERIA**

1. ✅ Model unified: `Case`→`Story`, `Subtask`→`Task`, `Epic` added
2. ✅ YAML configuration files created and loaded
3. ✅ Developer CANNOT see other tasks
4. ✅ Architect CAN see entire Epic
5. ✅ PO CAN see everything
6. ✅ Column filtering enforced (`business_notes` hidden from Developer)
7. ✅ All queries complete in <100ms (Developer), <200ms (Architect), <500ms (PO)
8. ✅ >90% unit test coverage
9. ✅ Integration tests passing
10. ✅ Security audit passed (no data leaks)
11. ✅ Audit logging working
12. ✅ Documentation complete

---

## 🚀 **NEXT STEPS**

1. **Architect approval** of this plan
2. **Start Phase 0** (Model Refactor) - CRITICAL FIRST
3. **Create branch:** `feature/rbac-l3-data-access`
4. **Commit incrementally** after each task
5. **Run tests** after each phase

---

**Ready to start?** Confirm this plan and I'll begin with Phase 0 Task 1 (Rename Case→Story). 🎯

