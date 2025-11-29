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

