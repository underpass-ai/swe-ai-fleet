"""Tests for NatsEventMapper conversions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from task_derivation.domain.events.task_derivation_completed_event import (
    TaskDerivationCompletedEvent,
)
from task_derivation.domain.events.task_derivation_failed_event import (
    TaskDerivationFailedEvent,
)
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.infrastructure.mappers.nats_event_mapper import NatsEventMapper


def _completed_event() -> TaskDerivationCompletedEvent:
    return TaskDerivationCompletedEvent(
        plan_id=PlanId("plan-1"),
        story_id=StoryId("story-1"),
        task_count=3,
        occurred_at=datetime(2025, 1, 1, tzinfo=UTC),
        role="PLANNER",
    )


def _failed_event() -> TaskDerivationFailedEvent:
    return TaskDerivationFailedEvent(
        plan_id=PlanId("plan-1"),
        story_id=StoryId("story-1"),
        reason="LLM unreachable",
        requires_manual_review=True,
        occurred_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_mapper_converts_completed_event() -> None:
    payload = NatsEventMapper.to_completed_payload(_completed_event())

    assert payload.plan_id == "plan-1"
    assert payload.task_count == 3
    assert payload.status == "success"


def test_mapper_converts_failed_event() -> None:
    payload = NatsEventMapper.to_failed_payload(_failed_event())

    assert payload.reason == "LLM unreachable"
    assert payload.status == "failed"
    assert payload.requires_manual_review is True


def test_mapper_payload_to_dict_serializes_dataclass() -> None:
    payload = NatsEventMapper.to_completed_payload(_completed_event())
    data = NatsEventMapper.payload_to_dict(payload)

    assert data["plan_id"] == "plan-1"
    assert data["status"] == "success"


@pytest.mark.parametrize(
    ("method", "message"),
    [
        (NatsEventMapper.to_completed_payload, "event cannot be None"),
        (NatsEventMapper.to_failed_payload, "event cannot be None"),
    ],
)
def test_mapper_rejects_missing_events(method, message) -> None:
    with pytest.raises(ValueError, match=message):
        method(None)  # type: ignore[arg-type]


def test_mapper_payload_to_dict_rejects_none() -> None:
    with pytest.raises(ValueError, match="payload cannot be None"):
        NatsEventMapper.payload_to_dict(None)  # type: ignore[arg-type]

