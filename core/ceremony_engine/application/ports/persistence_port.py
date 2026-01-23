"""PersistencePort: Port for persisting ceremony instances.

Following Hexagonal Architecture:
- This is a PORT (interface) in the application layer
- Infrastructure adapters implement this port
- Application services depend on this port, not concrete adapters
"""

from typing import Protocol

from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance


class PersistencePort(Protocol):
    """Port for persisting ceremony instances (Valkey/Neo4j).

    Provides persistence capabilities:
    - Save ceremony instances (dual persistence: Valkey + Neo4j)
    - Load ceremony instances by ID
    - Query instances by correlation_id or other criteria

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (ValkeyPersistenceAdapter, Neo4jPersistenceAdapter, etc.)
    - Application depends on PORT, not concrete implementation
    """

    async def save_instance(self, instance: CeremonyInstance) -> None:
        """Save a ceremony instance (dual persistence).

        Args:
            instance: Ceremony instance to save

        Raises:
            Exception: If persistence fails
        """
        ...

    async def load_instance(self, instance_id: str) -> CeremonyInstance | None:
        """Load a ceremony instance by ID.

        Args:
            instance_id: Instance ID to load

        Returns:
            CeremonyInstance if found, None otherwise

        Raises:
            Exception: If loading fails
        """
        ...

    async def find_instances_by_correlation_id(
        self,
        correlation_id: str,
    ) -> list[CeremonyInstance]:
        """Find ceremony instances by correlation ID.

        Args:
            correlation_id: Correlation ID to search for

        Returns:
            List of ceremony instances with matching correlation_id

        Raises:
            Exception: If query fails
        """
        ...
