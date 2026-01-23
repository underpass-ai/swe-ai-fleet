"""Neo4j adapter for CeremonyInstance persistence.

Following Hexagonal Architecture:
- Implements PersistencePort (application layer interface)
- Lives in infrastructure layer
- Handles Neo4j graph operations for ceremony instances
"""

import asyncio
import logging
from typing import Any

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable, TransientError

from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.infrastructure.adapters.neo4j_queries import (
    CeremonyInstanceNeo4jQueries,
)
from core.ceremony_engine.infrastructure.config.neo4j_config import Neo4jConfig
from core.ceremony_engine.infrastructure.mappers.ceremony_definition_mapper import (
    CeremonyDefinitionMapper,
)
from core.ceremony_engine.infrastructure.mappers.ceremony_instance_mapper import (
    CeremonyInstanceMapper,
)

logger = logging.getLogger(__name__)


class Neo4jPersistenceAdapter(PersistencePort):
    """Neo4j adapter for CeremonyInstance persistence.

    Responsibilities:
    - Store CeremonyInstance nodes in Neo4j graph
    - Load instances by ID
    - Query instances by correlation_id
    - Enable graph relationships for observability

    Following Hexagonal Architecture:
    - Implements PersistencePort (application layer interface)
    - Uses Neo4j driver (infrastructure detail)
    - Uses mappers for entity ↔ storage conversion
    """

    def __init__(
        self,
        config: Neo4jConfig | None = None,
        ceremonies_dir: str | None = None,
    ):
        """Initialize Neo4j adapter.

        Args:
            config: Neo4j configuration (optional, uses env vars if not provided)
            ceremonies_dir: Directory containing ceremony YAML files (for loading definitions)
        """
        self.config = config or Neo4jConfig()
        self.ceremonies_dir = ceremonies_dir or "config/ceremonies"

        # Create Neo4j driver
        self.driver: Driver = GraphDatabase.driver(
            self.config.uri,
            auth=(self.config.user, self.config.password),
        )

        # Initialize constraints
        self._init_constraints()

        logger.info(f"Neo4j persistence adapter initialized: {self.config.uri}")

    def close(self) -> None:
        """Close Neo4j driver connection."""
        self.driver.close()
        logger.info("Neo4j persistence adapter closed")

    def _session(self) -> Session:
        """Create a new Neo4j session.

        Returns:
            Neo4j session with configured database
        """
        if self.config.database:
            return self.driver.session(database=self.config.database)
        return self.driver.session()

    def _retry_operation(self, fn, *args, **kwargs):
        """Retry operations on transient errors with exponential backoff.

        Args:
            fn: Function to retry
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            Exception: If max retries exceeded
        """
        attempt = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except (ServiceUnavailable, TransientError) as e:
                if attempt >= self.config.max_retries:
                    logger.error(f"Max retries exceeded: {e}")
                    raise

                backoff = self.config.base_backoff_s * (2 ** attempt)
                logger.warning(
                    f"Retrying after {backoff}s (attempt {attempt + 1}): {e}"
                )
                import time

                time.sleep(backoff)
                attempt += 1

    def _init_constraints(self) -> None:
        """Initialize Neo4j constraints for CeremonyInstance nodes."""
        def _tx(tx):
            # Create unique constraint on instance_id
            tx.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (ci:CeremonyInstance) "
                "REQUIRE ci.instance_id IS UNIQUE"
            )
            # Create index on correlation_id for fast lookups
            tx.run(
                "CREATE INDEX IF NOT EXISTS FOR (ci:CeremonyInstance) "
                "ON (ci.correlation_id)"
            )

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

        logger.info("Neo4j constraints initialized for CeremonyInstance")

    async def save_instance(self, instance: CeremonyInstance) -> None:
        """Save a CeremonyInstance to Neo4j.

        Args:
            instance: Ceremony instance to save

        Raises:
            Exception: If persistence fails
        """
        await asyncio.to_thread(self._save_instance_sync, instance)
        logger.info(f"CeremonyInstance saved to Neo4j: {instance.instance_id}")

    def _save_instance_sync(self, instance: CeremonyInstance) -> None:
        """Synchronous save operation."""
        # Convert to Neo4j dict format
        instance_dict = CeremonyInstanceMapper.to_neo4j_dict(instance)

        def _tx(tx):
            # Merge CeremonyInstance node
            tx.run(
                CeremonyInstanceNeo4jQueries.MERGE_CEREMONY_INSTANCE.value,
                **instance_dict,
            )
            # Create relationship to CeremonyDefinition
            tx.run(
                CeremonyInstanceNeo4jQueries.CREATE_DEFINITION_RELATIONSHIP.value,
                instance_id=instance.instance_id,
                definition_name=instance.definition.name,
            )

        with self._session() as session:
            self._retry_operation(session.execute_write, _tx)

    async def load_instance(self, instance_id: str) -> CeremonyInstance | None:
        """Load a CeremonyInstance by ID.

        Args:
            instance_id: Instance ID to load

        Returns:
            CeremonyInstance if found, None otherwise

        Raises:
            Exception: If loading fails
        """
        return await asyncio.to_thread(self._load_instance_sync, instance_id)

    def _load_instance_sync(self, instance_id: str) -> CeremonyInstance | None:
        """Synchronous load operation."""
        def _tx(tx):
            result = tx.run(
                CeremonyInstanceNeo4jQueries.GET_CEREMONY_INSTANCE.value,
                instance_id=instance_id,
            )
            record = result.single()
            return dict(record["ci"]) if record else None

        with self._session() as session:
            data = self._retry_operation(session.execute_read, _tx)

        if not data:
            return None

        # Load definition from YAML
        definition_name = data["definition_name"]
        definition = CeremonyDefinitionMapper.load_by_name(
            definition_name, self.ceremonies_dir
        )

        # Convert from Neo4j dict to domain entity
        return CeremonyInstanceMapper.from_neo4j_dict(data, definition)

    async def find_instances_by_correlation_id(
        self,
        correlation_id: str,
    ) -> list[CeremonyInstance]:
        """Find CeremonyInstances by correlation ID.

        Args:
            correlation_id: Correlation ID to search for

        Returns:
            List of CeremonyInstances with matching correlation_id

        Raises:
            Exception: If query fails
        """
        return await asyncio.to_thread(
            self._find_instances_by_correlation_id_sync, correlation_id
        )

    def _find_instances_by_correlation_id_sync(
        self, correlation_id: str
    ) -> list[CeremonyInstance]:
        """Synchronous find operation."""
        def _tx(tx):
            result = tx.run(
                CeremonyInstanceNeo4jQueries.FIND_BY_CORRELATION_ID.value,
                correlation_id=correlation_id,
            )
            return [dict(record["ci"]) for record in result]

        with self._session() as session:
            records = self._retry_operation(session.execute_read, _tx)

        instances = []
        for data in records:
            # Load definition from YAML
            definition_name = data["definition_name"]
            definition = CeremonyDefinitionMapper.load_by_name(
                definition_name, self.ceremonies_dir
            )

            # Convert from Neo4j dict to domain entity
            instance = CeremonyInstanceMapper.from_neo4j_dict(data, definition)
            instances.append(instance)

        return instances
