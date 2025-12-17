from __future__ import annotations

from typing import Any

import pytest

from services.orchestrator.domain.entities.agent_completed_response import (
    AgentCompletedResponse,
)


class TestAgentCompletedResponseFromDict:
    def test_from_dict_happy_path_with_story_id_and_output(self) -> None:
        data: dict[str, Any] = {
            "task_id": "task-1",
            "agent_id": "agent-1",
            "story_id": "story-123",
            "role": "DEV",
            "timestamp": "2025-01-01T00:00:00Z",
            "output": {"duration_ms": 1500, "checks_passed": False},
        }

        event = AgentCompletedResponse.from_dict(data)

        assert event.task_id == "task-1"
        assert event.agent_id == "agent-1"
        assert event.story_id == "story-123"
        assert event.role == "DEV"
        assert event.timestamp == "2025-01-01T00:00:00Z"
        assert event.duration_ms == 1500
        assert event.checks_passed is False

        # to_dict round-trip
        assert event.to_dict()["story_id"] == "story-123"

    def test_from_dict_extracts_story_id_from_task_id_format(self) -> None:
        data: dict[str, Any] = {
            "task_id": "ceremony-1:story-abc123:role-DEV",
            "agent_id": "agent-2",
            "role": "DEV",
            "timestamp": "2025-01-01T01:00:00Z",
            "output": {},
        }

        event = AgentCompletedResponse.from_dict(data)

        assert event.story_id == "abc123"

    def test_from_dict_uses_empty_story_id_when_not_present(self) -> None:
        data: dict[str, Any] = {
            "task_id": "simple-task-id",
            "agent_id": "agent-3",
            "role": "DEV",
            "timestamp": "2025-01-01T02:00:00Z",
        }

        event = AgentCompletedResponse.from_dict(data)

        assert event.story_id == ""
        # Properties fall back to defaults when output is missing
        assert event.duration_ms == 0
        assert event.checks_passed is True

    def test_from_dict_missing_required_fields_raises_value_error(self) -> None:
        data: dict[str, Any] = {
            "task_id": "task-1",
            # missing agent_id, role, timestamp
        }

        with pytest.raises(ValueError) as exc_info:
            AgentCompletedResponse.from_dict(data)

        msg = str(exc_info.value)
        assert "Missing required fields" in msg
        assert "agent_id" in msg
        assert "role" in msg
        assert "timestamp" in msg


class TestAgentCompletedResponseToDict:
    def test_to_dict_contains_all_fields(self) -> None:
        event = AgentCompletedResponse(
            task_id="task-1",
            agent_id="agent-1",
            story_id="story-1",
            role="DEV",
            output={"duration_ms": 100, "checks_passed": True},
            timestamp="2025-01-01T03:00:00Z",
        )

        as_dict = event.to_dict()

        assert as_dict == {
            "task_id": "task-1",
            "agent_id": "agent-1",
            "story_id": "story-1",
            "role": "DEV",
            "output": {"duration_ms": 100, "checks_passed": True},
            "timestamp": "2025-01-01T03:00:00Z",
        }
