"""Unit tests for ProjectNeo4jMapper."""

from datetime import UTC, datetime

import pytest
from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.infrastructure.mappers.project_neo4j_mapper import ProjectNeo4jMapper


def test_to_graph_properties_happy_path():
    """Test Project to Neo4j properties conversion (happy path)."""
    now = datetime.now(UTC)

    project = Project(
        project_id=ProjectId("PROJ-123"),
        name="Test Project",
        description="Test description",
        status=ProjectStatus.ACTIVE,
        owner="test-owner",
        created_at=now,
        updated_at=now,
    )

    result = ProjectNeo4jMapper.to_graph_properties(project)

    assert isinstance(result, dict)
    assert result["id"] == "PROJ-123"
    assert result["project_id"] == "PROJ-123"
    assert result["name"] == "Test Project"
    assert result["status"] == "active"
    assert result["created_at"] == now.isoformat()
    assert result["updated_at"] == now.isoformat()


def test_to_graph_properties_minimal_fields():
    """Test to_graph_properties with minimal required fields."""
    now = datetime.now(UTC)

    project = Project(
        project_id=ProjectId("PROJ-MIN"),
        name="Minimal Project",
        created_at=now,
        updated_at=now,
        # Optional fields use defaults
    )

    result = ProjectNeo4jMapper.to_graph_properties(project)

    assert result["id"] == "PROJ-MIN"
    assert result["name"] == "Minimal Project"
    assert result["status"] == "active"  # Default status
    assert result["created_at"] == now.isoformat()


def test_to_graph_properties_all_statuses():
    """Test to_graph_properties with different status values."""
    now = datetime.now(UTC)

    statuses = [
        ProjectStatus.ACTIVE,
        ProjectStatus.PLANNING,
        ProjectStatus.IN_PROGRESS,
        ProjectStatus.COMPLETED,
        ProjectStatus.ARCHIVED,
        ProjectStatus.CANCELLED,
    ]

    for status in statuses:
        project = Project(
            project_id=ProjectId(f"PROJ-{status.value}"),
            name=f"Project {status.value}",
            status=status,
            created_at=now,
            updated_at=now,
        )

        result = ProjectNeo4jMapper.to_graph_properties(project)
        assert result["status"] == status.value


def test_from_node_data_happy_path():
    """Test Neo4j node data to Project conversion (happy path)."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    node_data = {
        "properties": {
            "id": "PROJ-456",
            "project_id": "PROJ-456",
            "name": "From Node Project",
            "status": "active",
            "description": "Test description",
            "owner": "node-owner",
            "created_at": now_iso,
            "updated_at": now_iso,
        }
    }

    project = ProjectNeo4jMapper.from_node_data(node_data)

    assert isinstance(project, Project)
    assert project.project_id.value == "PROJ-456"
    assert project.name == "From Node Project"
    assert project.description == "Test description"
    assert project.status == ProjectStatus.ACTIVE
    assert project.owner == "node-owner"
    assert project.created_at == now
    assert project.updated_at == now


def test_from_node_data_without_properties_key():
    """Test from_node_data when properties are at root level."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    node_data = {
        "id": "PROJ-789",
        "project_id": "PROJ-789",
        "name": "Direct Properties Project",
        "status": "completed",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    project = ProjectNeo4jMapper.from_node_data(node_data)

    assert project.project_id.value == "PROJ-789"
    assert project.name == "Direct Properties Project"
    assert project.status == ProjectStatus.COMPLETED


def test_from_node_data_uses_id_if_project_id_missing():
    """Test from_node_data falls back to 'id' if 'project_id' is missing."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    node_data = {
        "id": "PROJ-FALLBACK",
        "name": "Fallback Project",
        "status": "planning",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    project = ProjectNeo4jMapper.from_node_data(node_data)

    assert project.project_id.value == "PROJ-FALLBACK"


def test_from_node_data_with_optional_fields_defaults():
    """Test from_node_data uses defaults for optional fields."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    node_data = {
        "id": "PROJ-OPTIONAL",
        "project_id": "PROJ-OPTIONAL",
        "name": "Optional Fields Project",
        "created_at": now_iso,
        "updated_at": now_iso,
        # Missing: description, status, owner
    }

    project = ProjectNeo4jMapper.from_node_data(node_data)

    assert project.description == ""  # Default
    assert project.status == ProjectStatus.ACTIVE  # Default
    assert project.owner == ""  # Default


