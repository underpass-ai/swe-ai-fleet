"""Unit tests for StoryReviewResultDTO."""

from datetime import UTC, datetime

import pytest
from planning.application.dto import StoryReviewResultDTO
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)


def test_story_review_result_dto_valid():
    """Test creating valid StoryReviewResultDTO."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("ceremony-123")
    story_id = StoryId("story-456")
    role = BacklogReviewRole.ARCHITECT
    feedback = "Technical feedback from architect council"
    reviewed_at = datetime.now(UTC)

    # Act
    dto = StoryReviewResultDTO(
        ceremony_id=ceremony_id,
        story_id=story_id,
        role=role,
        feedback=feedback,
        reviewed_at=reviewed_at,
    )

    # Assert
    assert dto.ceremony_id == ceremony_id
    assert dto.story_id == story_id
    assert dto.role == role
    assert dto.feedback == feedback
    assert dto.reviewed_at == reviewed_at


def test_story_review_result_dto_immutable():
    """Test that StoryReviewResultDTO is immutable."""
    # Arrange
    dto = StoryReviewResultDTO(
        ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
        story_id=StoryId("story-456"),
        role=BacklogReviewRole.QA,
        feedback="QA feedback",
        reviewed_at=datetime.now(UTC),
    )

    # Act & Assert
    with pytest.raises(Exception):  # FrozenInstanceError
        dto.role = BacklogReviewRole.DEVOPS  # type: ignore


def test_story_review_result_dto_invalid_role():
    """Test that invalid role raises ValueError."""
    with pytest.raises(ValueError, match="role must be a BacklogReviewRole enum"):
        StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
            story_id=StoryId("story-456"),
            role="INVALID_ROLE",  # type: ignore
            feedback="Feedback",
            reviewed_at=datetime.now(UTC),
        )


def test_story_review_result_dto_empty_feedback():
    """Test that empty feedback raises ValueError."""
    with pytest.raises(ValueError, match="feedback cannot be empty"):
        StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
            story_id=StoryId("story-456"),
            role=BacklogReviewRole.ARCHITECT,
            feedback="",
            reviewed_at=datetime.now(UTC),
        )


def test_story_review_result_dto_whitespace_only_feedback():
    """Test that whitespace-only feedback raises ValueError."""
    with pytest.raises(ValueError, match="feedback cannot be empty"):
        StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
            story_id=StoryId("story-456"),
            role=BacklogReviewRole.DEVOPS,
            feedback="   ",
            reviewed_at=datetime.now(UTC),
        )


def test_story_review_result_dto_all_valid_roles():
    """Test that all valid roles (ARCHITECT, QA, DEVOPS) are accepted."""
    now = datetime.now(UTC)

    roles = [
        BacklogReviewRole.ARCHITECT,
        BacklogReviewRole.QA,
        BacklogReviewRole.DEVOPS,
    ]

    for role in roles:
        dto = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
            story_id=StoryId("story-456"),
            role=role,
            feedback=f"Feedback from {role.value}",
            reviewed_at=now,
        )
        assert dto.role == role

