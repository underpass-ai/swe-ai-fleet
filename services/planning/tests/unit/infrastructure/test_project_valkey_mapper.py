"""Unit tests for ProjectValkeyMapper."""

from datetime import UTC, datetime

import pytest
from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.infrastructure.mappers.project_valkey_mapper import ProjectValkeyMapper


def test_project_to_dict():
    """Test Project to Valkey dict conversion."""
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

    result = ProjectValkeyMapper.to_dict(project)

    assert isinstance(result, dict)
    assert result["project_id"] == "PROJ-123"
    assert result["name"] == "Test Project"
    assert result["description"] == "Test description"
    assert result["status"] == "active"
    assert result["owner"] == "test-owner"
    assert result["created_at"] == now.isoformat()
    assert result["updated_at"] == now.isoformat()


def test_project_to_dict_empty_optional_fields():
    """Test to_dict with empty optional fields."""
    now = datetime.now(UTC)

    project = Project(
        project_id=ProjectId("PROJ-EMPTY"),
        name="Minimal Project",
        description="",
        status=ProjectStatus.PLANNING,
        owner="",
        created_at=now,
        updated_at=now,
    )

    result = ProjectValkeyMapper.to_dict(project)

    assert result["description"] == ""
    assert result["owner"] == ""


def test_project_from_dict():
    """Test Valkey dict to Project conversion (string keys)."""
    now = datetime.now(UTC)

    data = {
        "project_id": "PROJ-456",
        "name": "From Dict Project",
        "description": "Test description",
        "status": "active",
        "owner": "owner-user",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    project = ProjectValkeyMapper.from_dict(data)

    assert isinstance(project, Project)
    assert project.project_id.value == "PROJ-456"
    assert project.name == "From Dict Project"
    assert project.description == "Test description"
    assert project.status == ProjectStatus.ACTIVE
    assert project.owner == "owner-user"


def test_project_from_dict_bytes_keys():
    """Test from_dict with bytes keys (decode_responses=False)."""
    now = datetime.now(UTC)

    data = {
        b"project_id": b"PROJ-BYTES",
        b"name": b"Bytes Keys Project",
        b"description": b"Test",
        b"status": b"completed",
        b"owner": b"bytes-owner",
        b"created_at": now.isoformat().encode(),
        b"updated_at": now.isoformat().encode(),
    }

    project = ProjectValkeyMapper.from_dict(data)

    assert project.project_id.value == "PROJ-BYTES"
    assert project.name == "Bytes Keys Project"
    assert project.status == ProjectStatus.COMPLETED


def test_project_from_dict_with_different_statuses():
    """Test conversion with different project statuses."""
    now = datetime.now(UTC)

    statuses = [
        (ProjectStatus.ACTIVE, "active"),
        (ProjectStatus.PLANNING, "planning"),
        (ProjectStatus.COMPLETED, "completed"),
        (ProjectStatus.ARCHIVED, "archived"),
        (ProjectStatus.CANCELLED, "cancelled"),
    ]

    for status_enum, status_str in statuses:
        data = {
            "project_id": f"PROJ-{status_str.upper()}",
            "name": f"Project {status_str}",
            "description": "",
            "status": status_str,
            "owner": "",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        project = ProjectValkeyMapper.from_dict(data)
        assert project.status == status_enum


def test_project_from_dict_empty_data():
    """Test from_dict with empty data raises ValueError."""
    with pytest.raises(ValueError, match="Cannot create Project from empty dict"):
        ProjectValkeyMapper.from_dict({})


def test_project_from_dict_missing_required_field():
    """Test from_dict with missing required field raises ValueError."""
    now = datetime.now(UTC)

    data = {
        # Missing project_id
        "name": "Incomplete Project",
        "description": "",
        "status": "active",
        "owner": "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    with pytest.raises(ValueError, match="Missing required field: project_id"):
        ProjectValkeyMapper.from_dict(data)


def test_project_roundtrip():
    """Test Project → dict → Project roundtrip."""
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

    # Convert to dict
    dict_data = ProjectValkeyMapper.to_dict(original)

    # Convert back to Project (string keys)
    reconstructed = ProjectValkeyMapper.from_dict(dict_data)

    assert reconstructed.project_id == original.project_id
    assert reconstructed.name == original.name
    assert reconstructed.description == original.description
    assert reconstructed.status == original.status
    assert reconstructed.owner == original.owner
    assert reconstructed.created_at == original.created_at
    assert reconstructed.updated_at == original.updated_at


def test_project_roundtrip_bytes():
    """Test Project → dict → bytes → Project roundtrip."""
    now = datetime.now(UTC)

    original = Project(
        project_id=ProjectId("PROJ-ROUNDTRIP-BYTES"),
        name="Bytes Roundtrip",
        description="Test",
        status=ProjectStatus.ACTIVE,
        owner="owner",
        created_at=now,
        updated_at=now,
    )

    # Convert to dict
    dict_data = ProjectValkeyMapper.to_dict(original)

    # Convert dict to bytes (simulating Redis without decode_responses)
    bytes_data = {
        k.encode("utf-8"): v.encode("utf-8") if isinstance(v, str) else v
        for k, v in dict_data.items()
    }

    # Convert back to Project
    reconstructed = ProjectValkeyMapper.from_dict(bytes_data)

    assert reconstructed.project_id == original.project_id
    assert reconstructed.name == original.name
    assert reconstructed.status == original.status

