"""Unit tests for Story entity (Aggregate Root)."""

import pytest
from datetime import datetime, timedelta

from planning.domain import Story, StoryId, StoryState, StoryStateEnum, DORScore


def test_story_creation_success():
    """Test successful Story creation."""
    now = datetime.utcnow()
    
    story = Story(
        story_id=StoryId("s-test-001"),
        title="As a user, I want authentication",
        brief="Implement JWT-based auth",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po-001",
        created_at=now,
        updated_at=now,
    )
    
    assert story.story_id.value == "s-test-001"
    assert story.title == "As a user, I want authentication"
    assert story.state.value == StoryStateEnum.DRAFT
    assert story.dor_score.value == 0


def test_story_is_frozen():
    """Test that Story is immutable (frozen dataclass)."""
    now = datetime.utcnow()
    story = Story(
        story_id=StoryId("s-001"),
        title="Test",
        brief="Brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    
    with pytest.raises(Exception):  # FrozenInstanceError
        story.title = "New title"  # type: ignore


def test_story_rejects_empty_title():
    """Test that Story rejects empty title."""
    now = datetime.utcnow()
    
    with pytest.raises(ValueError, match="title cannot be empty"):
        Story(
            story_id=StoryId("s-001"),
            title="",
            brief="Brief",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by="po",
            created_at=now,
            updated_at=now,
        )


def test_story_rejects_whitespace_title():
    """Test that Story rejects whitespace-only title."""
    now = datetime.utcnow()
    
    with pytest.raises(ValueError, match="title cannot be whitespace"):
        Story(
            story_id=StoryId("s-001"),
            title="   ",
            brief="Brief",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by="po",
            created_at=now,
            updated_at=now,
        )


def test_story_rejects_empty_brief():
    """Test that Story rejects empty brief."""
    now = datetime.utcnow()
    
    with pytest.raises(ValueError, match="brief cannot be empty"):
        Story(
            story_id=StoryId("s-001"),
            title="Title",
            brief="",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by="po",
            created_at=now,
            updated_at=now,
        )


def test_story_rejects_invalid_timestamps():
    """Test that Story rejects created_at > updated_at."""
    now = datetime.utcnow()
    future = now + timedelta(hours=1)
    past = now - timedelta(hours=1)
    
    with pytest.raises(ValueError, match="created_at .* cannot be after updated_at"):
        Story(
            story_id=StoryId("s-001"),
            title="Title",
            brief="Brief",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by="po",
            created_at=future,  # Future
            updated_at=past,    # Past - INVALID
        )


def test_story_transition_to_success():
    """Test successful story state transition."""
    now = datetime.utcnow()
    story = Story(
        story_id=StoryId("s-001"),
        title="Title",
        brief="Brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    
    # Transition to PO_REVIEW
    updated = story.transition_to(StoryState(StoryStateEnum.PO_REVIEW))
    
    assert updated.state.value == StoryStateEnum.PO_REVIEW
    assert updated.story_id == story.story_id  # ID unchanged
    assert updated.title == story.title  # Content unchanged
    assert updated is not story  # New instance (immutable)


def test_story_transition_invalid():
    """Test invalid state transition."""
    now = datetime.utcnow()
    story = Story(
        story_id=StoryId("s-001"),
        title="Title",
        brief="Brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    
    # DRAFT → DONE is invalid (must go through intermediate states)
    with pytest.raises(ValueError, match="Invalid state transition"):
        story.transition_to(StoryState(StoryStateEnum.DONE))


def test_story_update_dor_score():
    """Test updating DoR score."""
    now = datetime.utcnow()
    story = Story(
        story_id=StoryId("s-001"),
        title="Title",
        brief="Brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    
    updated = story.update_dor_score(DORScore(85))
    
    assert updated.dor_score.value == 85
    assert updated.story_id == story.story_id
    assert updated is not story  # New instance


def test_story_update_content():
    """Test updating story content (title and/or brief)."""
    now = datetime.utcnow()
    story = Story(
        story_id=StoryId("s-001"),
        title="Old title",
        brief="Old brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    
    # Update both
    updated = story.update_content(
        title="New title",
        brief="New brief",
    )
    
    assert updated.title == "New title"
    assert updated.brief == "New brief"
    assert updated.story_id == story.story_id
    assert updated is not story


def test_story_update_content_partial():
    """Test updating only title or only brief."""
    now = datetime.utcnow()
    story = Story(
        story_id=StoryId("s-001"),
        title="Old title",
        brief="Old brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    
    # Update only title
    updated_title = story.update_content(title="New title")
    assert updated_title.title == "New title"
    assert updated_title.brief == "Old brief"  # Unchanged
    
    # Update only brief
    updated_brief = story.update_content(brief="New brief")
    assert updated_brief.title == "Old title"  # Unchanged
    assert updated_brief.brief == "New brief"


def test_story_update_content_rejects_empty():
    """Test that update_content rejects empty values."""
    now = datetime.utcnow()
    story = Story(
        story_id=StoryId("s-001"),
        title="Title",
        brief="Brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    
    with pytest.raises(ValueError, match="Title cannot be empty"):
        story.update_content(title="")
    
    with pytest.raises(ValueError, match="Brief cannot be empty"):
        story.update_content(brief="")


def test_story_is_ready_for_planning():
    """Test is_ready_for_planning() business rule."""
    now = datetime.utcnow()
    
    # Ready: DoR >= 80 AND state >= READY_FOR_PLANNING
    ready_story = Story(
        story_id=StoryId("s-001"),
        title="Title",
        brief="Brief",
        state=StoryState(StoryStateEnum.READY_FOR_PLANNING),
        dor_score=DORScore(85),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    assert ready_story.is_ready_for_planning() is True
    
    # Not ready: DoR < 80
    not_ready_score = Story(
        story_id=StoryId("s-002"),
        title="Title",
        brief="Brief",
        state=StoryState(StoryStateEnum.READY_FOR_PLANNING),
        dor_score=DORScore(50),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    assert not_ready_score.is_ready_for_planning() is False
    
    # Not ready: State is DRAFT
    not_ready_state = Story(
        story_id=StoryId("s-003"),
        title="Title",
        brief="Brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(85),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    assert not_ready_state.is_ready_for_planning() is False


def test_story_str_representation():
    """Test string representation."""
    now = datetime.utcnow()
    story = Story(
        story_id=StoryId("s-001"),
        title="As a user, I want a very long title that will be truncated",
        brief="Brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(75),
        created_by="po",
        created_at=now,
        updated_at=now,
    )
    
    str_repr = str(story)
    assert "s-001" in str_repr
    assert "DRAFT" in str_repr
    assert "75/100" in str_repr

