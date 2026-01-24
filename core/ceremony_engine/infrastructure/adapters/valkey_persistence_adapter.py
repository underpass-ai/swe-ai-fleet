"""Valkey adapter for CeremonyInstance persistence.

Following Hexagonal Architecture:
- Implements PersistencePort (application layer interface)
- Lives in infrastructure layer
- Handles Valkey operations for ceremony instances
"""

import asyncio
import json
import logging

import valkey

from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.infrastructure.config.valkey_config import ValkeyConfig
from core.ceremony_engine.infrastructure.mappers.ceremony_definition_mapper import (
    CeremonyDefinitionMapper,
)
from core.ceremony_engine.infrastructure.mappers.ceremony_instance_mapper import (
    CeremonyInstanceMapper,
)

logger = logging.getLogger(__name__)


class ValkeyPersistenceAdapter(PersistencePort):
    """Valkey adapter for CeremonyInstance persistence.

    Storage Strategy:
    - Valkey with AOF + RDB persistence (configured in K8s)
    - No TTL (permanent storage)
    - Efficient lookups with Redis keys

    Data Model:
    - String: ceremony:instance:{instance_id} → JSON string (full instance)
    - Set: ceremony:instances:all → All instance IDs
    - Set: ceremony:instances:correlation:{correlation_id} → Instance IDs by correlation_id

    Following Hexagonal Architecture:
    - Implements PersistencePort (application layer interface)
    - Uses Valkey client (infrastructure detail)
    - Uses mappers for entity ↔ storage conversion
    """

    def __init__(
        self,
        config: ValkeyConfig | None = None,
        ceremonies_dir: str | None = None,
    ):
        """Initialize Valkey adapter.

        Args:
            config: Valkey configuration (optional, uses env vars if not provided)
            ceremonies_dir: Directory containing ceremony YAML files (for loading definitions)
        """
        self.config = config or ValkeyConfig()
        self.ceremonies_dir = ceremonies_dir or "config/ceremonies"

        # Create Valkey client (Redis-compatible)
        self.client = valkey.Valkey(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            decode_responses=self.config.decode_responses,
        )

        # Test connection
        self.client.ping()

        logger.info(
            f"Valkey persistence adapter initialized: {self.config.host}:{self.config.port}"
        )

    def close(self) -> None:
        """Close Valkey connection."""
        self.client.close()
        logger.info("Valkey persistence adapter closed")

    def _instance_key(self, instance_id: str) -> str:
        """Get Valkey key for an instance.

        Args:
            instance_id: Instance identifier

        Returns:
            Valkey key string
        """
        return f"ceremony:instance:{instance_id}"

    def _all_instances_set_key(self) -> str:
        """Get Valkey key for all instances set.

        Returns:
            Valkey key string
        """
        return "ceremony:instances:all"

    def _correlation_set_key(self, correlation_id: str) -> str:
        """Get Valkey key for correlation_id set.

        Args:
            correlation_id: Correlation ID

        Returns:
            Valkey key string
        """
        return f"ceremony:instances:correlation:{correlation_id}"

    async def save_instance(self, instance: CeremonyInstance) -> None:
        """Save a CeremonyInstance to Valkey.

        Args:
            instance: Ceremony instance to save

        Raises:
            Exception: If persistence fails
        """
        # Convert to JSON
        json_str = CeremonyInstanceMapper.to_valkey_json(instance)

        # Save instance
        instance_key = self._instance_key(instance.instance_id)
        await asyncio.to_thread(self.client.set, instance_key, json_str)

        # Add to all instances set
        all_set_key = self._all_instances_set_key()
        await asyncio.to_thread(self.client.sadd, all_set_key, instance.instance_id)

        # Add to correlation_id set
        correlation_set_key = self._correlation_set_key(instance.correlation_id)
        await asyncio.to_thread(
            self.client.sadd, correlation_set_key, instance.instance_id
        )

        logger.info(f"CeremonyInstance saved to Valkey: {instance.instance_id}")

    async def load_instance(self, instance_id: str) -> CeremonyInstance | None:
        """Load a CeremonyInstance by ID.

        Args:
            instance_id: Instance ID to load

        Returns:
            CeremonyInstance if found, None otherwise

        Raises:
            Exception: If loading fails
        """
        instance_key = self._instance_key(instance_id)
        json_str = await asyncio.to_thread(self.client.get, instance_key)

        if not json_str:
            return None

        # Parse JSON to get definition_name
        instance_dict = json.loads(json_str)
        definition_name = instance_dict["definition_name"]

        # Load definition from YAML
        definition = CeremonyDefinitionMapper.load_by_name(
            definition_name, self.ceremonies_dir
        )

        # Convert from JSON to domain entity
        return CeremonyInstanceMapper.from_valkey_json(json_str, definition)

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
        # Get instance IDs from correlation set
        correlation_set_key = self._correlation_set_key(correlation_id)
        instance_ids = await asyncio.to_thread(self.client.smembers, correlation_set_key)

        if not instance_ids:
            return []

        # Load each instance
        instances = []
        for instance_id in instance_ids:
            instance = await self.load_instance(instance_id)
            if instance:
                instances.append(instance)

        return instances
