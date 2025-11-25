"""Unit tests for process_result_handler."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from task_derivation.application.usecases.process_task_derivation_result_usecase import (
    ProcessTaskDerivationResultUseCase,
)
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.dependency.task_node import (
    TaskNode,
)
from task_derivation.infrastructure.handlers.process_result_handler import (
    process_result_handler,
)


@pytest.mark.asyncio
async def test_process_result_handler_success() -> None:
    """Test handler successfully processes valid payload."""
    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    use_case.execute = AsyncMock(return_value=None)

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {
            "proposal": "TITLE: Task 1\nDESCRIPTION: Do work\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: work",
        },
    }

    # Act
    await process_result_handler(payload, use_case)

    # Assert
    use_case.execute.assert_awaited_once()
    call_kwargs = use_case.execute.call_args[1]
    assert call_kwargs["plan_id"].value == "plan-1"
    assert call_kwargs["story_id"].value == "story-1"
    assert call_kwargs["role"].value == "DEVELOPER"
    assert len(call_kwargs["task_nodes"]) > 0


@pytest.mark.asyncio
async def test_process_result_handler_missing_plan_id() -> None:
    """Test handler raises ValueError for missing plan_id."""
    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    payload = {
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {"proposal": "TITLE: Task"},
    }

    # Act & Assert
    with pytest.raises(ValueError, match="plan_id missing"):
        await process_result_handler(payload, use_case)

    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_result_handler_missing_story_id() -> None:
    """Test handler raises ValueError for missing story_id."""
    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    payload = {
        "plan_id": "plan-1",
        "role": "DEVELOPER",
        "result": {"proposal": "TITLE: Task"},
    }

    # Act & Assert
    with pytest.raises(ValueError, match="story_id missing"):
        await process_result_handler(payload, use_case)

    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_result_handler_empty_llm_text() -> None:
    """Test handler raises ValueError for empty LLM proposal text."""
    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {"proposal": ""},
    }

    # Act & Assert
    with pytest.raises(ValueError, match="LLM proposal text is empty"):
        await process_result_handler(payload, use_case)

    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_result_handler_missing_result_key() -> None:
    """Test handler raises ValueError when result key is missing."""
    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
    }

    # Act & Assert
    with pytest.raises(ValueError, match="LLM proposal text is empty"):
        await process_result_handler(payload, use_case)

    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_result_handler_no_tasks_parsed() -> None:
    """Test handler raises ValueError when no tasks are parsed from LLM text."""
    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {
            "proposal": "Invalid format that cannot be parsed",
        },
    }

    # Act & Assert
    # Mapper raises ValueError("No valid tasks parsed from LLM output") when parsing fails
    with pytest.raises(ValueError, match="No valid tasks parsed"):
        await process_result_handler(payload, use_case)

    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_result_handler_default_role() -> None:
    """Test handler uses default role when not provided."""
    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    use_case.execute = AsyncMock(return_value=None)

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "result": {
            "proposal": "TITLE: Task 1\nDESCRIPTION: Do work\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: work",
        },
    }

    # Act
    await process_result_handler(payload, use_case)

    # Assert
    use_case.execute.assert_awaited_once()
    call_kwargs = use_case.execute.call_args[1]
    assert call_kwargs["role"].value == "DEVELOPER"  # Default role


@pytest.mark.asyncio
async def test_process_result_handler_use_case_raises_value_error() -> None:
    """Test handler re-raises ValueError from use case."""
    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    use_case.execute = AsyncMock(side_effect=ValueError("task_nodes cannot be empty"))

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {
            "proposal": "TITLE: Task 1\nDESCRIPTION: Do work\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: work",
        },
    }

    # Act & Assert
    with pytest.raises(ValueError, match="task_nodes cannot be empty"):
        await process_result_handler(payload, use_case)

    use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_result_handler_use_case_raises_generic_exception() -> None:
    """Test handler re-raises generic exception from use case."""
    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    use_case.execute = AsyncMock(side_effect=RuntimeError("Planning service error"))

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {
            "proposal": "TITLE: Task 1\nDESCRIPTION: Do work\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: work",
        },
    }

    # Act & Assert
    with pytest.raises(RuntimeError, match="Planning service error"):
        await process_result_handler(payload, use_case)

    use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_result_handler_logs_info_on_success(caplog) -> None:
    """Test handler logs info messages on successful processing."""
    import logging

    caplog.set_level(logging.INFO)

    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    use_case.execute = AsyncMock(return_value=None)

    payload = {
        "plan_id": "plan-999",
        "story_id": "story-999",
        "role": "QA",
        "result": {
            "proposal": "TITLE: Task 1\nDESCRIPTION: Do work\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: work",
        },
    }

    # Act
    await process_result_handler(payload, use_case)

    # Assert
    assert "Handling agent.response.completed" in caplog.text
    assert "plan_id=plan-999" in caplog.text
    assert "story_id=story-999" in caplog.text
    assert "Task derivation result processed" in caplog.text


@pytest.mark.asyncio
async def test_process_result_handler_logs_error_on_failure(caplog) -> None:
    """Test handler logs error messages on failure."""
    import logging

    caplog.set_level(logging.ERROR)

    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    payload = {
        "plan_id": "plan-1",
        # Missing story_id
        "role": "DEVELOPER",
        "result": {"proposal": "TITLE: Task"},
    }

    # Act
    with pytest.raises(ValueError):
        await process_result_handler(payload, use_case)

    # Assert
    assert "Invalid derivation result payload" in caplog.text


@pytest.mark.asyncio
async def test_process_result_handler_with_multiple_tasks() -> None:
    """Test handler processes payload with multiple tasks."""
    # Arrange
    use_case = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    use_case.execute = AsyncMock(return_value=None)

    payload = {
        "plan_id": "plan-2",
        "story_id": "story-2",
        "role": "DEVELOPER",
        "result": {
            "proposal": (
                "TITLE: Task 1\nDESCRIPTION: First task\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: task1\n"
                "---\n"
                "TITLE: Task 2\nDESCRIPTION: Second task\nESTIMATED_HOURS: 16\nPRIORITY: 2\nKEYWORDS: task2"
            ),
        },
    }

    # Act
    await process_result_handler(payload, use_case)

    # Assert
    use_case.execute.assert_awaited_once()
    call_kwargs = use_case.execute.call_args[1]
    assert len(call_kwargs["task_nodes"]) == 2

