"""Mapper for Project entity - Infrastructure layer.

Handles conversion between external formats (dict/JSON) and Project domain entity.
"""

from typing import Any

from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.project import Project
from core.context.domain.project_status import ProjectStatus


class ProjectMapper:
    """Mapper for Project entity conversions.

    This mapper handles conversions between:
    - External formats (dict, JSON, Neo4j properties)
    - Project domain entity

    Following DDD principles:
    - NO serialization methods in domain entity
    - ALL conversions live in infrastructure layer
    """

    @staticmethod
    def from_neo4j_node(node: dict[str, Any]) -> Project:
        """Create Project entity from Neo4j node data.

        Args:
            node: Neo4j node dictionary with project properties

        Returns:
            Project domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If project_id or status is invalid
        """
        return Project(
            project_id=ProjectId(value=node["project_id"]),
            name=node["name"],
            description=node.get("description", ""),
            status=ProjectStatus(node.get("status", "active")),
            owner=node.get("owner", ""),
            created_at_ms=int(node.get("created_at_ms", 0)),
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Project:
        """Create Project entity from dictionary.

        Args:
            data: Dictionary with project data

        Returns:
            Project domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If validation fails
        """
        return Project(
            project_id=ProjectId(value=data["project_id"]),
            name=data["name"],
            description=data.get("description", ""),
            status=ProjectStatus(data.get("status", "active")),
            owner=data.get("owner", ""),
            created_at_ms=int(data.get("created_at_ms", 0)),
        )

    @staticmethod
    def to_graph_properties(project: Project) -> dict[str, Any]:
        """Convert Project to properties suitable for Neo4j graph storage.

        Uses domain entity's to_graph_properties() method.

        Args:
            project: Project domain entity

        Returns:
            Dictionary with properties for Neo4j
        """
        # Domain entity already provides this method
        # Mapper just delegates to it
        return project.to_graph_properties()

    @staticmethod
    def to_dict(project: Project) -> dict[str, Any]:
        """Convert Project to dictionary (for Valkey/Redis storage).

        Args:
            project: Project domain entity

        Returns:
            Dictionary representation
        """
        return {
            "project_id": project.project_id.to_string(),
            "name": project.name,
            "description": project.description,
            "status": project.status.value,
            "owner": project.owner,
            "created_at_ms": str(project.created_at_ms),
        }

