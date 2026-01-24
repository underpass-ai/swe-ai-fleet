"""Unit tests for TaskExtractionStepHandler."""

import pytest
from unittest.mock import ANY, AsyncMock

from core.ceremony_engine.application.ports.task_extraction_port import TaskExtractionPort
from core.ceremony_engine.application.use_cases.submit_task_extraction_usecase import (
    SubmitTaskExtractionUseCase,
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
from core.ceremony_engine.infrastructure.adapters.step_handlers.task_extraction_step_handler import (
    TaskExtractionStepHandler,
)


@pytest.mark.asyncio
async def test_execute_task_extraction_happy_path() -> None:
    """Test executing task extraction step successfully."""
    task_extraction_port = AsyncMock(spec=TaskExtractionPort)
    task_extraction_port.submit_task_extraction.return_value = "delib-789"
    handler = TaskExtractionStepHandler(SubmitTaskExtractionUseCase(task_extraction_port))
    step = Step(
        id=StepId("extract_tasks"),
        state="STARTED",
        handler=StepHandlerType.TASK_EXTRACTION_STEP,
        config={"source": "artifact-1"},
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={
                    "story_id": "story-1",
                    "ceremony_id": "cer-1",
                    "agent_deliberations": [
                        {"agent_id": "a1", "role": "DEV", "proposal": {"content": "x"}},
                    ],
                },
            ),
        )
    )
    result = await handler.execute(step, context)

    assert result.status == StepStatus.COMPLETED
    assert result.output["source"] == "artifact-1"
    assert result.output["deliberation_id"] == "delib-789"
    assert result.output["status"] == "submitted"
    task_extraction_port.submit_task_extraction.assert_awaited_once_with(
        task_id="ceremony-cer-1:story-story-1:task-extraction",
        task_description=ANY,
        story_id="story-1",
        ceremony_id="cer-1",
    )


@pytest.mark.asyncio
async def test_execute_task_extraction_missing_source() -> None:
    """Test executing task extraction step with missing source."""
    handler = TaskExtractionStepHandler(
        SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort))
    )
    step = Step(
        id=StepId("extract_tasks"),
        state="STARTED",
        handler=StepHandlerType.TASK_EXTRACTION_STEP,
        config={"other_key": "value"},
    )

    with pytest.raises(ValueError, match="missing required keys"):
        await handler.execute(step, ExecutionContext.empty())


def test_task_extraction_handler_requires_task_extraction_use_case() -> None:
    """Test handler rejects missing task extraction use case."""
    with pytest.raises(ValueError, match="task_extraction_use_case is required"):
        TaskExtractionStepHandler(None)  # type: ignore[arg-type]
