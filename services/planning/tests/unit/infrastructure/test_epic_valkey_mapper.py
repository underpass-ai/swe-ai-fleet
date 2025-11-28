"""Unit tests for EpicValkeyMapper."""

from datetime import UTC, datetime

import pytest
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.epic_status import EpicStatus
from planning.infrastructure.mappers.epic_valkey_mapper import EpicValkeyMapper


def test_epic_to_dict():
    """Test Epic to Valkey dict conversion."""
    now = datetime.now(UTC)

    epic = Epic(
        epic_id=EpicId("E-123"),
        project_id=ProjectId("PROJ-456"),
        title="Test Epic",
        description="Test description",
        status=EpicStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    result = EpicValkeyMapper.to_dict(epic)

    assert isinstance(result, dict)
    assert result["epic_id"] == "E-123"
    assert result["project_id"] == "PROJ-456"
    assert result["title"] == "Test Epic"
    assert result["description"] == "Test description"
    assert result["status"] == "active"
    assert result["created_at"] == now.isoformat()
    assert result["updated_at"] == now.isoformat()


def test_epic_to_dict_empty_optional_fields():
    """Test to_dict with empty optional fields."""
    now = datetime.now(UTC)

    epic = Epic(
        epic_id=EpicId("E-EMPTY"),
        project_id=ProjectId("PROJ-789"),
        title="Minimal Epic",
        description="",
        status=EpicStatus.PLANNING,
        created_at=now,
        updated_at=now,
    )

    result = EpicValkeyMapper.to_dict(epic)

    assert result["description"] == ""


def test_epic_from_dict():
    """Test Valkey dict to Epic conversion (string keys)."""
    now = datetime.now(UTC)

    data = {
        "epic_id": "E-456",
        "project_id": "PROJ-789",
        "title": "From Dict Epic",
        "description": "Test description",
        "status": "active",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    epic = EpicValkeyMapper.from_dict(data)

    assert isinstance(epic, Epic)
    assert epic.epic_id.value == "E-456"
    assert epic.project_id.value == "PROJ-789"
    assert epic.title == "From Dict Epic"
    assert epic.description == "Test description"
    assert epic.status == EpicStatus.ACTIVE


def test_epic_from_dict_bytes_keys():
    """Test from_dict with bytes keys (decode_responses=False)."""
    now = datetime.now(UTC)

    data = {
        b"epic_id": b"E-BYTES",
        b"project_id": b"PROJ-BYTES",
        b"title": b"Bytes Keys Epic",
        b"description": b"Test",
        b"status": b"completed",
        b"created_at": now.isoformat().encode(),
        b"updated_at": now.isoformat().encode(),
    }

    epic = EpicValkeyMapper.from_dict(data)

    assert epic.epic_id.value == "E-BYTES"
    assert epic.project_id.value == "PROJ-BYTES"
    assert epic.title == "Bytes Keys Epic"
    assert epic.status == EpicStatus.COMPLETED


def test_epic_from_dict_with_different_statuses():
    """Test conversion with different epic statuses."""
    now = datetime.now(UTC)

    statuses = [
        (EpicStatus.ACTIVE, "active"),
        (EpicStatus.PLANNING, "planning"),
        (EpicStatus.COMPLETED, "completed"),
        (EpicStatus.CANCELLED, "cancelled"),
    ]

    for status_enum, status_str in statuses:
        data = {
            "epic_id": f"E-{status_str.upper()}",
            "project_id": "PROJ-1",
            "title": f"Epic {status_str}",
            "description": "",
            "status": status_str,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        epic = EpicValkeyMapper.from_dict(data)
        assert epic.status == status_enum


def test_epic_from_dict_empty_data():
    """Test from_dict with empty data raises ValueError."""
    with pytest.raises(ValueError, match="Cannot create Epic from empty dict"):
        EpicValkeyMapper.from_dict({})


def test_epic_from_dict_missing_required_field():
    """Test from_dict with missing required field raises ValueError."""
    now = datetime.now(UTC)

    data = {
        # Missing epic_id
        "project_id": "PROJ-1",
        "title": "Incomplete Epic",
        "description": "",
        "status": "active",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    with pytest.raises(ValueError, match="Missing required field: epic_id"):
        EpicValkeyMapper.from_dict(data)


def test_epic_roundtrip():
    """Test Epic → dict → Epic roundtrip."""
    now = datetime.now(UTC)

    original = Epic(
        epic_id=EpicId("E-ROUNDTRIP"),
        project_id=ProjectId("PROJ-ROUNDTRIP"),
        title="Roundtrip Epic",
        description="Roundtrip description",
        status=EpicStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    # Convert to dict
    dict_data = EpicValkeyMapper.to_dict(original)

    # Convert back to Epic (string keys)
    reconstructed = EpicValkeyMapper.from_dict(dict_data)

    assert reconstructed.epic_id == original.epic_id
    assert reconstructed.project_id == original.project_id
    assert reconstructed.title == original.title
    assert reconstructed.description == original.description
    assert reconstructed.status == original.status
    assert reconstructed.created_at == original.created_at
    assert reconstructed.updated_at == original.updated_at


def test_epic_roundtrip_bytes():
    """Test Epic → dict → bytes → Epic roundtrip."""
    now = datetime.now(UTC)

    original = Epic(
        epic_id=EpicId("E-ROUNDTRIP-BYTES"),
        project_id=ProjectId("PROJ-ROUNDTRIP-BYTES"),
        title="Bytes Roundtrip",
        description="Test",
        status=EpicStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    # Convert to dict
    dict_data = EpicValkeyMapper.to_dict(original)

    # Convert dict to bytes (simulating Redis without decode_responses)
    bytes_data = {
        k.encode("utf-8"): v.encode("utf-8") if isinstance(v, str) else v
        for k, v in dict_data.items()
    }

    # Convert back to Epic
    reconstructed = EpicValkeyMapper.from_dict(bytes_data)

    assert reconstructed.epic_id == original.epic_id
    assert reconstructed.project_id == original.project_id
    assert reconstructed.title == original.title
    assert reconstructed.status == original.status

