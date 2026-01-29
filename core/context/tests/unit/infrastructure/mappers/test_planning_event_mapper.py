"""Unit tests for PlanningEventMapper.payload_to_story."""

import pytest

from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.story import Story
from core.context.infrastructure.mappers.planning_event_mapper import PlanningEventMapper


class TestPayloadToStory:
    """Test suite for payload_to_story (planning.story.created → Story)."""

    def test_payload_to_story_happy_path_with_name(self) -> None:
        """Story built when payload has story_id, epic_id, name."""
        payload = {
            "story_id": "s-123",
            "epic_id": "E-456",
            "name": "As a user I want to login",
        }
        story = PlanningEventMapper.payload_to_story(payload)
        assert isinstance(story, Story)
        assert story.story_id == StoryId("s-123")
        assert story.epic_id == EpicId("E-456")
        assert story.name == "As a user I want to login"

    def test_payload_to_story_happy_path_with_title(self) -> None:
        """Story built when payload has title (Planning BC) instead of name."""
        payload = {
            "story_id": "s-789",
            "epic_id": "E-ABC",
            "title": "As a user I want to logout",
        }
        story = PlanningEventMapper.payload_to_story(payload)
        assert story.story_id == StoryId("s-789")
        assert story.epic_id == EpicId("E-ABC")
        assert story.name == "As a user I want to logout"

    def test_payload_to_story_missing_story_id_raises(self) -> None:
        """Missing story_id raises ValueError (fail-fast)."""
        payload = {"epic_id": "E-1", "name": "A story"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "story_id" in str(exc_info.value)
        assert "story.created" in str(exc_info.value).lower()

    def test_payload_to_story_missing_epic_id_raises(self) -> None:
        """Missing epic_id raises ValueError (fail-fast, no KeyError)."""
        payload = {"story_id": "s-1", "name": "A story"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "epic_id" in str(exc_info.value)
        assert "Epic" in str(exc_info.value) or "epic" in str(exc_info.value).lower()

    def test_payload_to_story_missing_name_and_title_raises(self) -> None:
        """Missing both name and title raises ValueError."""
        payload = {"story_id": "s-1", "epic_id": "E-1"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "name" in str(exc_info.value) or "title" in str(exc_info.value)

    def test_payload_to_story_empty_name_raises(self) -> None:
        """Empty name (whitespace only) raises ValueError."""
        payload = {"story_id": "s-1", "epic_id": "E-1", "name": "   "}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "name" in str(exc_info.value) or "title" in str(exc_info.value)

    def test_payload_to_story_name_or_title_must_be_str(self) -> None:
        """name/title must be str; non-str raises ValueError (no conversion)."""
        payload = {"story_id": "s-1", "epic_id": "E-1", "title": 123}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "must be str" in str(exc_info.value)
        assert "int" in str(exc_info.value)
