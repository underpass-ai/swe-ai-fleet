"""Task domain entity - Represents a work item within a plan."""

from dataclasses import dataclass

from .entity_ids.plan_id import PlanId
from .entity_ids.task_id import TaskId
from .graph_label import GraphLabel
from .graph_relation_type import GraphRelationType
from .graph_relationship import GraphRelationship
from .task_status import TaskStatus
from .task_type import TaskType


@dataclass(frozen=True)
class Task:
    """Task domain entity (formerly Subtask).

    Represents a concrete work item that belongs to a Plan.
    Tasks are assigned to specific roles and have status tracking.
    """

    plan_id: PlanId
    task_id: TaskId
    title: str = ""
    type: TaskType = TaskType.DEVELOPMENT
    status: TaskStatus | None = None

    def __post_init__(self) -> None:
        """Validate task."""
        if not self.task_id.value or not self.task_id.value.strip():
            raise ValueError("Task ID cannot be empty")

    def get_relationship_to_plan(self) -> GraphRelationship:
        """Get the relationship from Task to Plan.

        Returns:
            GraphRelationship connecting Task→Plan
        """
        return GraphRelationship(
            src_id=self.task_id.to_string(),
            src_labels=[GraphLabel.TASK],
            rel_type=GraphRelationType.BELONGS_TO_PLAN,
            dst_id=self.plan_id.to_string(),
            dst_labels=[GraphLabel.PLAN_VERSION],
            properties=None,
        )

    def to_graph_properties(self) -> dict[str, str]:
        """Convert Task to Neo4j node properties.

        Returns:
            Dictionary of properties for Neo4j node
        """
        props = {
            "task_id": self.task_id.to_string(),
            "plan_id": self.plan_id.to_string(),
            "title": self.title,
            "type": self.type.value,
        }

        if self.status is not None:
            props["status"] = self.status.value

        return props

    def get_log_context(self) -> dict[str, str]:
        """Get structured logging context (Tell, Don't Ask).

        Returns:
            Dictionary with logging fields
        """
        return {
            "task_id": self.task_id.to_string(),
            "plan_id": self.plan_id.to_string(),
            "title": self.title,
        }

