"""Unit tests for SubmitDeliberationUseCase."""

import pytest
from unittest.mock import AsyncMock

from core.ceremony_engine.application.ports.deliberation_port import DeliberationPort
from core.ceremony_engine.application.use_cases.submit_deliberation_usecase import (
    SubmitDeliberationUseCase,
)


@pytest.mark.asyncio
async def test_submit_deliberation_happy_path() -> None:
    deliberation_port = AsyncMock(spec=DeliberationPort)
    deliberation_port.submit_backlog_review_deliberation.return_value = "delib-1"
    use_case = SubmitDeliberationUseCase(deliberation_port)

    result = await use_case.execute(
        task_id="ceremony-1:story-1:role-DEV",
        task_description="Analyze the story",
        role="DEV",
        story_id="story-1",
        num_agents=3,
        constraints={"plan_id": "plan-1"},
    )

    assert result["deliberation_id"] == "delib-1"
    assert result["status"] == "submitted"
    deliberation_port.submit_backlog_review_deliberation.assert_awaited_once_with(
        task_id="ceremony-1:story-1:role-DEV",
        task_description="Analyze the story",
        role="DEV",
        story_id="story-1",
        num_agents=3,
        constraints={"plan_id": "plan-1"},
    )


@pytest.mark.asyncio
async def test_submit_deliberation_rejects_empty_task_id() -> None:
    use_case = SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort))
    with pytest.raises(ValueError, match="task_id cannot be empty"):
        await use_case.execute(
            task_id="",
            task_description="desc",
            role="DEV",
            story_id="story-1",
            num_agents=1,
        )


@pytest.mark.asyncio
async def test_submit_deliberation_rejects_invalid_num_agents() -> None:
    use_case = SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort))
    with pytest.raises(ValueError, match="num_agents must be positive"):
        await use_case.execute(
            task_id="t1",
            task_description="desc",
            role="DEV",
            story_id="story-1",
            num_agents=0,
        )


def test_submit_deliberation_requires_port() -> None:
    with pytest.raises(ValueError, match="deliberation_port is required"):
        SubmitDeliberationUseCase(None)  # type: ignore[arg-type]
