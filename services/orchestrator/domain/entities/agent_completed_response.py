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
        required = ["task_id", "agent_id", "role", "timestamp"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Extract story_id from task_id if not present (for backlog review format: "ceremony-{id}:story-{id}:role-{role}")
        story_id = data.get("story_id")
        if not story_id and "task_id" in data:
            task_id = data["task_id"]
            # Try to extract story_id from task_id format: "ceremony-{id}:story-{id}:role-{role}"
            if ":story-" in task_id:
                try:
                    parts = task_id.split(":")
                    for part in parts:
                        if part.startswith("story-"):
                            story_id = part.replace("story-", "")
                            break
                except Exception:
                    pass

        # If still no story_id, use empty string (for non-backlog-review tasks)
        if not story_id:
            story_id = ""

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

