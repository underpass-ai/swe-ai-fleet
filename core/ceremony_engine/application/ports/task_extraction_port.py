"""Port for submitting task extraction jobs."""

from typing import Protocol


class TaskExtractionPort(Protocol):
    """Port defining task extraction submission interface."""

    async def submit_task_extraction(
        self,
        task_id: str,
        task_description: str,
        story_id: str,
        ceremony_id: str,
    ) -> str:
        """Submit task extraction job and return a deliberation ID."""
        ...
