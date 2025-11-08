"""Mapper for Epic entity - Infrastructure layer."""

from typing import Any

from core.context.domain.epic import Epic
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.epic_status import EpicStatus


class EpicMapper:
    """Mapper for Epic entity conversions."""

    @staticmethod
    def from_event_payload(payload: dict[str, Any]) -> Epic:
        """Create Epic from event payload.

        Args:
            payload: Event data with {epic_id, title, description?, status?, created_at_ms?}

        Returns:
            Epic domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If data is invalid
        """
        # Parse status string to EpicStatus enum (fail-fast if invalid)
        status_str = payload.get("status", "active")
        try:
            status = EpicStatus(status_str)
        except ValueError as e:
            raise ValueError(
                f"Invalid epic status '{status_str}'. "
                f"Must be one of: {[s.value for s in EpicStatus]}"
            ) from e

        return Epic(
            epic_id=EpicId(value=payload["epic_id"]),
            title=payload["title"],
            description=payload.get("description", ""),
            status=status,
            created_at_ms=int(payload.get("created_at_ms", 0)),
        )

    @staticmethod
    def from_neo4j_node(node: Any) -> Epic:
        """Create Epic from Neo4j node properties.

        Args:
            node: Neo4j node with epic properties

        Returns:
            Epic domain entity

        Raises:
            ValueError: If node data is invalid
        """
        props = dict(node)

        # Parse status string to EpicStatus enum (fail-fast if invalid)
        status_str = props.get("status", "active")
        try:
            status = EpicStatus(status_str)
        except ValueError as e:
            raise ValueError(
                f"Invalid epic status '{status_str}' in Neo4j node. "
                f"Must be one of: {[s.value for s in EpicStatus]}"
            ) from e

        return Epic(
            epic_id=EpicId(value=props["epic_id"]),
            title=props["title"],
            description=props.get("description", ""),
            status=status,
            created_at_ms=int(props.get("created_at_ms", 0)),
        )

    @staticmethod
    def to_dict(epic: Epic) -> dict[str, Any]:
        """Convert Epic to dictionary representation.

        Args:
            epic: Epic domain entity

        Returns:
            Dictionary with primitive types
        """
        return {
            "epic_id": epic.epic_id.to_string(),
            "title": epic.title,
            "description": epic.description,
            "status": epic.status.value,  # Enum to string
            "created_at_ms": epic.created_at_ms,
        }

    @staticmethod
    def to_graph_properties(epic: Epic) -> dict[str, Any]:
        """Convert Epic to Neo4j node properties.

        Args:
            epic: Epic domain entity

        Returns:
            Dictionary suitable for Neo4j
        """
        return epic.to_graph_properties()

