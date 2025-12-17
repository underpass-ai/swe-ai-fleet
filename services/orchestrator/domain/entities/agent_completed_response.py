"""Agent completed response entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentCompletedResponse:
    """Event received when an agent completes a task.

    Origin: Ray Executor / Agent Service
    Subject: agent.response.completed

    Attributes:
        task_id: Task identifier
        agent_id: Agent identifier
        story_id: Story identifier
        role: Agent role
        output: Task output (contains duration_ms, checks_passed, etc.)
        timestamp: Event timestamp (ISO format)
    """

    task_id: str
    agent_id: str
    story_id: str
    role: str
    output: dict[str, Any]
    timestamp: str

    @property
    def duration_ms(self) -> int:
        """Get duration from output."""
        return self.output.get("duration_ms", 0)

    @property
    def checks_passed(self) -> bool:
        """Get checks passed status from output."""
        return self.output.get("checks_passed", True)

    @staticmethod
    def _extract_story_id_from_task_id(task_id: str) -> str:
        """Extract story_id from task_id if present.

        Args:
            task_id: Task identifier (may contain story in format "ceremony-{id}:story-{id}:role-{role}")

        Returns:
            Extracted story_id or empty string if not found
        """
        if ":story-" not in task_id:
            return ""

        try:
            parts = task_id.split(":")
            for part in parts:
                if part.startswith("story-"):
                    return part.replace("story-", "")
        except Exception:
            pass

        return ""

    @classmethod
    def _extract_story_id(cls, data: dict[str, Any]) -> str:
        """Extract story_id from data, falling back to parsing task_id if needed.

        Args:
            data: Event data from NATS message

        Returns:
            Story identifier or empty string if not found
        """
        story_id = data.get("story_id")
        if story_id:
            return story_id

        task_id = data.get("task_id")
        if task_id:
            story_id = cls._extract_story_id_from_task_id(task_id)
            if story_id:
                return story_id

        return ""

    @classmethod
    def _validate_required_fields(cls, data: dict[str, Any]) -> None:
        """Validate that all required fields are present.

        Args:
            data: Event data from NATS message

        Raises:
            ValueError: If required fields missing
        """
        required = ["task_id", "agent_id", "role", "timestamp"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentCompletedResponse:
        """Create event from dictionary.

        Args:
            data: Event data from NATS message

        Returns:
            AgentCompletedResponse instance

        Raises:
            ValueError: If required fields missing
        """
        cls._validate_required_fields(data)
        story_id = cls._extract_story_id(data)

        return cls(
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            story_id=story_id,
            role=data["role"],
            output=data.get("output", {}),
            timestamp=data["timestamp"],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "story_id": self.story_id,
            "role": self.role,
            "output": self.output,
            "timestamp": self.timestamp,
        }

