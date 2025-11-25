"""Tests for task derivation event payload DTOs."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from task_derivation.infrastructure.dto.task_derivation_completed_payload import (
    TaskDerivationCompletedPayload,
)
from task_derivation.infrastructure.dto.task_derivation_failed_payload import (
    TaskDerivationFailedPayload,
)


def _utc_now() -> str:
    return datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()


def test_completed_payload_accepts_valid_values() -> None:
    payload = TaskDerivationCompletedPayload(
        plan_id="plan-1",
        story_id="story-1",
        task_count=3,
        status="success",
        occurred_at=_utc_now(),
        derivation_request_id="req-123",
    )

    assert payload.plan_id == "plan-1"
    assert payload.task_count == 3
    assert payload.status == "success"
    assert payload.derivation_request_id == "req-123"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("plan_id", "", "plan_id cannot be empty"),
        ("story_id", "", "story_id cannot be empty"),
        ("task_count", -1, "task_count cannot be negative"),
        ("status", "done", "Invalid status"),
        ("occurred_at", "", "occurred_at cannot be empty"),
    ],
)
def test_completed_payload_validation(field: str, value: object, message: str) -> None:
    kwargs = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "task_count": 1,
        "status": "success",
        "occurred_at": _utc_now(),
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        TaskDerivationCompletedPayload(**kwargs)  # type: ignore[arg-type]


def test_failed_payload_accepts_valid_values() -> None:
    payload = TaskDerivationFailedPayload(
        plan_id="plan-1",
        story_id="story-1",
        status="failed",
        reason="LLM timeout",
        requires_manual_review=True,
        occurred_at=_utc_now(),
    )

    assert payload.reason == "LLM timeout"
    assert payload.requires_manual_review is True
    assert payload.status == "failed"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("plan_id", "", "plan_id cannot be empty"),
        ("story_id", "", "story_id cannot be empty"),
        ("status", "error", "Invalid status"),
        ("reason", "", "reason cannot be empty"),
        ("occurred_at", "", "occurred_at cannot be empty"),
    ],
)
def test_failed_payload_validation(field: str, value: object, message: str) -> None:
    kwargs = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "status": "failed",
        "reason": "LLM timeout",
        "requires_manual_review": False,
        "occurred_at": _utc_now(),
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        TaskDerivationFailedPayload(**kwargs)  # type: ignore[arg-type]

