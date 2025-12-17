"""Repository port for workflow state persistence.

Defines interface for workflow state storage.
Following Hexagonal Architecture (Port).
"""

from typing import Protocol

from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId


class WorkflowStateRepositoryPort(Protocol):
    """Port for workflow state persistence.

    Defines interface for storing and retrieving workflow states.
    Implemented by infrastructure adapters (Neo4j, Valkey, etc.).

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (implementations)
    - Domain/Application depend on PORT, not concrete ADAPTER
    """

    async def get_state(self, task_id: TaskId) -> WorkflowState | None:
        """Get workflow state for a task.

        Args:
            task_id: Task identifier

        Returns:
            WorkflowState if found, None otherwise
        """
        ...

    async def save_state(self, state: WorkflowState) -> None:
        """Save workflow state.

        Args:
            state: Workflow state to persist
        """
        ...

    async def get_pending_by_role(self, role: str, limit: int = 100) -> list[WorkflowState]:
        """Get pending tasks for a role.

        Args:
            role: Role identifier (developer, architect, qa, po)
            limit: Maximum number of results

        Returns:
            List of WorkflowState instances waiting for this role
        """
        ...

    async def get_all_by_story(self, story_id: StoryId) -> list[WorkflowState]:
        """Get all workflow states for a story.

        Args:
            story_id: Story identifier

        Returns:
            List of WorkflowState instances for this story
        """
        ...

    async def get_all_states(
        self,
        story_id: str | None = None,
        role: str | None = None,
    ) -> list[WorkflowState]:
        """Get all workflow states, optionally filtered by story or role.

        Used for statistics and reporting.

        Args:
            story_id: Optional story identifier filter
            role: Optional role identifier filter

        Returns:
            List of WorkflowState instances matching filters
        """
        ...

    async def delete_state(self, task_id: TaskId) -> None:
        """Delete workflow state.

        Args:
            task_id: Task identifier
        """
        ...

