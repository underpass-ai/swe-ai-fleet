"""Unit tests for SubmitTaskExtractionUseCase."""

import pytest
from unittest.mock import AsyncMock

from core.ceremony_engine.application.ports.task_extraction_port import TaskExtractionPort
from core.ceremony_engine.application.use_cases.submit_task_extraction_usecase import (
    SubmitTaskExtractionUseCase,
)


@pytest.mark.asyncio
async def test_submit_task_extraction_happy_path() -> None:
    task_extraction_port = AsyncMock(spec=TaskExtractionPort)
    task_extraction_port.submit_task_extraction.return_value = "delib-2"
    use_case = SubmitTaskExtractionUseCase(task_extraction_port)

    result = await use_case.execute(
        ceremony_id="cer-1",
        story_id="story-1",
        agent_deliberations=[
            {"agent_id": "a1", "role": "DEV", "proposal": {"content": "Plan A"}},
            {"agent_id": "a2", "role": "QA", "proposal": {"content": "Plan B"}},
        ],
    )

    assert result["deliberation_id"] == "delib-2"
    assert result["status"] == "submitted"
    task_extraction_port.submit_task_extraction.assert_awaited_once()
    called_kwargs = task_extraction_port.submit_task_extraction.call_args.kwargs
    assert called_kwargs["task_id"] == "ceremony-cer-1:story-story-1:task-extraction"
    assert called_kwargs["story_id"] == "story-1"
    assert called_kwargs["ceremony_id"] == "cer-1"
    assert "Story ID: story-1" in called_kwargs["task_description"]


@pytest.mark.asyncio
async def test_submit_task_extraction_rejects_empty_ceremony_id() -> None:
    use_case = SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort))
    with pytest.raises(ValueError, match="ceremony_id cannot be empty"):
        await use_case.execute(
            ceremony_id="",
            story_id="story-1",
            agent_deliberations=[{"agent_id": "a1"}],
        )


@pytest.mark.asyncio
async def test_submit_task_extraction_rejects_empty_deliberations() -> None:
    use_case = SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort))
    with pytest.raises(ValueError, match="agent_deliberations cannot be empty"):
        await use_case.execute(
            ceremony_id="cer-1",
            story_id="story-1",
            agent_deliberations=[],
        )


def test_submit_task_extraction_requires_port() -> None:
    with pytest.raises(ValueError, match="task_extraction_port is required"):
        SubmitTaskExtractionUseCase(None)  # type: ignore[arg-type]
