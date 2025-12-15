from __future__ import annotations

"""Unit tests for RayExecutorServiceServicer."""

from dataclasses import dataclass
from typing import Any

import asyncio
import grpc
import pytest

from services.ray_executor.domain.entities import (
    DeliberationResult,
    ExecutionStats,
    JobInfo,
    MultiAgentDeliberationResult,
)
from services.ray_executor.grpc_servicer import RayExecutorServiceServicer
from services.ray_executor.gen import ray_executor_pb2


@dataclass
class _DummyStatusRequest:
    deliberation_id: str


class _DummyContext:
    def __init__(self) -> None:
        self.code: grpc.StatusCode | None = None
        self.details: str | None = None

    def set_code(self, code: grpc.StatusCode) -> None:  # pragma: no cover - simple setter
        self.code = code

    def set_details(self, details: str) -> None:  # pragma: no cover - simple setter
        self.details = details


class _DummyGetDeliberationStatusUseCase:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.last_id: str | None = None

    async def execute(self, deliberation_id: str) -> Any:  # type: ignore[no-untyped-def]
        await asyncio.sleep(0)  # Make function properly async
        self.last_id = deliberation_id
        return self.response


class _DummyGetStatsUseCase:
    def __init__(self, stats: ExecutionStats, uptime: float) -> None:
        self._stats = stats
        self._uptime = uptime

    async def execute(self) -> tuple[ExecutionStats, float]:
        await asyncio.sleep(0)  # Make function properly async
        return self._stats, self._uptime


class _DummyGetActiveJobsUseCase:
    def __init__(self, jobs: list[JobInfo]) -> None:
        self._jobs = jobs

    async def execute(self) -> list[JobInfo]:
        await asyncio.sleep(0)  # Make function properly async
        return self._jobs


class _NoopExecuteDeliberationUseCase:
    async def execute(self, request: Any) -> Any:  # pragma: no cover - not used here
        raise NotImplementedError


@pytest.mark.asyncio
async def test_get_deliberation_status_single_result() -> None:
    """GetDeliberationStatus should map single DeliberationResult correctly."""
    domain_result = DeliberationResult(
        agent_id="agent-1",
        proposal="Use microservices",
        reasoning="Scalability",
        score=0.9,
        metadata={"foo": "bar"},
    )

    class _Response:
        status: str = "completed"
        result: DeliberationResult | None = domain_result
        error_message: str | None = None

    usecase = _DummyGetDeliberationStatusUseCase(response=_Response())
    stats_uc = _DummyGetStatsUseCase(
        stats=ExecutionStats(
            total_deliberations=0,
            active_deliberations=0,
            completed_deliberations=0,
            failed_deliberations=0,
            average_execution_time_ms=0.0,
        ),
        uptime=0.0,
    )
    jobs_uc = _DummyGetActiveJobsUseCase(jobs=[])

    servicer = RayExecutorServiceServicer(
        execute_deliberation_usecase=_NoopExecuteDeliberationUseCase(),  # type: ignore[arg-type]
        get_deliberation_status_usecase=usecase,
        get_stats_usecase=stats_uc,  # type: ignore[arg-type]
        get_active_jobs_usecase=jobs_uc,  # type: ignore[arg-type]
    )

    request = _DummyStatusRequest(deliberation_id="delib-1")
    context = _DummyContext()

    response = await servicer.GetDeliberationStatus(request, context)

    assert isinstance(response, ray_executor_pb2.GetDeliberationStatusResponse)
    assert response.status == "completed"
    assert response.result.agent_id == "agent-1"
    assert response.result.proposal == "Use microservices"
    assert response.result.reasoning == "Scalability"
    assert response.result.score == pytest.approx(0.9)
    assert dict(response.result.metadata) == {"foo": "bar"}
    assert response.error_message == ""
    assert usecase.last_id == "delib-1"


@pytest.mark.asyncio
async def test_get_deliberation_status_multi_agent_result() -> None:
    """GetDeliberationStatus should map MultiAgentDeliberationResult using best_result and metadata."""
    r1 = DeliberationResult(
        agent_id="agent-1",
        proposal="Option A",
        reasoning="Reason A",
        score=0.8,
        metadata={"a": "1"},
    )
    r2 = DeliberationResult(
        agent_id="agent-2",
        proposal="Option B",
        reasoning="Reason B",
        score=0.9,
        metadata={"b": "2"},
    )
    multi = MultiAgentDeliberationResult(
        agent_results=[r1, r2],
        total_agents=2,
        completed_agents=2,
        failed_agents=0,
    )

    class _Response:
        status: str = "completed"
        result: MultiAgentDeliberationResult | None = multi
        error_message: str | None = None

    usecase = _DummyGetDeliberationStatusUseCase(response=_Response())
    stats_uc = _DummyGetStatsUseCase(
        stats=ExecutionStats(
            total_deliberations=0,
            active_deliberations=0,
            completed_deliberations=0,
            failed_deliberations=0,
            average_execution_time_ms=0.0,
        ),
        uptime=0.0,
    )
    jobs_uc = _DummyGetActiveJobsUseCase(jobs=[])

    servicer = RayExecutorServiceServicer(
        execute_deliberation_usecase=_NoopExecuteDeliberationUseCase(),  # type: ignore[arg-type]
        get_deliberation_status_usecase=usecase,
        get_stats_usecase=stats_uc,  # type: ignore[arg-type]
        get_active_jobs_usecase=jobs_uc,  # type: ignore[arg-type]
    )

    request = _DummyStatusRequest(deliberation_id="delib-2")
    context = _DummyContext()

    response = await servicer.GetDeliberationStatus(request, context)

    assert response.status == "completed"
    # best_result is r2
    assert response.result.agent_id == "agent-2"
    assert response.result.proposal == "Option B"
    assert response.result.reasoning == "Reason B"
    assert response.result.score == pytest.approx(0.9)

    metadata = dict(response.result.metadata)
    assert metadata["b"] == "2"
    assert metadata["total_agents"] == "2"
    assert metadata["completed_agents"] == "2"
    assert metadata["failed_agents"] == "0"
    assert "average_score" in metadata