def test_from_node_data_with_z_suffix_in_timestamps():
    """Test from_node_data handles timestamps with Z suffix."""
    now = datetime.now(UTC)
    now_iso_z = now.isoformat().replace("+00:00", "Z")

    node_data = {
        "id": "PROJ-Z-SUFFIX",
        "project_id": "PROJ-Z-SUFFIX",
        "name": "Z Suffix Project",
        "created_at": now_iso_z,
        "updated_at": now_iso_z,
    }

    project = ProjectNeo4jMapper.from_node_data(node_data)

    # Should parse correctly
    assert isinstance(project.created_at, datetime)
    assert isinstance(project.updated_at, datetime)


def test_from_node_data_empty_data_raises_error():
    """Test from_node_data with empty data raises ValueError."""
    with pytest.raises(ValueError, match="Cannot create Project from empty node data"):
        ProjectNeo4jMapper.from_node_data({})


def test_from_node_data_missing_id_and_project_id_raises_error():
    """Test from_node_data raises error when both id and project_id are missing."""
    node_data = {
        "name": "Missing ID Project",
        "created_at": "2025-01-28T10:00:00Z",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Missing required field: project_id or id"):
        ProjectNeo4jMapper.from_node_data(node_data)


def test_from_node_data_missing_name_raises_error():
    """Test from_node_data raises error when name is missing."""
    node_data = {
        "project_id": "PROJ-NO-NAME",
        "created_at": "2025-01-28T10:00:00Z",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Missing required field: name"):
        ProjectNeo4jMapper.from_node_data(node_data)


def test_from_node_data_missing_timestamps_raises_error():
    """Test from_node_data raises error when timestamps are missing."""
    node_data = {
        "project_id": "PROJ-NO-TIMESTAMP",
        "name": "No Timestamp Project",
        # Missing created_at and updated_at
    }

    with pytest.raises(ValueError, match="Missing required fields: created_at or updated_at"):
        ProjectNeo4jMapper.from_node_data(node_data)


def test_from_node_data_all_statuses():
    """Test from_node_data with different status values."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    statuses = [
        ("active", ProjectStatus.ACTIVE),
        ("planning", ProjectStatus.PLANNING),
        ("in_progress", ProjectStatus.IN_PROGRESS),
        ("completed", ProjectStatus.COMPLETED),
        ("archived", ProjectStatus.ARCHIVED),
        ("cancelled", ProjectStatus.CANCELLED),
    ]

    for status_str, status_enum in statuses:
        node_data = {
            "project_id": f"PROJ-{status_str}",
            "name": f"Project {status_str}",
            "status": status_str,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        project = ProjectNeo4jMapper.from_node_data(node_data)
        assert project.status == status_enum


def test_roundtrip_project_to_neo4j_and_back():
    """Test Project → Neo4j properties → Project roundtrip."""
    now = datetime.now(UTC)

    original = Project(
        project_id=ProjectId("PROJ-ROUNDTRIP"),
        name="Roundtrip Project",
        description="Roundtrip description",
        status=ProjectStatus.IN_PROGRESS,
        owner="roundtrip-owner",
        created_at=now,
        updated_at=now,
    )

    # Convert to Neo4j properties
    neo4j_props = ProjectNeo4jMapper.to_graph_properties(original)

    # Simulate Neo4j node structure
    node_data = {"properties": neo4j_props}

    # Convert back to Project
    reconstructed = ProjectNeo4jMapper.from_node_data(node_data)

    assert reconstructed.project_id == original.project_id
    assert reconstructed.name == original.name
    assert reconstructed.status == original.status
    assert reconstructed.created_at == original.created_at
    assert reconstructed.updated_at == original.updated_at




