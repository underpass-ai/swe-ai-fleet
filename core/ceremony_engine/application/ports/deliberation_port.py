"""Port for submitting deliberations to external execution."""

from typing import Protocol


class DeliberationPort(Protocol):
    """Port defining deliberation submission interface."""

    async def submit_backlog_review_deliberation(
        self,
        task_id: str,
        task_description: str,
        role: str,
        story_id: str,
        num_agents: int,
        constraints: dict[str, object] | None = None,
    ) -> str:
        """Submit a deliberation job and return a deliberation ID."""
        ...