@pytest.mark.asyncio
async def test_get_deliberation_status_with_error_message_only() -> None:
    """GetDeliberationStatus should set error_message when present."""

    class _Response:
        status: str = "failed"
        result: None = None
        error_message: str | None = "boom"

    usecase = _DummyGetDeliberationStatusUseCase(response=_Response())
    stats_uc = _DummyGetStatsUseCase(
        stats=ExecutionStats(
            total_deliberations=0,
            active_deliberations=0,
            completed_deliberations=0,
            failed_deliberations=0,
            average_execution_time_ms=0.0,
        ),
        uptime=0.0,
    )
    jobs_uc = _DummyGetActiveJobsUseCase(jobs=[])

    servicer = RayExecutorServiceServicer(
        execute_deliberation_usecase=_NoopExecuteDeliberationUseCase(),  # type: ignore[arg-type]
        get_deliberation_status_usecase=usecase,
        get_stats_usecase=stats_uc,  # type: ignore[arg-type]
        get_active_jobs_usecase=jobs_uc,  # type: ignore[arg-type]
    )

    request = _DummyStatusRequest(deliberation_id="delib-3")
    context = _DummyContext()

    response = await servicer.GetDeliberationStatus(request, context)

    assert response.status == "failed"
    assert response.error_message == "boom"
    assert not response.HasField("result")


@pytest.mark.asyncio
async def test_get_status_happy_path() -> None:
    """GetStatus should map ExecutionStats and uptime to proto."""
    stats = ExecutionStats(
        total_deliberations=10,
        active_deliberations=2,
        completed_deliberations=7,
        failed_deliberations=1,
        average_execution_time_ms=123.4,
    )
    stats_uc = _DummyGetStatsUseCase(stats=stats, uptime=42.0)
    jobs_uc = _DummyGetActiveJobsUseCase(jobs=[])
    status_uc = _DummyGetDeliberationStatusUseCase(response=None)

    servicer = RayExecutorServiceServicer(
        execute_deliberation_usecase=_NoopExecuteDeliberationUseCase(),  # type: ignore[arg-type]
        get_deliberation_status_usecase=status_uc,
        get_stats_usecase=stats_uc,  # type: ignore[arg-type]
        get_active_jobs_usecase=jobs_uc,  # type: ignore[arg-type]
    )

    request = object()
    context = _DummyContext()

    response = await servicer.GetStatus(request, context)

    assert response.status == "healthy"
    assert response.uptime_seconds == pytest.approx(42.0)
    assert response.stats.total_deliberations == 10
    assert response.stats.active_deliberations == 2
    assert response.stats.completed_deliberations == 7
    assert response.stats.failed_deliberations == 1
    assert response.stats.average_execution_time_ms == pytest.approx(123.4)


@pytest.mark.asyncio
async def test_get_active_jobs_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """GetActiveJobs should map JobInfo list to proto response."""
    job = JobInfo(
        job_id="job-1",
        name="vllm-agent-job-job-1",
        status="RUNNING",
        submission_id="delib-1",
        role="DEV",
        task_id="task-1",
        start_time_seconds=1234567890,
        runtime="1m 0s",
    )
    jobs_uc = _DummyGetActiveJobsUseCase(jobs=[job])
    stats_uc = _DummyGetStatsUseCase(
        stats=ExecutionStats(
            total_deliberations=0,
            active_deliberations=0,
            completed_deliberations=0,
            failed_deliberations=0,
            average_execution_time_ms=0.0,
        ),
        uptime=0.0,
    )
    status_uc = _DummyGetDeliberationStatusUseCase(response=None)

    # Timestamp comes from google.protobuf.timestamp_pb2.Timestamp
    from google.protobuf.timestamp_pb2 import Timestamp  # type: ignore[import]

    # Patch in Timestamp into module namespace if missing (defensive)
    import services.ray_executor.grpc_servicer as servicer_module

    if not hasattr(servicer_module, "Timestamp"):
        setattr(servicer_module, "Timestamp", Timestamp)

    servicer = RayExecutorServiceServicer(
        execute_deliberation_usecase=_NoopExecuteDeliberationUseCase(),  # type: ignore[arg-type]
        get_deliberation_status_usecase=status_uc,
        get_stats_usecase=stats_uc,  # type: ignore[arg-type]
        get_active_jobs_usecase=jobs_uc,  # type: ignore[arg-type]
    )

    request = object()
    context = _DummyContext()

    response = await servicer.GetActiveJobs(request, context)

    assert len(response.jobs) == 1
    proto_job = response.jobs[0]

    assert proto_job.job_id == "job-1"
    assert proto_job.name == "vllm-agent-job-job-1"
    assert proto_job.status == "RUNNING"
    assert proto_job.submission_id == "delib-1"
    assert proto_job.role == "DEV"
    assert proto_job.task_id == "task-1"
    assert proto_job.runtime == "1m 0s"

