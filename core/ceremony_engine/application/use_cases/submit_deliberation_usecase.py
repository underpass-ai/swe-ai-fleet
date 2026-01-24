"""Use case for submitting deliberations."""

from core.ceremony_engine.application.ports.deliberation_port import DeliberationPort


class SubmitDeliberationUseCase:
    """Use case for submitting a deliberation job."""

    def __init__(self, deliberation_port: DeliberationPort) -> None:
        if not deliberation_port:
            raise ValueError("deliberation_port is required (fail-fast)")
        self._deliberation_port = deliberation_port

    async def execute(
        self,
        task_id: str,
        task_description: str,
        role: str,
        story_id: str,
        num_agents: int,
        constraints: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Submit a deliberation and return submission metadata."""
        if not task_id or not task_id.strip():
            raise ValueError("task_id cannot be empty")
        if not task_description or not task_description.strip():
            raise ValueError("task_description cannot be empty")
        if not role or not role.strip():
            raise ValueError("role cannot be empty")
        if not story_id or not story_id.strip():
            raise ValueError("story_id cannot be empty")
        if num_agents <= 0:
            raise ValueError("num_agents must be positive")

        deliberation_id = await self._deliberation_port.submit_backlog_review_deliberation(
            task_id=task_id,
            task_description=task_description,
            role=role,
            story_id=story_id,
            num_agents=num_agents,
            constraints=constraints,
        )

        return {
            "task_id": task_id,
            "deliberation_id": deliberation_id,
            "role": role,
            "num_agents": num_agents,
            "status": "submitted",
        }
