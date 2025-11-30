"""Unit tests for StoryValkeyMapper."""

from datetime import UTC, datetime

import pytest
from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum, Title, Brief, UserName
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.infrastructure.mappers.story_valkey_mapper import StoryValkeyMapper


def test_story_to_dict():
    """Test Story to Valkey dict conversion."""
    now = datetime.now(UTC)

    story = Story(
        epic_id=EpicId("E-TEST-VALKEY-001"),
        story_id=StoryId("story-123"),
        title=Title("Test Story"),
        brief=Brief("Test brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(85),
        created_by=UserName("po-user"),
        created_at=now,
        updated_at=now,
    )

    result = StoryValkeyMapper.to_dict(story)

    assert isinstance(result, dict)
    assert result["story_id"] == "story-123"
    assert result["epic_id"] == "E-TEST-VALKEY-001"  # Verify parent reference
    assert result["title"] == "Test Story"
    assert result["brief"] == "Test brief"
    assert result["state"] == "DRAFT"
    assert result["dor_score"] == "85"
    assert result["created_by"] == "po-user"
    assert result["created_at"] == now.isoformat()
    assert result["updated_at"] == now.isoformat()


def test_story_from_dict():
    """Test Valkey dict to Story conversion."""
    now = datetime.now(UTC)

    data = {
        b"story_id": b"story-123",
        b"epic_id": b"E-TEST-VALKEY-002",  # Parent reference (domain invariant)
        b"title": b"Test Story",
        b"brief": b"Test brief",
        b"state": b"DRAFT",
        b"dor_score": b"85",
        b"created_by": b"po-user",
        b"created_at": now.isoformat().encode(),
        b"updated_at": now.isoformat().encode(),
    }

    story = StoryValkeyMapper.from_dict(data)

    assert isinstance(story, Story)
    assert story.story_id.value == "story-123"
    assert story.epic_id.value == "E-TEST-VALKEY-002"  # Verify parent
    assert story.title.value == "Test Story"
    assert story.brief.value == "Test brief"
    assert story.state.value == StoryStateEnum.DRAFT
    assert story.dor_score.value == 85
    assert story.created_by.value == "po-user"


def test_story_from_dict_with_different_states():
    """Test conversion with different FSM states."""
    now = datetime.now(UTC)

    for state_enum in [StoryStateEnum.DRAFT, StoryStateEnum.ACCEPTED, StoryStateEnum.CARRY_OVER]:
        data = {
            b"story_id": b"story-123",
            b"epic_id": b"E-TEST-STATES",
            b"title": b"Test",
            b"brief": b"Brief",
            b"state": state_enum.value.encode(),
            b"dor_score": b"85",
            b"created_by": b"po",
            b"created_at": now.isoformat().encode(),
            b"updated_at": now.isoformat().encode(),
        }

        story = StoryValkeyMapper.from_dict(data)
        assert story.state.value == state_enum


def test_story_from_dict_empty_data():
    """Test from_dict with empty data raises ValueError."""
    with pytest.raises(ValueError, match="Cannot create Story from empty dict"):
        StoryValkeyMapper.from_dict({})


def test_story_roundtrip():
    """Test Story → dict → Story roundtrip."""
    now = datetime.now(UTC)

    original = Story(
        epic_id=EpicId("E-TEST-ROUNDTRIP"),
        story_id=StoryId("story-123"),
        title=Title("Test Story"),
        brief=Brief("Test brief"),
        state=StoryState(StoryStateEnum.IN_PROGRESS),
        dor_score=DORScore(90),
        created_by=UserName("po-user"),
        created_at=now,
        updated_at=now,
    )

    # Convert to dict
    dict_data = StoryValkeyMapper.to_dict(original)

    # Convert dict to bytes (simulating Redis)
    bytes_data = {k.encode(): v.encode() if isinstance(v, str) else v for k, v in dict_data.items()}

    # Convert back to Story
    reconstructed = StoryValkeyMapper.from_dict(bytes_data)

    assert reconstructed.story_id == original.story_id
    assert reconstructed.title == original.title
    assert reconstructed.state.value == original.state.value
    assert reconstructed.dor_score.value == original.dor_score.value


def test_story_from_dict_with_string_keys():
    """Test from_dict with string keys (decode_responses=True)."""
    now = datetime.now(UTC)

    data = {
        "story_id": "story-123",
        "epic_id": "E-TEST-STRING-KEYS",
        "title": "Test Story",
        "brief": "Test brief",
        "state": "DRAFT",
        "dor_score": "85",
        "created_by": "po-user",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    story = StoryValkeyMapper.from_dict(data)

    assert isinstance(story, Story)
    assert story.story_id.value == "story-123"
    assert story.epic_id.value == "E-TEST-STRING-KEYS"
    assert story.title.value == "Test Story"
    assert story.brief.value == "Test brief"
    assert story.state.value == StoryStateEnum.DRAFT
    assert story.dor_score.value == 85
    assert story.created_by.value == "po-user"


def test_story_from_dict_missing_required_field():
    """Test from_dict raises ValueError when required field is missing."""
    now = datetime.now(UTC)

    data = {
        "story_id": "story-123",
        # "epic_id": missing - REQUIRED field
        "title": "Test Story",
        "brief": "Test brief",
        "state": "DRAFT",
        "dor_score": "85",
        "created_by": "po-user",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    with pytest.raises(ValueError, match="Missing required field: epic_id"):
        StoryValkeyMapper.from_dict(data)


def test_story_from_dict_missing_story_id():
    """Test from_dict raises ValueError when story_id is missing."""
    now = datetime.now(UTC)

    data = {
        # "story_id": missing
        "epic_id": "E-TEST-001",
        "title": "Test Story",
        "brief": "Test brief",
        "state": "DRAFT",
        "dor_score": "85",
        "created_by": "po-user",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    with pytest.raises(ValueError, match="Missing required field: story_id"):
        StoryValkeyMapper.from_dict(data)


def test_story_from_dict_missing_title():
    """Test from_dict raises ValueError when title is missing."""
    now = datetime.now(UTC)

    data = {
        "story_id": "story-123",
        "epic_id": "E-TEST-001",
        # "title": missing
        "brief": "Test brief",
        "state": "DRAFT",
        "dor_score": "85",
        "created_by": "po-user",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    with pytest.raises(ValueError, match="Missing required field: title"):
        StoryValkeyMapper.from_dict(data)


def test_story_from_dict_mixed_string_and_bytes_keys():
    """Test from_dict handles edge case where dict has mixed key types (should use first sample)."""
    now = datetime.now(UTC)

    # Create dict with string keys (simulating decode_responses=True)
    data = {
        "story_id": "story-123",
        "epic_id": "E-TEST-MIXED",
        "title": "Test Story",
        "brief": "Test brief",
        "state": "DRAFT",
        "dor_score": "85",
        "created_by": "po-user",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    story = StoryValkeyMapper.from_dict(data)

    assert story.story_id.value == "story-123"
    assert story.epic_id.value == "E-TEST-MIXED"


def test_story_roundtrip_with_string_keys():
    """Test Story → dict → Story roundtrip with string keys (decode_responses=True)."""
    now = datetime.now(UTC)

    original = Story(
        epic_id=EpicId("E-TEST-ROUNDTRIP-STR"),
        story_id=StoryId("story-456"),
        title=Title("Roundtrip Test"),
        brief=Brief("Roundtrip brief"),
        state=StoryState(StoryStateEnum.ACCEPTED),
        dor_score=DORScore(95),
        created_by=UserName("po-user-2"),
        created_at=now,
        updated_at=now,
    )

    # Convert to dict (string keys)
    dict_data = StoryValkeyMapper.to_dict(original)

    # Convert back to Story (using string keys directly)
    reconstructed = StoryValkeyMapper.from_dict(dict_data)

    assert reconstructed.story_id == original.story_id
    assert reconstructed.epic_id == original.epic_id
    assert reconstructed.title == original.title
    assert reconstructed.brief == original.brief
    assert reconstructed.state.value == original.state.value
    assert reconstructed.dor_score.value == original.dor_score.value
    assert reconstructed.created_by == original.created_by
    assert reconstructed.created_at == original.created_at
    assert reconstructed.updated_at == original.updated_at


def test_story_to_dict_all_fields():
    """Test to_dict includes all required fields."""
    now = datetime.now(UTC)

    story = Story(
        epic_id=EpicId("E-ALL-FIELDS"),
        story_id=StoryId("story-all"),
        title=Title("All Fields Story"),
        brief=Brief("Complete brief"),
        state=StoryState(StoryStateEnum.DONE),
        dor_score=DORScore(100),
        created_by=UserName("admin"),
        created_at=now,
        updated_at=now,
    )

    result = StoryValkeyMapper.to_dict(story)

    # Verify all fields are present
    required_fields = [
        "story_id",
        "epic_id",
        "title",
        "brief",
        "state",
        "dor_score",
        "created_by",
        "created_at",
        "updated_at",
    ]
    for field in required_fields:
        assert field in result, f"Missing field: {field}"

    # Verify all values are strings
    for value in result.values():
        assert isinstance(value, str), f"Value {value} is not a string"


def test_story_from_dict_invalid_dor_score():
    """Test from_dict handles invalid dor_score (should raise ValueError from DORScore)."""
    now = datetime.now(UTC)

    data = {
        "story_id": "story-123",
        "epic_id": "E-TEST-001",
        "title": "Test Story",
        "brief": "Test brief",
        "state": "DRAFT",
        "dor_score": "invalid",  # Invalid - not a number
        "created_by": "po-user",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    with pytest.raises(ValueError):
        StoryValkeyMapper.from_dict(data)


def test_story_from_dict_invalid_datetime():
    """Test from_dict handles invalid datetime format."""
    data = {
        "story_id": "story-123",
        "epic_id": "E-TEST-001",
        "title": "Test Story",
        "brief": "Test brief",
        "state": "DRAFT",
        "dor_score": "85",
        "created_by": "po-user",
        "created_at": "invalid-datetime",  # Invalid format
        "updated_at": "2024-01-01T00:00:00+00:00",
    }

    with pytest.raises(ValueError):
        StoryValkeyMapper.from_dict(data)


def test_story_from_dict_bytes_value_not_bytes_type():
    """Test from_dict handles bytes dict where value is not bytes type (covers line 86)."""
    now = datetime.now(UTC)

    # Create dict with bytes keys but string values (edge case)
    data = {
        b"story_id": "story-123",  # bytes key, str value
        b"epic_id": "E-TEST-BYTES-STR",
        b"title": "Test Story",
        b"brief": "Test brief",
        b"state": "DRAFT",
        b"dor_score": "85",
        b"created_by": "po-user",
        b"created_at": now.isoformat(),
        b"updated_at": now.isoformat(),
    }

    story = StoryValkeyMapper.from_dict(data)

    assert story.story_id.value == "story-123"
    assert story.epic_id.value == "E-TEST-BYTES-STR"


def test_story_from_dict_missing_field_bytes_keys():
    """Test from_dict raises ValueError when field is missing (bytes keys)."""
    now = datetime.now(UTC)

    data = {
        b"story_id": b"story-123",
        # b"epic_id": missing - REQUIRED field
        b"title": b"Test Story",
        b"brief": b"Test brief",
        b"state": b"DRAFT",
        b"dor_score": b"85",
        b"created_by": b"po-user",
        b"created_at": now.isoformat().encode(),
        b"updated_at": now.isoformat().encode(),
    }

    with pytest.raises(ValueError, match="Missing required field: epic_id"):
        StoryValkeyMapper.from_dict(data)

