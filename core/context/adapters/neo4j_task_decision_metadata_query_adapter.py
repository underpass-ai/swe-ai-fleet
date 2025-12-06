"""Neo4j adapter for querying task decision metadata.

Infrastructure layer implementation of TaskDecisionMetadataQueryPort.
"""

import asyncio
import logging

from core.context.adapters.neo4j_query_store import Neo4jQueryStore
from core.context.domain.neo4j_queries import Neo4jQuery
from core.context.domain.task_decision_metadata import TaskDecisionMetadata
from core.context.infrastructure.mappers.task_decision_metadata_mapper import (
    TaskDecisionMetadataMapper,
)

logger = logging.getLogger(__name__)


class Neo4jTaskDecisionMetadataQueryAdapter:
    """Neo4j implementation of TaskDecisionMetadataQueryPort.

    This adapter translates domain queries into Cypher queries and
    Neo4j results back into domain value objects.

    Following Hexagonal Architecture:
    - Implements TaskDecisionMetadataQueryPort protocol
    - Depends on Neo4jQueryStore for low-level Neo4j operations
    - Translates infrastructure data (Neo4j records) to domain objects
    """

    def __init__(self, neo4j_query_store: Neo4jQueryStore) -> None:
        """Initialize adapter with Neo4j query store.

        Args:
            neo4j_query_store: Low-level Neo4j query executor
        """
        self._query_store = neo4j_query_store

    async def get_task_decision_metadata(self, task_id: str) -> TaskDecisionMetadata | None:
        """Retrieve decision metadata for a specific task from Neo4j.

        Queries the HAS_TASK relationship properties which contain decision metadata
        from Planning Service's FASE 1+2 (Backlog Review Ceremony).

        Args:
            task_id: Unique identifier of the task

        Returns:
            TaskDecisionMetadata if found, None if task has no decision metadata

        Raises:
            Exception: If Neo4j query execution fails
        """
        try:
            # Run synchronous Neo4j query in thread pool to avoid blocking event loop
            results = await asyncio.to_thread(
                self._query_store.query,
                Neo4jQuery.GET_TASK_DECISION_METADATA.value,
                {"task_id": task_id},
            )

            if not results or len(results) == 0:
                logger.debug(f"No decision metadata found for task {task_id}")
                return None

            # Extract first result (LIMIT 1 ensures only one)
            record = results[0]

            # Map Neo4j result to domain value object using infrastructure mapper
            return TaskDecisionMetadataMapper.from_neo4j_record(record)

        except Exception as e:
            logger.warning(f"Failed to query decision metadata for task {task_id}: {e}")
            raise

