"""Tests for TaskDerivationRequestMapper."""

from __future__ import annotations

import pytest
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.requests.task_derivation_request import (
    TaskDerivationRequest,
)
from task_derivation.infrastructure.mappers.task_derivation_request_mapper import (
    TaskDerivationRequestMapper,
)


def test_mapper_parses_roles_list() -> None:
    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "roles": ["DEVELOPER", "QA"],
        "requested_by": "user-123",
    }

    request = TaskDerivationRequestMapper.from_event(payload)

    assert isinstance(request, TaskDerivationRequest)
    assert len(request.roles) == 2
    assert request.roles[0] == ContextRole("DEVELOPER")


def test_mapper_defaults_role_when_missing() -> None:
    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "requested_by": "user-123",
    }

    request = TaskDerivationRequestMapper.from_event(payload)

    assert request.roles[0] == ContextRole("DEVELOPER")


def test_mapper_rejects_missing_plan_id() -> None:
    payload = {"story_id": "story-1", "requested_by": "user-123"}

    with pytest.raises(ValueError):
        TaskDerivationRequestMapper.from_event(payload)

