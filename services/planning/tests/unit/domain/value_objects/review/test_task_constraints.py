"""Unit tests for BacklogReviewTaskConstraints value object."""

import pytest
from planning.domain.value_objects.review.task_constraints import (
    BacklogReviewTaskConstraints,
)


class TestBacklogReviewTaskConstraints:
    """Test suite for BacklogReviewTaskConstraints."""

    def test_create_valid_constraints(self) -> None:
        """Test creating valid constraints."""
        constraints = BacklogReviewTaskConstraints(
            rubric="Evaluate technical feasibility",
            requirements=("Requirement 1", "Requirement 2"),
            timeout_seconds=180,
            max_iterations=3,
        )

        assert constraints.rubric == "Evaluate technical feasibility"
        assert constraints.requirements == ("Requirement 1", "Requirement 2")
        assert constraints.timeout_seconds == 180
        assert constraints.max_iterations == 3
        assert constraints.metadata is None

    def test_create_with_defaults(self) -> None:
        """Test creating constraints with default values."""
        constraints = BacklogReviewTaskConstraints(
            rubric="Test rubric",
            requirements=(),
        )

        assert constraints.timeout_seconds == 180  # Default
        assert constraints.max_iterations == 3  # Default
        assert constraints.metadata is None  # Default

    def test_create_with_metadata(self) -> None:
        """Test creating constraints with metadata."""
        metadata = {"key1": "value1", "key2": "value2"}
        constraints = BacklogReviewTaskConstraints(
            rubric="Test rubric",
            requirements=(),
            metadata=metadata,
        )

        assert constraints.metadata == metadata

    def test_rejects_empty_rubric(self) -> None:
        """Test that empty rubric raises ValueError."""
        with pytest.raises(ValueError, match="rubric cannot be empty"):
            BacklogReviewTaskConstraints(
                rubric="",  # Empty
                requirements=(),
            )

    def test_rejects_whitespace_only_rubric(self) -> None:
        """Test that whitespace-only rubric raises ValueError."""
        with pytest.raises(ValueError, match="rubric cannot be empty"):
            BacklogReviewTaskConstraints(
                rubric="   ",  # Only whitespace
                requirements=(),
            )

    def test_rejects_zero_timeout(self) -> None:
        """Test that zero timeout_seconds raises ValueError."""
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            BacklogReviewTaskConstraints(
                rubric="Test rubric",
                requirements=(),
                timeout_seconds=0,
            )

    def test_rejects_negative_timeout(self) -> None:
        """Test that negative timeout_seconds raises ValueError."""
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            BacklogReviewTaskConstraints(
                rubric="Test rubric",
                requirements=(),
                timeout_seconds=-100,
            )

    def test_rejects_zero_max_iterations(self) -> None:
        """Test that zero max_iterations raises ValueError."""
        with pytest.raises(ValueError, match="max_iterations must be > 0"):
            BacklogReviewTaskConstraints(
                rubric="Test rubric",
                requirements=(),
                max_iterations=0,
            )

    def test_rejects_negative_max_iterations(self) -> None:
        """Test that negative max_iterations raises ValueError."""
        with pytest.raises(ValueError, match="max_iterations must be > 0"):
            BacklogReviewTaskConstraints(
                rubric="Test rubric",
                requirements=(),
                max_iterations=-5,
            )

    def test_is_immutable(self) -> None:
        """Test that constraints are immutable (frozen)."""
        constraints = BacklogReviewTaskConstraints(
            rubric="Test rubric",
            requirements=(),
        )

        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # FrozenInstanceError
            constraints.rubric = "Modified"  # type: ignore

    def test_empty_requirements_allowed(self) -> None:
        """Test that empty requirements tuple is allowed."""
        constraints = BacklogReviewTaskConstraints(
            rubric="Test rubric",
            requirements=(),  # Empty tuple
        )

        assert constraints.requirements == ()

    def test_multiple_requirements(self) -> None:
        """Test constraints with multiple requirements."""
        requirements = (
            "Requirement 1",
            "Requirement 2",
            "Requirement 3",
            "Requirement 4",
        )
        constraints = BacklogReviewTaskConstraints(
            rubric="Test rubric",
            requirements=requirements,
        )

        assert len(constraints.requirements) == 4
        assert constraints.requirements == requirements

