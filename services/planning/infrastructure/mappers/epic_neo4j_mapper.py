"""Mapper: Domain Epic ↔ Neo4j node properties."""

from datetime import datetime
from typing import Any

from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.statuses.epic_status import EpicStatus


class EpicNeo4jMapper:
    """
    Mapper: Convert domain Epic to/from Neo4j node properties.

    Infrastructure Layer Responsibility:
    - Domain entities should not know about Neo4j format
    - Conversions live in dedicated mappers (Hexagonal Architecture)
    """

    @staticmethod
    def to_graph_properties(epic: Epic) -> dict[str, Any]:
        """
        Convert domain Epic to Neo4j node properties.

        Args:
            epic: Domain Epic entity.

        Returns:
            Dict with properties for Neo4j node.
        """
        return {
            "id": epic.epic_id.value,
            "epic_id": epic.epic_id.value,
            "project_id": epic.project_id.value,
            "name": epic.title,  # Epic uses 'title', unlike Project 'name'
            "status": epic.status.value,
            "created_at": epic.created_at.isoformat(),
            "updated_at": epic.updated_at.isoformat(),
        }

    @staticmethod
    def from_node_data(node_data: dict[str, Any]) -> Epic:
        """
        Convert Neo4j node data to domain Epic.

        Args:
            node_data: Neo4j node dictionary.

        Returns:
            Domain Epic entity.
        """
        if not node_data:
            raise ValueError("Cannot create Epic from empty node data")

        props = node_data.get("properties", {}) if "properties" in node_data else node_data

        epic_id_str = props.get("epic_id") or props.get("id")
        if not epic_id_str:
            raise ValueError("Missing required field: epic_id or id")

        # project_id is usually a relationship, but we store it as prop for convenience too
        project_id_str = props.get("project_id", "")
        if not project_id_str:
             # If not in props, might need to be passed separately or inferred
             # For now, require it in props as we store it there
             pass

        title = props.get("name", "") or props.get("title", "")
        if not title:
            raise ValueError("Missing required field: name/title")

        created_at_str = props.get("created_at", "")
        updated_at_str = props.get("updated_at", "")

        if not created_at_str or not updated_at_str:
            raise ValueError("Missing required timestamps")

        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))

        status_str = props.get("status")
        if not status_str:
            raise ValueError("Missing required field: status")

        description = props.get("description", "")

        # NOTE: This reconstruction might be incomplete if project_id is missing
        # or if we need other fields not in graph.
        # Usually we rehydrate from Valkey. This mapper is for graph queries mostly.

        # Assuming ProjectId is required for Epic constructor
        from planning.domain.value_objects.identifiers.project_id import ProjectId

        return Epic(
            epic_id=EpicId(epic_id_str),
            project_id=ProjectId(project_id_str) if project_id_str else ProjectId("unknown"), # Placeholder?
            title=title,
            description=description,
            status=EpicStatus(status_str),
            created_at=created_at,
            updated_at=updated_at,
        )

