"""Unit tests for Story domain invariants (mandatory hierarchy)."""

import pytest
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.story import Story


class TestStoryDomainInvariants:
    """Test suite for Story domain invariants - mandatory hierarchy enforcement."""

    def test_story_with_valid_epic_id(self) -> None:
        """Test creating Story with valid epic_id (happy path)."""
        story = Story(
            story_id=StoryId("US-001"),
            epic_id=EpicId("E-001"),  # Valid epic reference
            name="User can login securely",
        )

        assert story.epic_id.to_string() == "E-001"
        assert story.name == "User can login securely"

    def test_story_without_epic_id_raises_error(self) -> None:
        """Test that Story MUST have epic_id (domain invariant).

        Domain Rule: NO orphan stories allowed.
        Every Story MUST belong to an Epic.

        Note: Validation happens in EpicId value object (fail-fast).
        This is correct layered validation.
        """
        with pytest.raises(ValueError, match="EpicId cannot be empty"):
            Story(
                story_id=StoryId("US-001"),
                epic_id=EpicId(""),  # Empty epic_id violates invariant
                name="Orphan Story",
            )

    def test_story_with_whitespace_epic_id_raises_error(self) -> None:
        """Test that epic_id cannot be whitespace-only.

        Note: Validation happens in EpicId value object (fail-fast).
        """
        with pytest.raises(ValueError, match="EpicId cannot be empty"):
            Story(
                story_id=StoryId("US-001"),
                epic_id=EpicId("   "),  # Whitespace-only violates invariant
                name="Invalid Story",
            )

    def test_story_id_cannot_be_empty(self) -> None:
        """Test that story_id cannot be empty.

        Note: Validation happens in StoryId value object (fail-fast).
        """
        with pytest.raises(ValueError, match="StoryId cannot be empty"):
            Story(
                story_id=StoryId(""),  # Empty story_id
                epic_id=EpicId("E-001"),
                name="Test Story",
            )

    def test_story_name_cannot_be_empty(self) -> None:
        """Test that story name cannot be empty."""
        with pytest.raises(ValueError, match="Story name cannot be empty"):
            Story(
                story_id=StoryId("US-001"),
                epic_id=EpicId("E-001"),
                name="",  # Empty name
            )

    def test_story_name_cannot_be_whitespace(self) -> None:
        """Test that story name cannot be whitespace-only."""
        with pytest.raises(ValueError, match="Story name cannot be empty"):
            Story(
                story_id=StoryId("US-001"),
                epic_id=EpicId("E-001"),
                name="   ",  # Whitespace-only
            )

