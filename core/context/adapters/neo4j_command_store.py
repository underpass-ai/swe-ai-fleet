# core/context/adapters/neo4j_command_store.py
"""Neo4j command store adapter - Infrastructure layer.

Implements GraphCommandPort using Neo4j driver for write operations.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from typing import Any

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable, TransientError

from core.context.domain.epic import Epic
from core.context.domain.graph_label import GraphLabel
from core.context.domain.graph_relationship import GraphRelationship
from core.context.domain.neo4j_config import Neo4jConfig
from core.context.domain.phase_transition import PhaseTransition
from core.context.domain.plan_approval import PlanApproval
from core.context.domain.plan_version import PlanVersion
from core.context.domain.project import Project
from core.context.domain.story import Story
from core.context.domain.task import Task
from core.context.infrastructure.mappers.epic_mapper import EpicMapper
from core.context.infrastructure.mappers.graph_relationship_mapper import GraphRelationshipMapper
from core.context.infrastructure.mappers.plan_version_mapper import PlanVersionMapper
from core.context.infrastructure.mappers.project_mapper import ProjectMapper
from core.context.infrastructure.mappers.story_mapper import StoryMapper
from core.context.ports.graph_command_port import GraphCommandPort


class Neo4jCommandStore(GraphCommandPort):
    """Neo4j implementation of GraphCommandPort for write operations.

    This adapter receives configuration via dependency injection.
    Follows fail-fast principle: if Neo4j is not available, import fails immediately.
    """

    def __init__(self, config: Neo4jConfig, driver: Driver | None = None) -> None:
        """Initialize Neo4j command store with injected configuration.

        Args:
            config: Neo4jConfig domain value object (REQUIRED)
            driver: Optional pre-configured driver (for testing)

        Raises:
            ValueError: If config is invalid
        """
        self._config = config
        self._driver = driver or GraphDatabase.driver(
            config.uri,
            auth=(config.user, config.password)
        )

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        self._driver.close()

    def _session(self) -> Session:
        """Get a Neo4j session.

        Returns:
            Neo4j session with configured database
        """
        if self._config.database:
            return self._driver.session(database=self._config.database)
        return self._driver.session()

    def _retry_write(self, fn, *args, **kwargs):
        """Retry write operation with exponential backoff.

        Args:
            fn: Function to retry
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            ServiceUnavailable: If Neo4j is not available after retries
            TransientError: If transient error persists after retries
        """
        attempt = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except (ServiceUnavailable, TransientError):
                if attempt >= self._config.max_retries:
                    raise  # Fail fast on last attempt
                time.sleep(self._config.base_backoff_s * (2**attempt))
                attempt += 1

    def init_constraints(self, labels: list[GraphLabel]) -> None:
        """Initialize unique constraints for node labels.

        Creates unique constraints on 'id' property for each label.

        Args:
            labels: List of GraphLabel enums
        """
        cyphers = [
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label.value}) REQUIRE n.id IS UNIQUE"
            for label in labels
        ]

        def _tx(tx):
            for cypher in cyphers:
                tx.run(cypher)

        with self._session() as session:
            self._retry_write(session.execute_write, _tx)

    def save_project(self, project: Project) -> None:
        """Save Project entity to Neo4j (root of hierarchy).

        Args:
            project: Project domain entity
        """
        props = ProjectMapper.to_graph_properties(project)
        self.upsert_entity(
            label=GraphLabel.PROJECT.value,
            id=project.project_id.to_string(),
            properties=props
        )

    def save_epic(self, epic: Epic) -> None:
        """Save Epic entity to Neo4j.

        Domain Invariant: Epic MUST have project_id.

        Args:
            epic: Epic domain entity with project_id

        Raises:
            ValueError: If epic.project_id is empty (domain invariant violation)
        """
        # Domain entity validation already enforces project_id is present
        # (Epic.__post_init__ raises ValueError if project_id is empty)
        props = EpicMapper.to_graph_properties(epic)
        self.upsert_entity(
            label=GraphLabel.EPIC.value,
            id=epic.epic_id.to_string(),
            properties=props
        )

    def save_story(self, story: Story) -> None:
        """Save Story entity to Neo4j.

        Domain Invariant: Story MUST have epic_id.

        Args:
            story: Story domain entity with epic_id

        Raises:
            ValueError: If story.epic_id is empty (domain invariant violation)
        """
        # Domain entity validation already enforces epic_id is present
        # (Story.__post_init__ raises ValueError if epic_id is empty)
        props = StoryMapper.to_graph_properties(story)
        self.upsert_entity(
            label=GraphLabel.STORY.value,
            id=story.story_id.to_string(),
            properties=props
        )

    def save_task(self, task: Task) -> None:
        """Save Task entity to Neo4j.

        Args:
            task: Task domain entity
        """
        props = task.to_graph_properties()
        self.upsert_entity(
            label=GraphLabel.TASK.value,
            id=task.task_id.to_string(),
            properties=props
        )

    def save_plan_version(self, plan: PlanVersion) -> None:
        """Save PlanVersion entity to Neo4j.

        Args:
            plan: PlanVersion domain entity
        """
        props = PlanVersionMapper.to_graph_properties(plan)
        self.upsert_entity(
            label=GraphLabel.PLAN_VERSION.value,
            id=plan.plan_id.to_string(),
            properties=props
        )

    def save_plan_approval(self, approval: PlanApproval) -> None:
        """Save PlanApproval entity to Neo4j (audit trail).

        Args:
            approval: PlanApproval domain entity
        """
        props = approval.to_graph_properties()
        self.upsert_entity(
            label=approval.get_graph_label(),
            id=approval.get_entity_id(),
            properties=props
        )

    def save_phase_transition(self, transition: PhaseTransition) -> None:
        """Save PhaseTransition entity to Neo4j (audit trail).

        Args:
            transition: PhaseTransition domain entity
        """
        props = transition.to_graph_properties()
        self.upsert_entity(
            label=transition.get_graph_label(),
            id=transition.get_entity_id(),
            properties=props
        )

    def create_relationship(self, relationship: GraphRelationship) -> None:
        """Create relationship between entities.

        Args:
            relationship: GraphRelationship domain value object
        """
        cypher = GraphRelationshipMapper.to_cypher_pattern(relationship)
        params = GraphRelationshipMapper.to_cypher_params(relationship)

        with self._session() as session:
            self._retry_write(
                session.execute_write,
                lambda tx: tx.run(cypher, **params)
            )

    def upsert_entity(
        self,
        label: str,
        id: str,
        properties: Mapping[str, Any] | None = None
    ) -> None:
        """Upsert an entity with a single label.

        Args:
            label: Neo4j label (e.g., "Story", "Task")
            id: Entity identifier
            properties: Optional entity properties
        """
        props = dict(properties or {})
        props["id"] = id
        cypher = f"MERGE (n:{label} {{id:$id}}) SET n += $props"

        with self._session() as session:
            self._retry_write(
                session.execute_write,
                lambda tx: tx.run(cypher, id=id, props=props)
            )

    def upsert_entity_multi(
        self,
        labels: Iterable[str],
        id: str,
        properties: Mapping[str, Any] | None = None
    ) -> None:
        """Upsert an entity with multiple labels.

        Args:
            labels: List of Neo4j labels
            id: Entity identifier
            properties: Optional entity properties

        Raises:
            ValueError: If labels list is empty
        """
        labels_list = list(labels)
        if not labels_list:
            raise ValueError("labels must be non-empty")

        label_expr = ":" + ":".join(sorted(set(labels_list)))
        props = dict(properties or {})
        props["id"] = id
        cypher = f"MERGE (n{label_expr} {{id:$id}}) SET n += $props"

        with self._session() as session:
            self._retry_write(
                session.execute_write,
                lambda tx: tx.run(cypher, id=id, props=props)
            )

    def relate(
        self,
        src_id: str,
        rel_type: str,
        dst_id: str,
        *,
        src_labels: Iterable[str] | None = None,
        dst_labels: Iterable[str] | None = None,
        properties: Mapping[str, Any] | None = None,
    ) -> None:
        """Create a relationship between two entities.

        Args:
            src_id: Source entity ID
            rel_type: Relationship type (e.g., "HAS_PLAN", "AFFECTS")
            dst_id: Destination entity ID
            src_labels: Optional source entity labels
            dst_labels: Optional destination entity labels
            properties: Optional relationship properties
        """
        src_label_expr = ":" + ":".join(sorted(set(src_labels))) if src_labels else ""
        dst_label_expr = ":" + ":".join(sorted(set(dst_labels))) if dst_labels else ""

        cypher = (
            f"MATCH (a{src_label_expr} {{id:$src}}), (b{dst_label_expr} {{id:$dst}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) SET r += $props"
        )

        with self._session() as session:
            self._retry_write(
                session.execute_write,
                lambda tx: tx.run(cypher, src=src_id, dst=dst_id, props=dict(properties or {})),
            )

    def execute_write(self, cypher: str, params: Mapping[str, Any] | None = None) -> Any:
        """Execute a raw Cypher write query.

        Args:
            cypher: The Cypher query to execute
            params: Query parameters

        Returns:
            Query result records
        """
        params = params or {}

        def _tx(tx):
            result = tx.run(cypher, params)
            return list(result)

        with self._session() as session:
            return self._retry_write(session.execute_write, _tx)
