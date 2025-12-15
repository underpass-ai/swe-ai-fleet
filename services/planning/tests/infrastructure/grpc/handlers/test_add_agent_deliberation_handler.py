from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import grpc
import pytest

from planning.domain.value_objects.statuses.backlog_review_role import BacklogReviewRole
from planning.infrastructure.grpc.handlers.add_agent_deliberation_handler import (
    add_agent_deliberation_handler,
)


@dataclass
class _DummyRequest:
    ceremony_id: str
    story_id: str
    role: str
    agent_id: str
    proposal: Any
    reviewed_at: str = ""
    feedback: str = "feedback"


class _DummyContext:
    def __init__(self) -> None:
        self.code: grpc.StatusCode | None = None

    def set_code(self, code: grpc.StatusCode) -> None:  # pragma: no cover - simple setter
        self.code = code


class _DummyUseCase:
    def __init__(self) -> None:
        self.last_dto: Any | None = None

    async def execute(self, dto: Any) -> Any:  # pragma: no cover - trivial passthrough
        await asyncio.sleep(0)  # Make function properly async
        self.last_dto = dto
        return object()


@pytest.mark.asyncio
async def test_add_agent_deliberation_handler_keeps_invalid_json_proposal_as_string(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = _DummyUseCase()
    context = _DummyContext()

    # Stub out protobuf response creation to avoid importing generated types
    called: dict[str, Any] = {}

    def _fake_response_mapper(**kwargs: Any) -> dict[str, Any]:  # type: ignore[return-type]
        called.update(kwargs)
        return {"success": kwargs.get("success"), "message": kwargs.get("message")}

    from planning.infrastructure.mappers import response_protobuf_mapper as mapper_module

    monkeypatch.setattr(
        mapper_module.ResponseProtobufMapper,
        "add_agent_deliberation_response",
        staticmethod(_fake_response_mapper),
    )

    request = _DummyRequest(
        ceremony_id="cer-1",
        story_id="story-1",
        role=BacklogReviewRole.ARCHITECT.value,
        agent_id="agent-1",
        proposal="{not-valid-json}",
    )

    response = await add_agent_deliberation_handler(request, context, use_case)

    assert response["success"] is True
    assert use_case.last_dto is not None
    assert isinstance(use_case.last_dto.proposal, str)
    assert use_case.last_dto.proposal == "{not-valid-json}"


@pytest.mark.asyncio
async def test_add_agent_deliberation_handler_parses_valid_json_proposal(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = _DummyUseCase()
    context = _DummyContext()

    called: dict[str, Any] = {}

    def _fake_response_mapper(**kwargs: Any) -> dict[str, Any]:  # type: ignore[return-type]
        called.update(kwargs)
        return {"success": kwargs.get("success"), "message": kwargs.get("message")}

    from planning.infrastructure.mappers import response_protobuf_mapper as mapper_module

    monkeypatch.setattr(
        mapper_module.ResponseProtobufMapper,
        "add_agent_deliberation_response",
        staticmethod(_fake_response_mapper),
    )

    request = _DummyRequest(
        ceremony_id="cer-1",
        story_id="story-1",
        role=BacklogReviewRole.QA.value,
        agent_id="agent-2",
        proposal='{"foo": "bar"}',
    )

    response = await add_agent_deliberation_handler(request, context, use_case)

    assert response["success"] is True
    assert use_case.last_dto is not None
    assert isinstance(use_case.last_dto.proposal, dict)
    assert use_case.last_dto.proposal == {"foo": "bar"}
