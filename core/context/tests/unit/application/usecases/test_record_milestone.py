"""Unit tests for RecordMilestoneUseCase."""

from unittest.mock import Mock

import pytest

from core.context.application.usecases.record_milestone import RecordMilestoneUseCase

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_execute_calls_upsert_entity() -> None:
    """Execute calls graph.upsert_entity with Event label and properties."""
    graph_command = Mock()
    use_case = RecordMilestoneUseCase(graph_command=graph_command)

    await use_case.execute(
        milestone_id="M-1",
        story_id="s-1",
        event_type="review_started",
        description="First review",
        timestamp_ms=1234567890,
    )

    graph_command.upsert_entity.assert_called_once()
    call_args = graph_command.upsert_entity.call_args
    assert call_args[0][0] == "Event"
    assert call_args[0][1] == "M-1"
    assert call_args[0][2] == {
        "id": "M-1",
        "case_id": "s-1",
        "event_type": "review_started",
        "description": "First review",
        "timestamp_ms": 1234567890,
    }
