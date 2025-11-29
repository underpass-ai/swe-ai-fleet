"""Mapper: Domain Project ↔ Neo4j node properties."""

from datetime import datetime
from typing import Any

from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus


class ProjectNeo4jMapper:
    """
    Mapper: Convert domain Project to/from Neo4j node properties.

    Infrastructure Layer Responsibility:
    - Domain entities should not know about Neo4j format
    - Conversions live in dedicated mappers (Hexagonal Architecture)

    Following the same pattern as Story nodes for consistency.
    """

    @staticmethod
    def to_graph_properties(project: Project) -> dict[str, Any]:
        """
        Convert domain Project to Neo4j node properties.

        Args:
            project: Domain Project entity.

        Returns:
            Dict with properties for Neo4j node (minimal properties for graph structure).
        """
        return {
            "id": project.project_id.value,  # Neo4j uses 'id' for unique constraint
            "project_id": project.project_id.value,  # Also store for clarity
            "name": project.name,
            "status": project.status.value,  # Enum string value
            "created_at": project.created_at.isoformat(),  # ISO format for Neo4j
            "updated_at": project.updated_at.isoformat(),
        }

    @staticmethod
    def from_node_data(node_data: dict[str, Any]) -> Project:
        """
        Convert Neo4j node data to domain Project.

        Args:
            node_data: Neo4j node dictionary (from MATCH query result).

        Returns:
            Domain Project entity.

        Raises:
            ValueError: If data is invalid or missing required fields.
        """
        if not node_data:
            raise ValueError("Cannot create Project from empty node data")

        # Extract node properties (Neo4j returns {prop: value} dict)
        props = node_data.get("properties", {}) if "properties" in node_data else node_data

        # Get required fields
        project_id_str = props.get("project_id") or props.get("id")
        if not project_id_str:
            raise ValueError("Missing required field: project_id or id")

        name = props.get("name", "")
        if not name:
            raise ValueError("Missing required field: name")

        # Parse timestamps
        created_at_str = props.get("created_at", "")
        updated_at_str = props.get("updated_at", "")

        if not created_at_str or not updated_at_str:
            raise ValueError("Missing required fields: created_at or updated_at")

        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))

        # Optional fields with defaults
        description = props.get("description", "")
        status_str = props.get("status", ProjectStatus.ACTIVE.value)
        owner = props.get("owner", "")

        return Project(
            project_id=ProjectId(project_id_str),
            name=name,
            description=description,
            status=ProjectStatus(status_str),
            owner=owner,
            created_at=created_at,
            updated_at=updated_at,
        )




