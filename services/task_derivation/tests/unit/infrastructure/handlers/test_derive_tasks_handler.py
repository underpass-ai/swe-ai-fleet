"""Unit tests for derive_tasks_handler."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from task_derivation.application.usecases.derive_tasks_usecase import (
    DeriveTasksUseCase,
)
from task_derivation.domain.value_objects.task_derivation.requests.derivation_request_id import (
    DerivationRequestId,
)
from task_derivation.infrastructure.handlers.derive_tasks_handler import (
    derive_tasks_handler,
)


@pytest.mark.asyncio
async def test_derive_tasks_handler_success() -> None:
    """Test handler successfully processes valid payload."""
    # Arrange
    use_case = AsyncMock(spec=DeriveTasksUseCase)
    request_id = DerivationRequestId("req-123")
    use_case.execute = AsyncMock(return_value=request_id)

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "roles": ["DEVELOPER"],
        "requested_by": "user-1",
    }

    # Act
    await derive_tasks_handler(payload, use_case)

    # Assert
    use_case.execute.assert_awaited_once()
    call_args = use_case.execute.call_args[0][0]
    assert call_args.plan_id.value == "plan-1"
    assert call_args.story_id.value == "story-1"
    assert len(call_args.roles) == 1
    assert call_args.roles[0].value == "DEVELOPER"


@pytest.mark.asyncio
async def test_derive_tasks_handler_with_multiple_roles() -> None:
    """Test handler processes payload with multiple roles."""
    # Arrange
    use_case = AsyncMock(spec=DeriveTasksUseCase)
    request_id = DerivationRequestId("req-456")
    use_case.execute = AsyncMock(return_value=request_id)

    payload = {
        "plan_id": "plan-2",
        "story_id": "story-2",
        "roles": ["DEVELOPER", "QA"],
        "requested_by": "user-2",
    }

    # Act
    await derive_tasks_handler(payload, use_case)

    # Assert
    use_case.execute.assert_awaited_once()
    call_args = use_case.execute.call_args[0][0]
    assert len(call_args.roles) == 2
    assert call_args.roles[0].value == "DEVELOPER"
    assert call_args.roles[1].value == "QA"


@pytest.mark.asyncio
async def test_derive_tasks_handler_missing_plan_id() -> None:
    """Test handler raises ValueError for missing plan_id."""
    # Arrange
    use_case = AsyncMock(spec=DeriveTasksUseCase)
    payload = {
        "story_id": "story-1",
        "roles": ["DEVELOPER"],
        "requested_by": "user-1",
    }

    # Act & Assert
    with pytest.raises(ValueError, match="plan_id"):
        await derive_tasks_handler(payload, use_case)

    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_derive_tasks_handler_missing_story_id() -> None:
    """Test handler raises ValueError for missing story_id."""
    # Arrange
    use_case = AsyncMock(spec=DeriveTasksUseCase)
    payload = {
        "plan_id": "plan-1",
        "roles": ["DEVELOPER"],
        "requested_by": "user-1",
    }

    # Act & Assert
    with pytest.raises(ValueError, match="story_id"):
        await derive_tasks_handler(payload, use_case)

    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_derive_tasks_handler_empty_roles() -> None:
    """Test handler handles empty roles (uses default)."""
    # Arrange
    use_case = AsyncMock(spec=DeriveTasksUseCase)
    request_id = DerivationRequestId("req-789")
    use_case.execute = AsyncMock(return_value=request_id)

    payload = {
        "plan_id": "plan-3",
        "story_id": "story-3",
        "roles": [],
        "requested_by": "user-3",
    }

    # Act
    await derive_tasks_handler(payload, use_case)

    # Assert
    use_case.execute.assert_awaited_once()
    call_args = use_case.execute.call_args[0][0]
    # Should use default role when empty
    assert len(call_args.roles) == 1
    assert call_args.roles[0].value == "DEVELOPER"


@pytest.mark.asyncio
async def test_derive_tasks_handler_use_case_raises_value_error() -> None:
    """Test handler re-raises ValueError from use case."""
    # Arrange
    use_case = AsyncMock(spec=DeriveTasksUseCase)
    use_case.execute = AsyncMock(side_effect=ValueError("Invalid plan"))

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "roles": ["DEVELOPER"],
        "requested_by": "user-1",
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid plan"):
        await derive_tasks_handler(payload, use_case)

    use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_derive_tasks_handler_use_case_raises_generic_exception() -> None:
    """Test handler re-raises generic exception from use case."""
    # Arrange
    use_case = AsyncMock(spec=DeriveTasksUseCase)
    use_case.execute = AsyncMock(side_effect=RuntimeError("Network error"))

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "roles": ["DEVELOPER"],
        "requested_by": "user-1",
    }

    # Act & Assert
    with pytest.raises(RuntimeError, match="Network error"):
        await derive_tasks_handler(payload, use_case)

    use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_derive_tasks_handler_logs_info_on_success(caplog) -> None:
    """Test handler logs info messages on successful processing."""
    import logging

    caplog.set_level(logging.INFO)

    # Arrange
    use_case = AsyncMock(spec=DeriveTasksUseCase)
    request_id = DerivationRequestId("req-999")
    use_case.execute = AsyncMock(return_value=request_id)

    payload = {
        "plan_id": "plan-999",
        "story_id": "story-999",
        "roles": ["DEVELOPER"],
        "requested_by": "user-999",
    }

    # Act
    await derive_tasks_handler(payload, use_case)

    # Assert
    assert "Handling task.derivation.requested" in caplog.text
    assert "plan_id=plan-999" in caplog.text
    assert "story_id=story-999" in caplog.text
    assert "Task derivation job submitted" in caplog.text
    assert "request_id=req-999" in caplog.text


@pytest.mark.asyncio
async def test_derive_tasks_handler_logs_error_on_failure(caplog) -> None:
    """Test handler logs error messages on failure."""
    import logging

    caplog.set_level(logging.ERROR)

    # Arrange
    use_case = AsyncMock(spec=DeriveTasksUseCase)
    use_case.execute = AsyncMock(side_effect=ValueError("Invalid payload"))

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "roles": ["DEVELOPER"],
        "requested_by": "user-1",
    }

    # Act
    with pytest.raises(ValueError):
        await derive_tasks_handler(payload, use_case)

    # Assert
    assert "Invalid derivation request payload" in caplog.text




