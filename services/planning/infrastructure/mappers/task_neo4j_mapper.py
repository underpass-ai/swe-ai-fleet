"""Mapper: Domain Task ↔ Neo4j node properties."""

from datetime import datetime
from typing import Any

from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType


class TaskNeo4jMapper:
    """
    Mapper: Convert domain Task to/from Neo4j node properties.

    Infrastructure Layer Responsibility:
    - Domain entities should not know about Neo4j format
    - Conversions live in dedicated mappers (Hexagonal Architecture)

    Following the same pattern as Story and Project nodes for consistency.
    """

    @staticmethod
    def to_graph_properties(task: Task) -> dict[str, Any]:
        """
        Convert domain Task to Neo4j node properties.

        Args:
            task: Domain Task entity.

        Returns:
            Dict with properties for Neo4j node (minimal properties for graph structure).
        """
        props: dict[str, Any] = {
            "id": task.task_id.value,  # Neo4j uses 'id' for unique constraint
            "task_id": task.task_id.value,  # Also store for clarity
            "status": str(task.status),  # TaskStatus enum string value
            "type": str(task.type),  # TaskType enum string value
        }

        return props

    @staticmethod
    def _extract_properties(node_data: dict[str, Any]) -> dict[str, Any]:
        """Extract properties from Neo4j node data."""
        if not node_data:
            raise ValueError("Cannot create Task from empty node_data")
        return node_data.get("properties", {}) if "properties" in node_data else node_data

    @staticmethod
    def _require_field(props: dict[str, Any], field_name: str, error_msg: str | None = None) -> str:
        """Extract and validate required field from props."""
        value = props.get(field_name)
        if not value:
            msg = error_msg or f"Missing required field: {field_name}"
            raise ValueError(msg)
        return value

    @staticmethod
    def _parse_task_status(status_str: str) -> TaskStatus:
        """Parse TaskStatus enum from string."""
        try:
            return TaskStatus(status_str)
        except ValueError as e:
            raise ValueError(f"Invalid task status: {status_str}") from e

    @staticmethod
    def _parse_task_type(type_str: str) -> TaskType:
        """Parse TaskType enum from string."""
        try:
            return TaskType(type_str)
        except ValueError as e:
            raise ValueError(f"Invalid task type: {type_str}") from e

    @staticmethod
    def _parse_datetime(dt_str: str, field_name: str) -> datetime:
        """Parse datetime from ISO format string."""
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid {field_name} format: {dt_str}") from e

    @staticmethod
    def _build_task_kwargs(
        props: dict[str, Any],
        task_id_str: str,
        story_id_str: str,
        title: str,
        created_at: datetime,
        updated_at: datetime,
        task_type: TaskType,
        status: TaskStatus,
    ) -> dict[str, Any]:
        """Build kwargs dict for Task constructor."""
        task_kwargs: dict[str, Any] = {
            "task_id": TaskId(task_id_str),
            "story_id": StoryId(story_id_str),
            "title": title,
            "created_at": created_at,
            "updated_at": updated_at,
            "type": task_type,
            "status": status,
        }

        plan_id_str = props.get("plan_id")
        if plan_id_str and plan_id_str != "NO PLAN ID":
            task_kwargs["plan_id"] = PlanId(plan_id_str)

        if "description" in props:
            task_kwargs["description"] = props["description"]

        if "assigned_to" in props:
            task_kwargs["assigned_to"] = props["assigned_to"]

        if "estimated_hours" in props:
            task_kwargs["estimated_hours"] = int(props["estimated_hours"])

        if "priority" in props:
            task_kwargs["priority"] = int(props["priority"])

        return task_kwargs

    @staticmethod
    def from_node_data(node_data: dict[str, Any]) -> Task:
        """
        Convert Neo4j node data to domain Task.

        Note: This creates a MINIMAL Task with only graph properties.
        Neo4j stores: id, task_id, status, type
        Missing fields (title, description, etc.) use defaults.

        For full Task details, use StorageAdapter.get_task(task_id) which retrieves from Valkey.

        Args:
            node_data: Neo4j node data (from MATCH query).
                     Can include 'properties' key or flat dict.
                     Should include 'story_id' if available from relationship.

        Returns:
            Domain Task entity (minimal - use StorageAdapter.get_task() for full details).

        Raises:
            ValueError: If node_data is invalid or missing required fields.
        """
        props = TaskNeo4jMapper._extract_properties(node_data)

        task_id_str = props.get("task_id") or props.get("id")
        if not task_id_str:
            raise ValueError("Missing required field: task_id or id")

        story_id_str = TaskNeo4jMapper._require_field(
            props,
            "story_id",
            "Missing required field: story_id. "
            "Include story_id in query result or relationship data.",
        )

        status_str = TaskNeo4jMapper._require_field(props, "status")
        type_str = TaskNeo4jMapper._require_field(props, "type")

        status = TaskNeo4jMapper._parse_task_status(status_str)
        task_type = TaskNeo4jMapper._parse_task_type(type_str)

        title = TaskNeo4jMapper._require_field(
            props,
            "title",
            "Missing required field: title. "
            "Neo4j only stores minimal properties. "
            "Include title in query or use StorageAdapter.get_task() for full Task.",
        )

        created_at_str = TaskNeo4jMapper._require_field(
            props,
            "created_at",
            "Missing required field: created_at. "
            "Neo4j only stores minimal properties. "
            "Include created_at in query or use StorageAdapter.get_task() for full Task.",
        )

        updated_at_str = TaskNeo4jMapper._require_field(
            props,
            "updated_at",
            "Missing required field: updated_at. "
            "Neo4j only stores minimal properties. "
            "Include updated_at in query or use StorageAdapter.get_task() for full Task.",
        )

        created_at = TaskNeo4jMapper._parse_datetime(created_at_str, "created_at")
        updated_at = TaskNeo4jMapper._parse_datetime(updated_at_str, "updated_at")

        task_kwargs = TaskNeo4jMapper._build_task_kwargs(
            props,
            task_id_str,
            story_id_str,
            title,
            created_at,
            updated_at,
            task_type,
            status,
        )

        return Task(**task_kwargs)

