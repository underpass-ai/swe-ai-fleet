from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import grpc
import pytest

from services.ray_executor.application.usecases import ExecuteDeliberationUseCase
from services.ray_executor.domain.entities import DeliberationRequest
from services.ray_executor.grpc_servicer import RayExecutorServiceServicer


@dataclass
class _DummyConstraints:
    story_id: str
    plan_id: str = ""
    timeout_seconds: int = 0
    max_retries: int = 0
    metadata: dict[str, str] | None = None


@dataclass
class _DummyAgent:
    id: str
    role: str
    model: str
    prompt_template: str


@dataclass
class _DummyRequest:
    task_id: str
    task_description: str
    role: str
    constraints: _DummyConstraints
    agents: list[_DummyAgent]
    vllm_url: str = "http://vllm"
    vllm_model: str = "model"


class _DummyContext:
    def __init__(self) -> None:
        self.code: grpc.StatusCode | None = None
        self.details: str | None = None

    def set_code(self, code: grpc.StatusCode) -> None:  # pragma: no cover - simple setter
        self.code = code

    def set_details(self, details: str) -> None:  # pragma: no cover - simple setter
        self.details = details


class _DummyExecuteDeliberationUseCase(ExecuteDeliberationUseCase):  # type: ignore[misc]
    def __init__(self) -> None:
        # Bypass parent init; tests only need execute behavior
        self.last_request: DeliberationRequest | None = None

    async def execute(self, request: DeliberationRequest) -> Any:  # type: ignore[override]
        self.last_request = request

        @dataclass
        class _Result:
            deliberation_id: str = "delib-1"
            status: str = "queued"
            message: str = "ok"

        return _Result()


class _DummyStatsUseCase:
    async def execute(self) -> tuple[Any, float]:  # pragma: no cover - not used here
        raise NotImplementedError


class _DummyStatusUseCase:
    async def execute(self, deliberation_id: str) -> Any:  # pragma: no cover - not used here
        raise NotImplementedError


class _DummyActiveJobsUseCase:
    async def execute(self) -> list[Any]:  # pragma: no cover - not used here
        raise NotImplementedError


@pytest.mark.asyncio
async def test_execute_backlog_review_deliberation_invalid_task_id_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execute_uc = _DummyExecuteDeliberationUseCase()
    servicer = RayExecutorServiceServicer(
        execute_deliberation_usecase=execute_uc,
        get_deliberation_status_usecase=_DummyStatusUseCase(),
        get_stats_usecase=_DummyStatsUseCase(),
        get_active_jobs_usecase=_DummyActiveJobsUseCase(),
    )

    request = _DummyRequest(
        task_id=" ",
        task_description="desc",
        role="ARCHITECT",
        constraints=_DummyConstraints(story_id="story-1"),
        agents=[],
    )
    context = _DummyContext()

    response = await servicer.ExecuteBacklogReviewDeliberation(request, context)

    assert isinstance(response, object)
    assert context.code == grpc.StatusCode.INVALID_ARGUMENT
    assert context.details is not None
    assert "task_id is MISSING" in context.details


@pytest.mark.asyncio
async def test_execute_backlog_review_deliberation_invalid_task_id_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execute_uc = _DummyExecuteDeliberationUseCase()
    servicer = RayExecutorServiceServicer(
        execute_deliberation_usecase=execute_uc,
        get_deliberation_status_usecase=_DummyStatusUseCase(),
        get_stats_usecase=_DummyStatsUseCase(),
        get_active_jobs_usecase=_DummyActiveJobsUseCase(),
    )

    request = _DummyRequest(
        task_id="invalid-format",
        task_description="desc",
        role="ARCHITECT",
        constraints=_DummyConstraints(story_id="story-1"),
        agents=[],
    )
    context = _DummyContext()

    response = await servicer.ExecuteBacklogReviewDeliberation(request, context)

    assert isinstance(response, object)
    assert context.code == grpc.StatusCode.INVALID_ARGUMENT
    assert context.details is not None
    assert "Invalid task_id format" in context.details


@pytest.mark.asyncio
async def test_execute_backlog_review_deliberation_happy_path_builds_request_and_metadata() -> None:
    execute_uc = _DummyExecuteDeliberationUseCase()
    servicer = RayExecutorServiceServicer(
        execute_deliberation_usecase=execute_uc,
        get_deliberation_status_usecase=_DummyStatusUseCase(),
        get_stats_usecase=_DummyStatsUseCase(),
        get_active_jobs_usecase=_DummyActiveJobsUseCase(),
    )

    constraints = _DummyConstraints(story_id="story-1", metadata={"foo": "bar"})
    agents = [_DummyAgent(id="a1", role="ARCHITECT", model="m", prompt_template="t")]

    request = _DummyRequest(
        task_id="ceremony-1:story-1:role-ARCHITECT",
        task_description="desc",
        role="ARCHITECT",
        constraints=constraints,
        agents=agents,
    )
    context = _DummyContext()

    response = await servicer.ExecuteBacklogReviewDeliberation(request, context)

    assert response.task_id == request.task_id
    assert execute_uc.last_request is not None
    assert execute_uc.last_request.constraints.story_id == "story-1"
    assert execute_uc.last_request.constraints.plan_id == ""
    assert execute_uc.last_request.constraints.metadata is not None
    assert execute_uc.last_request.constraints.metadata["foo"] == "bar"
    # story_id must be ensured in metadata
    assert execute_uc.last_request.constraints.metadata["story_id"] == "story-1"
