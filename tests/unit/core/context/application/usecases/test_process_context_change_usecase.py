"""Unit tests for ProcessContextChangeUseCase."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from core.context.application.usecases.process_context_change import ProcessContextChangeUseCase


@pytest.mark.asyncio
async def test_validate_required_fields():
    """Test that missing required fields raise ValueError."""
    # Arrange
    decision_uc = AsyncMock()
    task_uc = AsyncMock()
    story_uc = AsyncMock()
    plan_uc = AsyncMock()
    milestone_uc = AsyncMock()

    use_case = ProcessContextChangeUseCase(
        decision_uc=decision_uc,
        task_uc=task_uc,
        story_uc=story_uc,
        plan_uc=plan_uc,
        milestone_uc=milestone_uc,
    )

    # Test missing operation
    change = Mock()
    change.operation = ""
    change.entity_type = "DECISION"
    change.entity_id = "DEC-001"
    change.payload = ""

    with pytest.raises(ValueError, match="Missing required fields"):
        await use_case.execute(change, "TEST-001")


@pytest.mark.asyncio
async def test_route_to_decision_handler():
    """Test that DECISION entity routes to decision_uc."""
    # Arrange
    decision_uc = AsyncMock()
    task_uc = AsyncMock()
    story_uc = AsyncMock()
    plan_uc = AsyncMock()
    milestone_uc = AsyncMock()

    use_case = ProcessContextChangeUseCase(
        decision_uc=decision_uc,
        task_uc=task_uc,
        story_uc=story_uc,
        plan_uc=plan_uc,
        milestone_uc=milestone_uc,
    )

    change = Mock()
    change.operation = "CREATE"
    change.entity_type = "DECISION"
    change.entity_id = "DEC-001"
    change.payload = json.dumps({"title": "Test Decision"})

    # Act
    await use_case.execute(change, "TEST-001")

    # Assert
    decision_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_route_to_subtask_handler():
    """Test that SUBTASK entity routes to task_uc."""
    # Arrange
    decision_uc = AsyncMock()
    task_uc = AsyncMock()
    story_uc = AsyncMock()
    plan_uc = AsyncMock()
    milestone_uc = AsyncMock()

    use_case = ProcessContextChangeUseCase(
        decision_uc=decision_uc,
        task_uc=task_uc,
        story_uc=story_uc,
        plan_uc=plan_uc,
        milestone_uc=milestone_uc,
    )

    change = Mock()
    change.operation = "CREATE"
    change.entity_type = "SUBTASK"
    change.entity_id = "SUB-001"
    change.payload = json.dumps({"title": "Test Subtask"})

    # Act
    await use_case.execute(change, "TEST-001")

    # Assert
    task_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_route_to_milestone_handler():
    """Test that MILESTONE entity routes to milestone_uc."""
    # Arrange
    decision_uc = AsyncMock()
    task_uc = AsyncMock()
    story_uc = AsyncMock()
    plan_uc = AsyncMock()
    milestone_uc = AsyncMock()

    use_case = ProcessContextChangeUseCase(
        decision_uc=decision_uc,
        task_uc=task_uc,
        story_uc=story_uc,
        plan_uc=plan_uc,
        milestone_uc=milestone_uc,
    )

    change = Mock()
    change.operation = "CREATE"
    change.entity_type = "MILESTONE"
    change.entity_id = "MILE-001"
    change.payload = json.dumps({"description": "Test Milestone"})

    # Act
    await use_case.execute(change, "TEST-001")

    # Assert
    milestone_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_route_to_case_handler():
    """Test that CASE entity routes to story_uc."""
    # Arrange
    decision_uc = AsyncMock()
    task_uc = AsyncMock()
    story_uc = AsyncMock()
    plan_uc = AsyncMock()
    milestone_uc = AsyncMock()

    use_case = ProcessContextChangeUseCase(
        decision_uc=decision_uc,
        task_uc=task_uc,
        story_uc=story_uc,
        plan_uc=plan_uc,
        milestone_uc=milestone_uc,
    )

    change = Mock()
    change.operation = "CREATE"
    change.entity_type = "CASE"
    change.entity_id = "CASE-001"
    change.payload = json.dumps({"title": "Test Case"})

    # Act
    await use_case.execute(change, "TEST-001")

    # Assert
    story_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_route_to_plan_handler():
    """Test that PLAN entity routes to plan_uc."""
    # Arrange
    decision_uc = AsyncMock()
    task_uc = AsyncMock()
    story_uc = AsyncMock()
    plan_uc = AsyncMock()
    milestone_uc = AsyncMock()

    use_case = ProcessContextChangeUseCase(
        decision_uc=decision_uc,
        task_uc=task_uc,
        story_uc=story_uc,
        plan_uc=plan_uc,
        milestone_uc=milestone_uc,
    )

    change = Mock()
    change.operation = "CREATE"
    change.entity_type = "PLAN"
    change.entity_id = "PLAN-001"
    change.payload = json.dumps({"version": 1})

    # Act
    await use_case.execute(change, "TEST-001")

    # Assert
    plan_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_unknown_entity_type():
    """Test that unknown entity type raises ValueError."""
    # Arrange
    decision_uc = AsyncMock()
    task_uc = AsyncMock()
    story_uc = AsyncMock()
    plan_uc = AsyncMock()
    milestone_uc = AsyncMock()

    use_case = ProcessContextChangeUseCase(
        decision_uc=decision_uc,
        task_uc=task_uc,
        story_uc=story_uc,
        plan_uc=plan_uc,
        milestone_uc=milestone_uc,
    )

    change = Mock()
    change.operation = "CREATE"
    change.entity_type = "UNKNOWN"
    change.entity_id = "UNK-001"
    change.payload = "{}"

    # Act & Assert
    with pytest.raises(ValueError, match="Unknown entity type"):
        await use_case.execute(change, "TEST-001")


@pytest.mark.asyncio
async def test_handle_persistence_error_gracefully():
    """Test that persistence errors propagate correctly."""
    # Arrange
    decision_uc = AsyncMock()
    decision_uc.execute.side_effect = Exception("Database error")

    use_case = ProcessContextChangeUseCase(
        decision_uc=decision_uc,
        task_uc=AsyncMock(),
        story_uc=AsyncMock(),
        plan_uc=AsyncMock(),
        milestone_uc=AsyncMock(),
    )

    change = Mock()
    change.operation = "CREATE"
    change.entity_type = "DECISION"
    change.entity_id = "DEC-001"
    change.payload = json.dumps({"title": "Test"})

    # Act & Assert - error should propagate
    with pytest.raises(Exception, match="Database error"):
        await use_case.execute(change, "TEST-001")


@pytest.mark.asyncio
async def test_parse_json_payload():
    """Test that JSON payload is parsed correctly."""
    # Arrange
    decision_uc = AsyncMock()

    use_case = ProcessContextChangeUseCase(
        decision_uc=decision_uc,
        task_uc=AsyncMock(),
        story_uc=AsyncMock(),
        plan_uc=AsyncMock(),
        milestone_uc=AsyncMock(),
    )

    change = Mock()
    change.operation = "CREATE"
    change.entity_type = "DECISION"
    change.entity_id = "DEC-001"
    change.payload = json.dumps({"title": "Test Decision", "status": "PROPOSED"})

    # Act
    await use_case.execute(change, "TEST-001")

    # Assert - payload should be parsed and passed to use case as dict
    decision_uc.execute.assert_awaited_once()
    call_args = decision_uc.execute.call_args[0][0]  # First positional arg is the dict
    assert "title" in call_args
    assert call_args["title"] == "Test Decision"
    assert call_args["node_id"] == "DEC-001"
    assert call_args["case_id"] == "TEST-001"


@pytest.mark.asyncio
async def test_invalid_json_payload():
    """Test that invalid JSON raises ValueError."""
    # Arrange
    use_case = ProcessContextChangeUseCase(
        decision_uc=AsyncMock(),
        task_uc=AsyncMock(),
        story_uc=AsyncMock(),
        plan_uc=AsyncMock(),
        milestone_uc=AsyncMock(),
    )

    change = Mock()
    change.operation = "CREATE"
    change.entity_type = "DECISION"
    change.entity_id = "DEC-001"
    change.payload = "invalid json{"

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid JSON payload"):
        await use_case.execute(change, "TEST-001")

