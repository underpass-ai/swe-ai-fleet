"""RehydrationPort: Port for rehydrating ceremony instances from Neo4j.

Following Hexagonal Architecture:
- This is a PORT (interface) in the application layer
- Infrastructure adapters implement this port
- Application services depend on this port, not concrete adapters
"""

from typing import Protocol

from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance


class RehydrationPort(Protocol):
    """Port for rehydrating ceremony instances from Neo4j.

    Provides rehydration capabilities:
    - Rebuild ceremony instance state from Neo4j graph
    - Reconstruct step status from graph relationships
    - Recover idempotency keys from graph metadata
    - Handle missing data gracefully (fail-fast or return None)

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (Neo4jRehydrationAdapter, etc.)
    - Application depends on PORT, not concrete implementation

    Business Rules:
    - Rehydration is used when Valkey cache is lost (pod restart)
    - Neo4j is the source of truth for ceremony state
    - Rehydration should reconstruct complete instance state
    - Missing data should fail-fast (no partial state)
    """

    async def rehydrate_instance(
        self,
        instance_id: str,
    ) -> CeremonyInstance | None:
        """Rehydrate a ceremony instance from Neo4j.

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
        ...

    async def rehydrate_instances_by_correlation_id(
        self,
        correlation_id: str,
    ) -> list[CeremonyInstance]:
        """Rehydrate all ceremony instances for a correlation ID.

        Useful for recovering all instances in a distributed trace.

        Args:
            correlation_id: Correlation ID to search for

        Returns:
            List of rehydrated ceremony instances

        Raises:
            Exception: If Neo4j query fails
        """
        ...
