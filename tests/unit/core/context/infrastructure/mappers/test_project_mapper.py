"""Unit tests for ProjectMapper."""

import pytest
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.project import Project
from core.context.domain.project_status import ProjectStatus
from core.context.infrastructure.mappers.project_mapper import ProjectMapper


class TestProjectMapper:
    """Test suite for ProjectMapper."""

    def test_from_neo4j_node_happy_path(self) -> None:
        """Test converting Neo4j node to Project entity."""
        node = {
            "project_id": "PROJ-001",
            "name": "SWE Platform v1",
            "description": "Complete platform",
            "status": "in_progress",
            "owner": "tirso",
            "created_at_ms": 1699564800000,
        }

        project = ProjectMapper.from_neo4j_node(node)

        assert project.project_id.to_string() == "PROJ-001"
        assert project.name == "SWE Platform v1"
        assert project.status == ProjectStatus.IN_PROGRESS
        assert project.owner == "tirso"

    def test_from_dict_happy_path(self) -> None:
        """Test converting dict to Project entity."""
        data = {
            "project_id": "PROJ-002",
            "name": "Test Project",
            "description": "Test description",
            "status": "active",
            "owner": "test_owner",
            "created_at_ms": 1699568400000,
        }

        project = ProjectMapper.from_dict(data)

        assert project.project_id.to_string() == "PROJ-002"
        assert project.name == "Test Project"
        assert project.status == ProjectStatus.ACTIVE

    def test_from_dict_minimal_fields(self) -> None:
        """Test converting dict with only required fields."""
        data = {
            "project_id": "PROJ-MIN",
            "name": "Minimal Project",
        }

        project = ProjectMapper.from_dict(data)

        assert project.project_id.to_string() == "PROJ-MIN"
        assert project.name == "Minimal Project"
        assert project.description == ""  # Default
        assert project.status == ProjectStatus.ACTIVE  # Default
        assert project.owner == ""  # Default

    def test_to_graph_properties(self) -> None:
        """Test converting Project to Neo4j properties."""
        project = Project(
            project_id=ProjectId("PROJ-GRAPH"),
            name="Graph Test",
            description="Test description",
            status=ProjectStatus.PLANNING,
            owner="test_owner",
            created_at_ms=1699572000000,
        )

        props = ProjectMapper.to_graph_properties(project)

        assert props["project_id"] == "PROJ-GRAPH"
        assert props["name"] == "Graph Test"
        assert props["description"] == "Test description"
        assert props["status"] == "planning"
        assert props["owner"] == "test_owner"
        assert props["created_at_ms"] == "1699572000000"

    def test_to_dict(self) -> None:
        """Test converting Project to dictionary."""
        project = Project(
            project_id=ProjectId("PROJ-DICT"),
            name="Dict Test",
            description="Test",
            status=ProjectStatus.COMPLETED,
            owner="owner",
            created_at_ms=1699575600000,
        )

        data = ProjectMapper.to_dict(project)

        assert data["project_id"] == "PROJ-DICT"
        assert data["name"] == "Dict Test"
        assert data["status"] == "completed"
        assert data["owner"] == "owner"
        assert isinstance(data["created_at_ms"], str)

    def test_from_neo4j_node_with_invalid_status(self) -> None:
        """Test that invalid status raises ValueError."""
        node = {
            "project_id": "PROJ-BAD",
            "name": "Bad Status Project",
            "status": "invalid_status",  # Invalid
        }

        with pytest.raises(ValueError):
            ProjectMapper.from_neo4j_node(node)

    def test_from_dict_missing_required_field(self) -> None:
        """Test that missing project_id raises error."""
        data = {
            "name": "No ID Project",
        }

        with pytest.raises(KeyError):
            ProjectMapper.from_dict(data)

    def test_roundtrip_dict_conversion(self) -> None:
        """Test that Project → dict → Project preserves data."""
        original = Project(
            project_id=ProjectId("PROJ-ROUND"),
            name="Roundtrip Test",
            description="Test desc",
            status=ProjectStatus.ON_HOLD,
            owner="test",
            created_at_ms=1699579200000,
        )

        # Convert to dict
        data = ProjectMapper.to_dict(original)

        # Convert back to Project
        restored = ProjectMapper.from_dict(data)

        # Verify equality
        assert restored.project_id == original.project_id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.status == original.status
        assert restored.owner == original.owner
        # Note: created_at_ms might differ slightly due to string conversion

