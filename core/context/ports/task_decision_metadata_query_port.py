"""Port for querying task decision metadata.

This port defines the interface for retrieving decision context from graph storage.
Following Hexagonal Architecture: application layer depends on this port (interface),
infrastructure adapter implements it.
"""

from typing import Protocol

from core.context.domain.task_decision_metadata import TaskDecisionMetadata


class TaskDecisionMetadataQueryPort(Protocol):
    """Port for querying task decision metadata from graph storage.

    This port abstracts the infrastructure concern of how decision metadata
    is stored and retrieved, allowing the application layer to work with
    pure domain objects.

    Following Hexagonal Architecture:
    - Application layer depends on this port (interface)
    - Infrastructure adapter implements this port (Neo4j, in-memory, etc.)
    - Port works with domain value objects, NOT primitives
    """

    async def get_task_decision_metadata(self, task_id: str) -> TaskDecisionMetadata | None:
        """Retrieve decision metadata for a specific task.

        Args:
            task_id: Unique identifier of the task

        Returns:
            TaskDecisionMetadata if found, None if task has no decision metadata

        Raises:
            Exception: If query execution fails (infrastructure error)
        """
        ...



