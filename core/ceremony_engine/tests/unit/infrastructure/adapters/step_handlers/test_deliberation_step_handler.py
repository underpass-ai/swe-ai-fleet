"""Unit tests for DeliberationStepHandler."""

import pytest
from unittest.mock import AsyncMock

from core.ceremony_engine.application.ports.deliberation_port import DeliberationPort
from core.ceremony_engine.application.use_cases.submit_deliberation_usecase import (
    SubmitDeliberationUseCase,
)
from core.ceremony_engine.domain.value_objects import (
    ContextEntry,
    ContextKey,
    ExecutionContext,
    Step,
    StepHandlerType,
    StepId,
    StepStatus,
)
from core.ceremony_engine.infrastructure.adapters.step_handlers.deliberation_step_handler import (
    DeliberationStepHandler,
)


@pytest.mark.asyncio
async def test_execute_deliberation_happy_path() -> None:
    """Test executing deliberation step successfully."""
    deliberation_port = AsyncMock(spec=DeliberationPort)
    deliberation_port.submit_backlog_review_deliberation.return_value = "delib-123"
    use_case = SubmitDeliberationUseCase(deliberation_port)
    handler = DeliberationStepHandler(use_case)
    step = Step(
        id=StepId("deliberate"),
        state="STARTED",
        handler=StepHandlerType.DELIBERATION_STEP,
        config={"prompt": "What should we build?", "role": "ARCHITECT", "num_agents": 2},
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"story_id": "story-1", "ceremony_id": "cer-1"},
            ),
        )
    )
    result = await handler.execute(step, context)

    assert result.status == StepStatus.COMPLETED
    assert result.output["deliberation_id"] == "delib-123"
    assert result.output["role"] == "ARCHITECT"
    assert result.output["num_agents"] == 2
    deliberation_port.submit_backlog_review_deliberation.assert_awaited_once_with(
        task_id="ceremony-cer-1:story-story-1:role-ARCHITECT",
        task_description="What should we build?",
        role="ARCHITECT",
        story_id="story-1",
        num_agents=2,
        constraints=None,
    )


@pytest.mark.asyncio
async def test_execute_deliberation_missing_prompt() -> None:
    """Test executing deliberation step with missing prompt."""
    handler = DeliberationStepHandler(
        SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort))
    )
    # Step validation requires non-empty config, so we need to provide at least one key
    step = Step(
        id=StepId("deliberate"),
        state="STARTED",
        handler=StepHandlerType.DELIBERATION_STEP,
        config={"other_key": "value"},  # Missing prompt
    )

    with pytest.raises(ValueError, match="missing required keys"):
        await handler.execute(step, ExecutionContext.empty())


@pytest.mark.asyncio
async def test_execute_deliberation_with_agents() -> None:
    """Test executing deliberation step with agents."""
    deliberation_port = AsyncMock(spec=DeliberationPort)
    deliberation_port.submit_backlog_review_deliberation.return_value = "delib-456"
    handler = DeliberationStepHandler(SubmitDeliberationUseCase(deliberation_port))
    step = Step(
        id=StepId("deliberate"),
        state="STARTED",
        handler=StepHandlerType.DELIBERATION_STEP,
        config={
            "prompt": "What should we build?",
            "role": "QA",
            "num_agents": 3,
        },
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"story_id": "story-2", "ceremony_id": "cer-2"},
            ),
        )
    )
    result = await handler.execute(step, context)

    assert result.status == StepStatus.COMPLETED
    assert result.output["deliberation_id"] == "delib-456"
    assert result.output["role"] == "QA"
    assert result.output["num_agents"] == 3


def test_deliberation_handler_requires_deliberation_use_case() -> None:
    """Test handler rejects missing deliberation use case."""
    with pytest.raises(ValueError, match="deliberation_use_case is required"):
        DeliberationStepHandler(None)  # type: ignore[arg-type]
