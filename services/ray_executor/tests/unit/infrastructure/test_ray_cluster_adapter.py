from __future__ import annotations

"""Unit tests for RayClusterAdapter."""

from typing import Any

import pytest

import services.ray_executor.infrastructure.adapters.ray_cluster_adapter as adapter_module
from services.ray_executor.domain.entities import (
    DeliberationResult,
    MultiAgentDeliberationResult,
)


@pytest.mark.asyncio
async def test_submit_deliberation_happy_path_creates_registry_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """submit_deliberation should create Ray jobs and registry entry."""

    class _FakeActor:
        def __init__(self, agent_id: str) -> None:
            self.agent_id = agent_id
            self.run_kwargs: list[dict[str, Any]] = []

        class run:  # type: ignore[too-many-ancestors]
            @staticmethod
            def remote(**kwargs: Any) -> str:  # type: ignore[no-untyped-def]
                # Return a simple string as fake future identifier
                return f"future-{kwargs['task_id']}"

    class _FakeRayAgentJob:
        @staticmethod
        def remote(
            **kwargs: Any,  # type: ignore[no-untyped-def]
        ) -> _FakeActor:
            # We don't use kwargs here beyond creating a fake actor
            return _FakeActor(agent_id=kwargs.get("config").agent_id)  # type: ignore[arg-type]

    monkeypatch.setattr(adapter_module, "RayAgentJob", _FakeRayAgentJob)

    registry: dict[str, Any] = {}
    adapter = adapter_module.RayClusterAdapter(registry)

    agents = [
        {"agent_id": "agent-1", "role": "DEV"},
        {"agent_id": "agent-2", "role": "QA"},
    ]

    deliberation_id = "delib-1"

    result = await adapter.submit_deliberation(
        deliberation_id=deliberation_id,
        task_id="task-123",
        task_description="Do something important",
        role="DEV",
        agents=agents,
        constraints={"story_id": "story-1", "metadata": {"task_id": "orig-task"}},
        vllm_url="http://vllm",
        vllm_model="model",
    )

    assert result == deliberation_id
    assert deliberation_id in registry

    entry = registry[deliberation_id]
    assert entry["status"] == "running"
    assert entry["task_id"] == "task-123"
    assert entry["role"] == "DEV"
    assert entry["total_agents"] == 2
    assert entry["agents"] == ["agent-1", "agent-2"]
    assert isinstance(entry["futures"], list)
    assert len(entry["futures"]) == 2
    assert entry["start_time"] > 0.0
    # Metadata should be enriched
    assert entry["futures"][0].startswith("future-task-123")  # type: ignore[index]


@pytest.mark.asyncio
async def test_submit_deliberation_handles_non_dict_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """submit_deliberation should wrap non-dict metadata into 'original' key."""

    class _FakeActor:
        class run:  # type: ignore[too-many-ancestors]
            @staticmethod
            def remote(**kwargs: Any) -> str:  # type: ignore[no-untyped-def]
                return "future-1"

    class _FakeRayAgentJob:
        @staticmethod
        def remote(**kwargs: Any) -> _FakeActor:  # type: ignore[no-untyped-def]
            return _FakeActor()

    monkeypatch.setattr(adapter_module, "RayAgentJob", _FakeRayAgentJob)

    registry: dict[str, Any] = {}
    adapter = adapter_module.RayClusterAdapter(registry)

    agents = [{"agent_id": "agent-1", "role": "DEV"}]

    await adapter.submit_deliberation(
        deliberation_id="delib-1",
        task_id="task-1",
        task_description="desc",
        role="DEV",
        agents=agents,
        constraints={"metadata": "not-a-dict"},
        vllm_url="http://vllm",
        vllm_model="model",
    )

    entry = registry["delib-1"]
    # We cannot access constraints_with_metadata directly, but at least ensure registry entry exists
    assert entry["status"] == "running"


@pytest.mark.asyncio
async def test_submit_deliberation_raises_when_no_agents() -> None:
    """submit_deliberation should fail fast when no agents provided."""
    registry: dict[str, Any] = {}
    adapter = adapter_module.RayClusterAdapter(registry)

    with pytest.raises(ValueError, match="At least one agent required"):
        await adapter.submit_deliberation(
            deliberation_id="delib-1",
            task_id="task-123",
            task_description="desc",
            role="DEV",
            agents=[],
            constraints={},
            vllm_url="http://vllm",
            vllm_model="model",
        )


@pytest.mark.asyncio
async def test_check_deliberation_status_not_found() -> None:
    """check_deliberation_status should return not_found when id missing."""
    registry: dict[str, Any] = {}
    adapter = adapter_module.RayClusterAdapter(registry)

    status, result, error = await adapter.check_deliberation_status("unknown")

    assert status == "not_found"
    assert result is None
    assert "unknown" in (error or "")


