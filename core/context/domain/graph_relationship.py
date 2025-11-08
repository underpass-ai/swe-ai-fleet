# core/context/domain/graph_relationship.py
from __future__ import annotations

from dataclasses import dataclass

from .entity_ids.decision_id import DecisionId
from .entity_ids.plan_id import PlanId
from .entity_ids.story_id import StoryId
from .entity_ids.task_id import TaskId
from .graph_label import GraphLabel
from .graph_relation_type import GraphRelationType


@dataclass(frozen=True)
class GraphRelationship:
    """Domain model representing a relationship between entities in the context graph.

    This model encapsulates the structure and properties of relationships
    between different entities in the graph database.

    This is a pure domain value object. Use GraphRelationshipMapper in infrastructure
    layer to convert to Neo4j-specific formats (Cypher, properties dict, etc).

    Note: Uses Value Objects for IDs to prevent primitive obsession anti-pattern.
    """

    src_id: str  # String representation after extraction from Value Object
    rel_type: GraphRelationType
    dst_id: str  # String representation after extraction from Value Object
    src_labels: list[GraphLabel]
    dst_labels: list[GraphLabel]

    @staticmethod
    def affects_relationship(decision_id: DecisionId, task_id: TaskId) -> GraphRelationship:
        """Create an AFFECTS relationship between a decision and task (formerly subtask).

        Args:
            decision_id: DecisionId value object
            task_id: TaskId value object

        Returns:
            GraphRelationship with AFFECTS type
        """
        return GraphRelationship(
            src_id=decision_id.to_string(),
            rel_type=GraphRelationType.AFFECTS,
            dst_id=task_id.to_string(),
            src_labels=[GraphLabel.DECISION],
            dst_labels=[GraphLabel.TASK],
        )

    @staticmethod
    def has_plan_relationship(story_id: StoryId, plan_id: PlanId) -> GraphRelationship:
        """Create a HAS_PLAN relationship between a Story and plan (formerly case/plan).

        Args:
            story_id: StoryId value object
            plan_id: PlanId value object

        Returns:
            GraphRelationship with HAS_PLAN type
        """
        return GraphRelationship(
            src_id=story_id.to_string(),
            rel_type=GraphRelationType.HAS_PLAN,
            dst_id=plan_id.to_string(),
            src_labels=[GraphLabel.STORY],
            dst_labels=[GraphLabel.PLAN_VERSION],
        )

    @staticmethod
    def has_task_relationship(plan_id: PlanId, task_id: TaskId) -> GraphRelationship:
        """Create a HAS_TASK relationship between a plan and task (formerly has_subtask).

        Args:
            plan_id: PlanId value object
            task_id: TaskId value object

        Returns:
            GraphRelationship with HAS_TASK type
        """
        return GraphRelationship(
            src_id=plan_id.to_string(),
            rel_type=GraphRelationType.HAS_TASK,
            dst_id=task_id.to_string(),
            src_labels=[GraphLabel.PLAN_VERSION],
            dst_labels=[GraphLabel.TASK],
        )
