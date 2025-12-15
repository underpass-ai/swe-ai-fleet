from __future__ import annotations

from typing import Any

import pytest

from services.orchestrator.domain.entities.agent_response_message import (
    AgentResponseMessage,
)


class TestAgentResponseMessageFromDict:
    def test_from_dict_happy_path_uses_all_fields(self) -> None:
        data: dict[str, Any] = {
            "task_id": "task-123",
            "agent_id": "agent-1",
            "role": "DEV",
            "proposal": {"text": "answer"},
            "duration_ms": 500,
            "timestamp": "2025-01-01T00:00:00Z",
            "num_agents": 3,
        }

        msg = AgentResponseMessage.from_dict(data)

        assert msg.task_id == "task-123"
        assert msg.agent_id == "agent-1"
        assert msg.role == "DEV"
        assert msg.proposal == {"text": "answer"}
        assert msg.duration_ms == 500
        assert msg.timestamp == "2025-01-01T00:00:00Z"
        assert msg.num_agents == 3

        # to_dict round-trip includes num_agents when set
        as_dict = msg.to_dict()
        assert as_dict["num_agents"] == 3

    def test_from_dict_applies_defaults_for_optional_fields(self) -> None:
        data: dict[str, Any] = {
            "task_id": "task-456",
            "agent_id": "agent-2",
        }

        msg = AgentResponseMessage.from_dict(data)

        assert msg.role == "unknown"
        assert msg.proposal == {}
        assert msg.duration_ms == 0
        assert msg.timestamp == ""
        assert msg.num_agents is None

        as_dict = msg.to_dict()
        assert "num_agents" not in as_dict

    def test_from_dict_missing_required_fields_raises_value_error(self) -> None:
        data_missing_task: dict[str, Any] = {"agent_id": "agent-1"}
        data_missing_agent: dict[str, Any] = {"task_id": "task-1"}

        with pytest.raises(ValueError) as exc_info1:
            AgentResponseMessage.from_dict(data_missing_task)
        assert "task_id" in str(exc_info1.value)

        with pytest.raises(ValueError) as exc_info2:
            AgentResponseMessage.from_dict(data_missing_agent)
        assert "agent_id" in str(exc_info2.value)


class TestAgentResponseMessageToDict:
    def test_to_dict_excludes_num_agents_when_none(self) -> None:
        msg = AgentResponseMessage(
            task_id="task-789",
            agent_id="agent-3",
            role="ARCHITECT",
            proposal={"text": "design"},
            duration_ms=1000,
            timestamp="2025-01-01T01:00:00Z",
            num_agents=None,
        )

        as_dict = msg.to_dict()

        assert "num_agents" not in as_dict
        assert as_dict["task_id"] == "task-789"
        assert as_dict["agent_id"] == "agent-3"
        assert as_dict["role"] == "ARCHITECT"
        assert as_dict["proposal"] == {"text": "design"}
        assert as_dict["duration_ms"] == 1000
        assert as_dict["timestamp"] == "2025-01-01T01:00:00Z"
