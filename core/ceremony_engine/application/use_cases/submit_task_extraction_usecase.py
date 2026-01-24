"""Use case for submitting task extraction jobs."""

from core.ceremony_engine.application.ports.task_extraction_port import TaskExtractionPort


class SubmitTaskExtractionUseCase:
    """Use case for submitting task extraction to Ray Executor."""

    def __init__(self, task_extraction_port: TaskExtractionPort) -> None:
        if not task_extraction_port:
            raise ValueError("task_extraction_port is required (fail-fast)")
        self._task_extraction_port = task_extraction_port

    async def execute(
        self,
        ceremony_id: str,
        story_id: str,
        agent_deliberations: list[dict[str, object]],
    ) -> dict[str, object]:
        """Submit task extraction job and return submission metadata."""
        if not ceremony_id or not ceremony_id.strip():
            raise ValueError("ceremony_id cannot be empty")
        if not story_id or not story_id.strip():
            raise ValueError("story_id cannot be empty")
        if not agent_deliberations:
            raise ValueError("agent_deliberations cannot be empty")

        prompt = self._build_extraction_prompt(story_id, agent_deliberations)
        task_id = f"ceremony-{ceremony_id}:story-{story_id}:task-extraction"

        deliberation_id = await self._task_extraction_port.submit_task_extraction(
            task_id=task_id,
            task_description=prompt,
            story_id=story_id,
            ceremony_id=ceremony_id,
        )

        return {
            "task_id": task_id,
            "deliberation_id": deliberation_id,
            "status": "submitted",
        }

    def _build_extraction_prompt(
        self, story_id: str, agent_deliberations: list[dict[str, object]]
    ) -> str:
        """Build prompt for task extraction agent."""
        deliberations_text = []
        for i, deliberation in enumerate(agent_deliberations, 1):
            agent_id = deliberation.get("agent_id", "unknown")
            role = deliberation.get("role", "unknown")
            proposal = deliberation.get("proposal", {})

            if isinstance(proposal, dict):
                feedback_text = proposal.get("content", str(proposal))
            else:
                feedback_text = str(proposal)

            deliberations_text.append(
                f"--- Deliberation {i}: {agent_id} ({role}) ---\n"
                f"{feedback_text}\n"
            )

        return (
            "You are a task extraction specialist. Analyze the following agent deliberations "
            "for a user story and extract concrete, actionable tasks.\n\n"
            f"Story ID: {story_id}\n\n"
            "Agent Deliberations:\n"
            f"{chr(10).join(deliberations_text)}\n\n"
            "Instructions:\n"
            "1. Analyze all agent deliberations carefully\n"
            "2. Extract concrete, actionable tasks that need to be completed\n"
            "3. Each task should be specific, measurable, and have clear acceptance criteria\n"
            "4. Tasks should be ordered logically (dependencies considered)\n"
            "5. For each task, identify which agent deliberations contributed to it\n"
            "6. Return a JSON array of tasks with the following structure:\n"
            "   {\n"
            '     "tasks": [\n'
            "       {\n"
            '         "title": "Task title",\n'
            '         "description": "Detailed description",\n'
            '         "estimated_hours": 8,\n'
            '         "deliberation_indices": [0, 1, 2],\n'
            '         "priority": 1\n'
            "       }\n"
            "     ]\n"
            "   }\n\n"
            "Return ONLY valid JSON, no markdown, no explanations."
        )
