"""Workflow state collection.

Domain collection for managing multiple WorkflowState aggregates.
Following Domain-Driven Design principles.
"""

from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role


class WorkflowStateCollection:
    """Collection of WorkflowState aggregates.

    Encapsulates collection-level operations:
    - Filtering by role
    - Sorting by priority
    - Querying collection state

    Following DDD:
    - Domain logic stays in domain (not in use cases)
    - Rich domain model (not anemic)
    - Tell, Don't Ask
    """

    def __init__(self, states: list[WorkflowState]) -> None:
        """Initialize collection.

        Args:
            states: List of workflow states
        """
        self._states = states

    def filter_ready_for_role(self, role: Role) -> "WorkflowStateCollection":
        """Filter tasks ready for a specific role.

        Tell, Don't Ask: Collection tells us which tasks match criteria.

        Args:
            role: Role to filter by

        Returns:
            New collection with filtered states
        """
        filtered = [
            state for state in self._states
            if state.is_ready_for_role(role)
        ]
        return WorkflowStateCollection(filtered)

    def sort_by_priority(self) -> "WorkflowStateCollection":
        """Sort tasks by priority.

        Priority logic:
        - Higher rejection count = higher priority (needs more attention)
        - Then by updated_at ASC (older tasks first)

        Returns:
            New collection with sorted states
        """
        sorted_states = sorted(
            self._states,
            key=lambda s: (-s.get_rejection_count(), s.updated_at),
        )
        return WorkflowStateCollection(sorted_states)

    def to_list(self) -> list[WorkflowState]:
        """Convert collection to list.

        Returns:
            List of workflow states
        """
        return list(self._states)

    def __len__(self) -> int:
        """Get collection size."""
        return len(self._states)

    def __iter__(self):
        """Iterate over collection."""
        return iter(self._states)

    def __bool__(self) -> bool:
        """Check if collection is non-empty."""
        return bool(self._states)

