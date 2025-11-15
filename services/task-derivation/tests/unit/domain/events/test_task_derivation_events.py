"""Unit tests for task derivation domain events."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from task_derivation.domain.events.task_derivation_completed_event import (
    TaskDerivationCompletedEvent,
)
from task_derivation.domain.events.task_derivation_failed_event import (
    TaskDerivationFailedEvent,
)
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.status.task_derivation_status import (
    TaskDerivationStatus,
)


class TestTaskDerivationStatus:
    """Tests for TaskDerivationStatus value object."""

    def test_from_value_parses_valid_status(self) -> None:
        """Ensure string parsing returns enum members."""
        status = TaskDerivationStatus.from_value("success")

        assert status is TaskDerivationStatus.SUCCESS
        assert status.is_success()
        assert not status.is_failure()

    def test_from_value_rejects_invalid_status(self) -> None:
        """Fail fast on invalid status values."""
        with pytest.raises(ValueError, match="Invalid derivation status"):
            TaskDerivationStatus.from_value("unknown")


class TestTaskDerivationCompletedEvent:
    """Tests for TaskDerivationCompletedEvent."""

    def test_success_event_happy_path(self) -> None:
        """Ensure event captures immutable success fact."""
        event = TaskDerivationCompletedEvent(
            plan_id=PlanId("plan-123"),
            story_id=StoryId("story-123"),
            task_count=5,
            occurred_at=datetime.now(tz=timezone.utc),
        )

        assert event.status is TaskDerivationStatus.SUCCESS
        assert event.task_count == 5

    def test_success_event_requires_timezone(self) -> None:
        """Fail fast when timestamp lacks timezone info."""
        with pytest.raises(ValueError, match="timezone-aware"):
            TaskDerivationCompletedEvent(
                plan_id=PlanId("plan-123"),
                story_id=StoryId("story-123"),
                task_count=2,
                occurred_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )

    def test_success_event_rejects_negative_task_count(self) -> None:
        """Fail fast when negative task counts are provided."""
        with pytest.raises(ValueError, match="cannot be negative"):
            TaskDerivationCompletedEvent(
                plan_id=PlanId("plan-123"),
                story_id=StoryId("story-123"),
                task_count=-1,
                occurred_at=datetime.now(tz=timezone.utc),
            )

    def test_success_event_rejects_non_success_status(self) -> None:
        """Ensure status is locked to SUCCESS."""
        with pytest.raises(ValueError, match="must be SUCCESS"):
            TaskDerivationCompletedEvent(
                plan_id=PlanId("plan-123"),
                story_id=StoryId("story-123"),
                task_count=1,
                occurred_at=datetime.now(tz=timezone.utc),
                status=TaskDerivationStatus.FAILED,
            )


class TestTaskDerivationFailedEvent:
    """Tests for TaskDerivationFailedEvent."""

    def test_failure_event_happy_path(self) -> None:
        """Ensure failed event enforces status enum."""
        event = TaskDerivationFailedEvent(
            plan_id=PlanId("plan-123"),
            story_id=StoryId("story-123"),
            reason="LLM parsing failed",
            requires_manual_review=True,
            occurred_at=datetime.now(tz=timezone.utc),
        )

        assert event.status is TaskDerivationStatus.FAILED
        assert event.requires_manual_review

    def test_failure_event_requires_reason(self) -> None:
        """Fail fast when reason is empty."""
        with pytest.raises(ValueError, match="reason cannot be empty"):
            TaskDerivationFailedEvent(
                plan_id=PlanId("plan-123"),
                story_id=StoryId("story-123"),
                reason=" ",
                requires_manual_review=False,
                occurred_at=datetime.now(tz=timezone.utc),
            )

    def test_failure_event_requires_timezone(self) -> None:
        """Fail fast when timestamp is naive."""
        with pytest.raises(ValueError, match="timezone-aware"):
            TaskDerivationFailedEvent(
                plan_id=PlanId("plan-123"),
                story_id=StoryId("story-123"),
                reason="network issue",
                requires_manual_review=False,
                occurred_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )

    def test_failure_event_rejects_non_failed_status(self) -> None:
        """Ensure status is locked to FAILED."""
        with pytest.raises(ValueError, match="must be FAILED"):
            TaskDerivationFailedEvent(
                plan_id=PlanId("plan-123"),
                story_id=StoryId("story-123"),
                reason="network issue",
                requires_manual_review=False,
                occurred_at=datetime.now(tz=timezone.utc),
                status=TaskDerivationStatus.SUCCESS,
            )