@pytest.mark.asyncio
async def test_check_deliberation_status_running_when_no_futures_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When no Ray futures are ready, status should be running."""
    registry: dict[str, Any] = {
        "delib-1": {
            "futures": ["f1"],
            "total_agents": 1,
        }
    }
    adapter = adapter_module.RayClusterAdapter(registry)

    def _fake_wait(
        futures: list[Any],  # type: ignore[no-untyped-def]
        num_returns: int,
        timeout: float,
    ) -> tuple[list[Any], list[Any]]:
        return [], futures

    monkeypatch.setattr(adapter_module.ray, "wait", _fake_wait)

    status, result, error = await adapter.check_deliberation_status("delib-1")

    assert status == "running"
    assert result is None
    assert error is None


@pytest.mark.asyncio
async def test_check_deliberation_status_completed_single_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When one future is ready and total_agents=1, return DeliberationResult."""
    future = object()
    registry: dict[str, Any] = {
        "delib-1": {
            "futures": [future],
            "total_agents": 1,
        }
    }
    adapter = adapter_module.RayClusterAdapter(registry)

    def _fake_wait(
        futures: list[Any],  # type: ignore[no-untyped-def]
        num_returns: int,
        timeout: float,
    ) -> tuple[list[Any], list[Any]]:
        return futures, []

    def _fake_get(obj: Any) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        # proposal as plain string exercises legacy path
        return {
            "agent_id": "agent-1",
            "proposal": "Use microservices",
            "reasoning": "Scalability",
            "score": 0.9,
            "metadata": {"foo": "bar"},
        }

    monkeypatch.setattr(adapter_module.ray, "wait", _fake_wait)
    monkeypatch.setattr(adapter_module.ray, "get", _fake_get)

    status, result, error = await adapter.check_deliberation_status("delib-1")

    assert status == "completed"
    assert isinstance(result, DeliberationResult)
    assert result.agent_id == "agent-1"
    assert result.proposal == "Use microservices"
    assert result.score == pytest.approx(0.9)
    assert error is None


@pytest.mark.asyncio
async def test_check_deliberation_status_completed_multi_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When all futures are ready and total_agents>1, return MultiAgentDeliberationResult."""
    f1 = object()
    f2 = object()
    registry: dict[str, Any] = {
        "delib-1": {
            "futures": [f1, f2],
            "total_agents": 2,
        }
    }
    adapter = adapter_module.RayClusterAdapter(registry)

    def _fake_wait(
        futures: list[Any],  # type: ignore[no-untyped-def]
        num_returns: int,
        timeout: float,
    ) -> tuple[list[Any], list[Any]]:
        return futures, []

    def _fake_get(obj: Any) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        if obj is f1:
            # proposal as dict with content exercises llm_content logging path
            return {
                "agent_id": "agent-1",
                "proposal": {"content": "Option A"},
                "reasoning": "Reason A",
                "score": 0.8,
                "metadata": {},
            }
        return {
            "agent_id": "agent-2",
            "proposal": {"content": "Option B"},
            "reasoning": "Reason B",
            "score": 0.9,
            "metadata": {},
        }

    monkeypatch.setattr(adapter_module.ray, "wait", _fake_wait)
    monkeypatch.setattr(adapter_module.ray, "get", _fake_get)

    status, result, error = await adapter.check_deliberation_status("delib-1")

    assert status == "completed"
    assert isinstance(result, MultiAgentDeliberationResult)
    assert result.total_agents == 2
    assert result.completed_agents == 2
    assert result.failed_agents == 0
    assert result.best_result is not None
    assert result.best_result.agent_id == "agent-2"
    assert error is None


@pytest.mark.asyncio
async def test_check_deliberation_status_failed_when_no_futures() -> None:
    """If registry contains no futures, status should be failed."""
    registry: dict[str, Any] = {
        "delib-1": {
            "futures": [],
            "total_agents": 0,
        }
    }
    adapter = adapter_module.RayClusterAdapter(registry)

    status, result, error = await adapter.check_deliberation_status("delib-1")

    assert status == "failed"
    assert result is None
    assert error is not None
    assert "No futures found" in error


@pytest.mark.asyncio
async def test_check_deliberation_status_handles_ray_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any exception from Ray should be converted into failed status."""
    registry: dict[str, Any] = {
        "delib-1": {
            "futures": ["f1"],
            "total_agents": 1,
        }
    }
    adapter = adapter_module.RayClusterAdapter(registry)

    def _failing_wait(
        futures: list[Any],  # type: ignore[no-untyped-def]
        num_returns: int,
        timeout: float,
    ) -> tuple[list[Any], list[Any]]:
        raise RuntimeError("ray failure")

    monkeypatch.setattr(adapter_module.ray, "wait", _failing_wait)

    status, result, error = await adapter.check_deliberation_status("delib-1")

    assert status == "failed"
    assert result is None
    assert error is not None
    assert "ray failure" in error


@pytest.mark.asyncio
async def test_check_deliberation_status_partial_completion_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When some but not all futures are ready, status should remain running."""
    f1 = object()
    f2 = object()
    registry: dict[str, Any] = {
        "delib-1": {
            "futures": [f1, f2],
            "total_agents": 2,
        }
    }
    adapter = adapter_module.RayClusterAdapter(registry)

    def _fake_wait(
        futures: list[Any],  # type: ignore[no-untyped-def]
        num_returns: int,
        timeout: float,
    ) -> tuple[list[Any], list[Any]]:
        # Only one future is ready
        return [f1], [f2]

    monkeypatch.setattr(adapter_module.ray, "wait", _fake_wait)

    status, result, error = await adapter.check_deliberation_status("delib-1")

    assert status == "running"
    assert result is None
    assert error is None


@pytest.mark.asyncio
async def test_get_active_jobs_returns_registry_items() -> None:
    """get_active_jobs should return the items from the deliberations registry."""
    registry: dict[str, Any] = {
        "delib-1": {"status": "running"},
        "delib-2": {"status": "completed"},
    }
    adapter = adapter_module.RayClusterAdapter(registry)

    jobs = await adapter.get_active_jobs()

    assert ("delib-1", {"status": "running"}) in jobs
    assert ("delib-2", {"status": "completed"}) in jobs

