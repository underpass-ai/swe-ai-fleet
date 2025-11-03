"""Unit tests for Story entity (Aggregate Root)."""

from datetime import UTC, datetime, timedelta

import pytest

from planning.domain import (
    Brief,
    DORScore,
    Story,
    StoryId,
    StoryState,
    StoryStateEnum,
    Title,
    UserName,
)


def test_story_creation_success():
    """Test successful Story creation."""
    now = datetime.now(UTC)

    story = Story(
        story_id=StoryId("s-test-001"),
        title=Title("As a user, I want authentication"),
        brief=Brief("Implement JWT-based auth"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by=UserName("po-001"),
        created_at=now,
        updated_at=now,
    )

    assert story.story_id.value == "s-test-001"
    assert story.title.value == "As a user, I want authentication"
    assert story.state.value == StoryStateEnum.DRAFT
    assert story.dor_score.value == 0


def test_story_is_frozen():
    """Test that Story is immutable (frozen dataclass)."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-001"),
        title=Title("Test"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(Exception):  # FrozenInstanceError
        story.title = Title("New title")  # type: ignore


def test_story_rejects_empty_title():
    """Test that Title Value Object rejects empty title."""
    # Validation is delegated to Value Object, not Story entity
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Title("")


def test_story_rejects_whitespace_title():
    """Test that Title Value Object rejects whitespace-only title."""
    # Validation is delegated to Value Object, strips and rejects empty
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Title("   ")


def test_story_rejects_empty_brief():
    """Test that Brief Value Object rejects empty brief."""
    # Validation is delegated to Value Object, not Story entity
    with pytest.raises(ValueError, match="Brief cannot be empty"):
        Brief("")


def test_story_rejects_invalid_timestamps():
    """Test that Story rejects created_at > updated_at."""
    now = datetime.now(UTC)
    future = now + timedelta(hours=1)
    past = now - timedelta(hours=1)

    with pytest.raises(ValueError, match="created_at .* cannot be after updated_at"):
        Story(
            story_id=StoryId("s-001"),
            title=Title("Title"),
            brief=Brief("Brief"),
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by=UserName("po"),
            created_at=future,  # Future
            updated_at=past,    # Past - INVALID
        )


def test_story_transition_to_success():
    """Test successful story state transition."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-001"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by=UserName("po"),
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
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-001"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )

    # DRAFT → DONE is invalid (must go through intermediate states)
    with pytest.raises(ValueError, match="Invalid state transition"):
        story.transition_to(StoryState(StoryStateEnum.DONE))


def test_story_update_dor_score():
    """Test updating DoR score."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-001"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )

    updated = story.update_dor_score(DORScore(85))

    assert updated.dor_score.value == 85
    assert updated.story_id == story.story_id
    assert updated is not story  # New instance


def test_story_update_content():
    """Test updating story content (title and/or brief)."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-001"),
        title=Title("Old title"),
        brief=Brief("Old brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )

    # Update both
    updated = story.update_content(
        title=Title("New title"),
        brief=Brief("New brief"),
    )

    assert updated.title.value == "New title"
    assert updated.brief.value == "New brief"
    assert updated.story_id == story.story_id
    assert updated is not story


def test_story_update_content_partial():
    """Test updating only title or only brief."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-001"),
        title=Title("Old title"),
        brief=Brief("Old brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )

    # Update only title
    updated_title = story.update_content(title=Title("New title"))
    assert updated_title.title.value == "New title"
    assert updated_title.brief.value == "Old brief"  # Unchanged

    # Update only brief
    updated_brief = story.update_content(brief=Brief("New brief"))
    assert updated_brief.title.value == "Old title"  # Unchanged
    assert updated_brief.brief.value == "New brief"


def test_story_update_content_rejects_empty():
    """Test that Value Objects reject empty values."""
    # Validation happens in Value Objects, not in update_content method

    with pytest.raises(ValueError, match="Title cannot be empty"):
        Title("")

    with pytest.raises(ValueError, match="Brief cannot be empty"):
        Brief("")


def test_story_meets_dor_threshold():
    """Test meets_dor_threshold() business rule."""
    now = datetime.now(UTC)

    # DoR >= 80
    high_dor = Story(
        story_id=StoryId("s-001"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(85),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )
    assert high_dor.meets_dor_threshold() is True

    # DoR < 80
    low_dor = Story(
        story_id=StoryId("s-002"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(50),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )
    assert low_dor.meets_dor_threshold() is False


def test_story_can_be_planned():
    """Test can_be_planned() business rule."""
    now = datetime.now(UTC)

    # Ready: DoR >= 80 AND state READY_FOR_PLANNING
    can_plan = Story(
        story_id=StoryId("s-003"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.READY_FOR_PLANNING),
        dor_score=DORScore(85),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )
    assert can_plan.can_be_planned() is True

    # Not ready: DoR < 80
    low_dor = Story(
        story_id=StoryId("s-004"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.READY_FOR_PLANNING),
        dor_score=DORScore(50),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )
    assert low_dor.can_be_planned() is False

    # Not ready: Wrong state
    wrong_state = Story(
        story_id=StoryId("s-005"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(85),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )
    assert wrong_state.can_be_planned() is False

    # Already planned: Cannot be planned again
    already_planned = Story(
        story_id=StoryId("s-006"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.PLANNED),
        dor_score=DORScore(85),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )
    assert already_planned.can_be_planned() is False


def test_story_is_planned_or_beyond():
    """Test is_planned_or_beyond() business rule."""
    now = datetime.now(UTC)

    # PLANNED state
    planned = Story(
        story_id=StoryId("s-007"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.PLANNED),
        dor_score=DORScore(85),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )
    assert planned.is_planned_or_beyond() is True

    # IN_PROGRESS (beyond planning)
    in_progress = Story(
        story_id=StoryId("s-008"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.IN_PROGRESS),
        dor_score=DORScore(85),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )
    assert in_progress.is_planned_or_beyond() is True

    # READY_FOR_PLANNING (NOT planned yet)
    ready_planning = Story(
        story_id=StoryId("s-009"),
        title=Title("Title"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.READY_FOR_PLANNING),
        dor_score=DORScore(85),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )
    assert ready_planning.is_planned_or_beyond() is False


def test_story_str_representation():
    """Test string representation."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-001"),
        title=Title("As a user, I want a very long title that will be truncated"),
        brief=Brief("Brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(75),
        created_by=UserName("po"),
        created_at=now,
        updated_at=now,
    )

    str_repr = str(story)
    assert "s-001" in str_repr
    assert "DRAFT" in str_repr
    assert "75/100" in str_repr

