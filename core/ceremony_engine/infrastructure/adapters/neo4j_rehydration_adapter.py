"""Neo4j adapter for CeremonyInstance rehydration.

Following Hexagonal Architecture:
- Implements RehydrationPort (application layer interface)
- Lives in infrastructure layer
- Rebuilds CeremonyInstance state from Neo4j graph
"""

import logging

from core.ceremony_engine.application.ports.rehydration_port import RehydrationPort
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.infrastructure.adapters.neo4j_persistence_adapter import (
    Neo4jPersistenceAdapter,
)
from core.ceremony_engine.infrastructure.config.neo4j_config import Neo4jConfig

logger = logging.getLogger(__name__)


class Neo4jRehydrationAdapter(RehydrationPort):
    """Neo4j adapter for rehydrating CeremonyInstance from graph.

    Responsibilities:
    - Rebuild CeremonyInstance state from Neo4j graph
    - Reconstruct step status from graph relationships
    - Recover idempotency keys from graph metadata
    - Handle missing data gracefully (fail-fast)

    Following Hexagonal Architecture:
    - Implements RehydrationPort (application layer interface)
    - Uses Neo4jPersistenceAdapter for graph queries
    - Uses mappers for graph ↔ domain conversion

    Business Rules:
    - Rehydration is used when Valkey cache is lost (pod restart)
    - Neo4j is the source of truth for ceremony state
    - Rehydration should reconstruct complete instance state
    - Missing data should fail-fast (no partial state)
    """

    def __init__(
        self,
        neo4j_config: Neo4jConfig | None = None,
        ceremonies_dir: str | None = None,
    ):
        """Initialize Neo4j rehydration adapter.

        Args:
            neo4j_config: Neo4j configuration (optional, uses env vars if not provided)
            ceremonies_dir: Directory containing ceremony YAML files (for loading definitions)
        """
        # Reuse Neo4jPersistenceAdapter for graph queries
        self.neo4j_adapter = Neo4jPersistenceAdapter(
            config=neo4j_config, ceremonies_dir=ceremonies_dir
        )

        logger.info("Neo4j rehydration adapter initialized")

    def close(self) -> None:
        """Close Neo4j connection."""
        self.neo4j_adapter.close()
        logger.info("Neo4j rehydration adapter closed")

    async def rehydrate_instance(
        self,
        instance_id: str,
    ) -> CeremonyInstance | None:
        """
        Rehydrate a CeremonyInstance from Neo4j.

        Rebuilds the complete instance state from Neo4j graph:
        - Loads instance node with properties
        - Reconstructs step status from step nodes/relationships
        - Reconstructs idempotency keys from metadata
        - Validates reconstructed instance (fail-fast)

        Args:
            instance_id: Instance ID to rehydrate

        Returns:
            CeremonyInstance if found and successfully rehydrated, None if not found

        Raises:
            ValueError: If instance data is invalid (fail-fast)
            Exception: If Neo4j query fails
        """
        # Use Neo4j adapter to load instance
        instance = await self.neo4j_adapter.load_instance(instance_id)

        if instance:
            logger.info(
                f"CeremonyInstance rehydrated from Neo4j: {instance_id} "
                f"(state: {instance.current_state}, "
                f"steps: {len(instance.step_status.entries)})"
            )
        else:
            logger.warning(f"CeremonyInstance not found in Neo4j: {instance_id}")

        return instance

    async def rehydrate_instances_by_correlation_id(
        self,
        correlation_id: str,
    ) -> list[CeremonyInstance]:
        """
        Rehydrate all CeremonyInstances for a correlation ID.

        Useful for recovering all instances in a distributed trace.

        Args:
            correlation_id: Correlation ID to search for

        Returns:
            List of rehydrated CeremonyInstances

        Raises:
            Exception: If Neo4j query fails
        """
        # Use Neo4j adapter to find instances
        instances = await self.neo4j_adapter.find_instances_by_correlation_id(
            correlation_id
        )

        logger.info(
            f"Rehydrated {len(instances)} CeremonyInstances for correlation_id: {correlation_id}"
        )

        return instances
