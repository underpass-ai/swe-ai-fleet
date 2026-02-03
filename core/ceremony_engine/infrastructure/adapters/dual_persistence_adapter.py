"""Dual persistence adapter for CeremonyInstance (Neo4j + Valkey).

Following Hexagonal Architecture:
- Implements PersistencePort (application layer interface)
- Lives in infrastructure layer
- Combines Neo4j (graph) and Valkey (details) adapters
- Optionally emits reconciliation events when Neo4j fails (Valkey succeeded)
"""

import logging
from typing import Any

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.infrastructure.adapters.neo4j_persistence_adapter import (
    Neo4jPersistenceAdapter,
)
from core.ceremony_engine.infrastructure.adapters.valkey_persistence_adapter import (
    ValkeyPersistenceAdapter,
)
from core.ceremony_engine.infrastructure.config.neo4j_config import Neo4jConfig
from core.ceremony_engine.infrastructure.config.valkey_config import ValkeyConfig
from core.shared.events.helpers import create_event_envelope

logger = logging.getLogger(__name__)

RECONCILE_SUBJECT = "ceremony.dualwrite.reconcile.requested"
OPERATION_TYPE_SAVE_INSTANCE = "save_instance"


class DualPersistenceAdapter(PersistencePort):
    """
    Composite storage adapter implementing the dual persistence pattern.

    Architecture:
    ┌─────────────────────────────────────────────────────┐
    │         DualPersistenceAdapter                      │
    ├─────────────────────────────────────────────────────┤
    │                                                      │
    │  Neo4j (Graph)          Valkey (Details)            │
    │  ├─ Nodes (Instance)    ├─ JSON (full instance)     │
    │  ├─ Relationships       ├─ Sets (indexing)          │
    │  ├─ State (minimal)     ├─ Permanent (AOF+RDB)      │
    │  └─ Observability       └─ Fast reads               │
    │                                                      │
    └─────────────────────────────────────────────────────┘

    Neo4j Responsibility:
    - Graph structure (CeremonyInstance nodes)
    - Relationships (INSTANCE_OF CeremonyDefinition)
    - Enable rehydration from graph
    - Support graph queries and observability

    Valkey Responsibility:
    - Detailed content (full instance JSON)
    - Permanent storage (AOF + RDB persistence)
    - Fast reads/writes
    - Indexing (sets by correlation_id, all instances)

    Write Path:
    1. Save details to Valkey (source of truth)
    2. Create/update node in Neo4j graph

    Read Path:
    - Retrieve from Valkey (has all details)

    Query Path (find by correlation_id):
    - Use Valkey sets for fast filtering
    - Use Neo4j for graph queries (if needed for relationships)
    """

    def __init__(
        self,
        neo4j_config: Neo4jConfig | None = None,
        valkey_config: ValkeyConfig | None = None,
        ceremonies_dir: str | None = None,
        messaging_port: MessagingPort | None = None,
    ):
        """
        Initialize composite storage adapter.

        Args:
            neo4j_config: Neo4j configuration (optional, uses env vars)
            valkey_config: Valkey configuration (optional, uses env vars)
            ceremonies_dir: Directory containing ceremony YAML files
            messaging_port: Optional port to emit reconciliation events when Neo4j fails
        """
        self.neo4j = Neo4jPersistenceAdapter(
            config=neo4j_config, ceremonies_dir=ceremonies_dir
        )
        self.valkey = ValkeyPersistenceAdapter(
            config=valkey_config, ceremonies_dir=ceremonies_dir
        )
        self._messaging_port = messaging_port

        logger.info(
            "Dual persistence adapter initialized (Neo4j graph + Valkey details)"
        )

    def close(self) -> None:
        """Close all connections."""
        self.neo4j.close()
        self.valkey.close()
        logger.info("Dual persistence adapter closed")

    async def save_instance(self, instance: CeremonyInstance) -> None:
        """
        Persist CeremonyInstance using dual persistence pattern.

        Operations:
        1. Save full details to Valkey (source of truth)
        2. Create/update graph node in Neo4j (structure only)

        Args:
            instance: CeremonyInstance entity to persist

        Raises:
            Exception: If Valkey persistence fails (fail-fast)
            Note: Neo4j failures are logged but don't fail the operation
        """
        # 1. Save to Valkey (source of truth) - fail fast if this fails
        await self.valkey.save_instance(instance)

        # 2. Try Neo4j write (non-blocking - if it fails, Valkey has the data)
        try:
            await self.neo4j.save_instance(instance)
            logger.info(
                f"Dual write completed: CeremonyInstance {instance.instance_id}"
            )
        except Exception as neo4j_error:
            # Log warning but don't fail - Valkey write succeeded
            logger.warning(
                f"Neo4j write failed (Valkey write succeeded): {instance.instance_id}, "
                f"error: {neo4j_error}"
            )
            await self._emit_reconcile_requested(
                instance=instance,
                operation_id=f"save_instance:{instance.instance_id}",
                error_message=str(neo4j_error),
            )

    async def load_instance(self, instance_id: str) -> CeremonyInstance | None:
        """
        Load CeremonyInstance by ID.

        Read Path:
        - Retrieve from Valkey (has all details)

        Args:
            instance_id: Instance ID to load

        Returns:
            CeremonyInstance if found, None otherwise

        Raises:
            Exception: If loading fails
        """
        return await self.valkey.load_instance(instance_id)

    async def _emit_reconcile_requested(
        self,
        instance: CeremonyInstance,
        operation_id: str,
        error_message: str,
    ) -> None:
        """Emit reconciliation event when Neo4j fails (best-effort, do not raise)."""
        if not self._messaging_port:
            return
        operation_data: dict[str, Any] = {
            "instance_id": instance.instance_id,
            "correlation_id": instance.correlation_id,
            "definition_name": instance.definition.name,
            "error_message": error_message,
        }
        envelope = create_event_envelope(
            event_type=RECONCILE_SUBJECT,
            payload={
                "operation_id": operation_id,
                "operation_type": OPERATION_TYPE_SAVE_INSTANCE,
                "operation_data": operation_data,
            },
            producer="ceremony-engine",
            entity_id=operation_id,
            operation="reconcile",
            correlation_id=instance.correlation_id,
        )
        try:
            await self._messaging_port.publish_event(RECONCILE_SUBJECT, envelope)
            logger.info(
                "Published reconciliation event: operation_id=%s, instance_id=%s",
                operation_id,
                instance.instance_id,
            )
        except Exception as e:
            logger.warning(
                "Failed to publish reconciliation event (operation_id=%s): %s",
                operation_id,
                e,
                exc_info=True,
            )

    async def find_instances_by_correlation_id(
        self,
        correlation_id: str,
    ) -> list[CeremonyInstance]:
        """
        Find CeremonyInstances by correlation ID.

        Query Path:
        - Use Valkey sets for fast filtering

        Args:
            correlation_id: Correlation ID to search for

        Returns:
            List of CeremonyInstances with matching correlation_id

        Raises:
            Exception: If query fails
        """
        return await self.valkey.find_instances_by_correlation_id(correlation_id)
