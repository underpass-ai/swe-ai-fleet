"""
NATS Handler for Orchestrator Service.

Manages NATS JetStream connection and event publishing.

Refactored to use Hexagonal Architecture:
- Wraps NATSMessagingAdapter (implements MessagingPort)
- Publishes domain events instead of raw dicts
- Legacy compatibility maintained for gradual migration
"""

import asyncio
import logging

from services.orchestrator.domain.events import (
    DeliberationCompletedEvent,
    TaskDispatchedEvent,
)
from services.orchestrator.infrastructure.adapters import NATSMessagingAdapter

logger = logging.getLogger(__name__)


class OrchestratorNATSHandler:
    """Handles NATS messaging for Orchestrator Service.
    
    This is a legacy wrapper around NATSMessagingAdapter.
    New code should use NATSMessagingAdapter directly via MessagingPort.
    
    Following Hexagonal Architecture:
    - Delegates to NATSMessagingAdapter (port implementation)
    - Publishes domain events for type safety
    - Maintains backwards compatibility
    """

    def __init__(self, nats_url: str):
        """
        Initialize NATS handler.

        Args:
            nats_url: NATS server URL
        """
        self.nats_url = nats_url
        self._adapter = NATSMessagingAdapter(nats_url)

    async def connect(self):
        """Connect to NATS and setup JetStream."""
        await self._adapter.connect()

    async def publish(self, subject: str, data: bytes):
        """
        Publish raw bytes to a NATS subject (legacy method).

        Prefer using publish_event() with domain events.

        Args:
            subject: NATS subject
            data: Message data (bytes)
        """
        # Decode and publish as dict (legacy compatibility)
        import json
        try:
            data_dict = json.loads(data.decode())
            await self._adapter.publish_dict(subject, data_dict)
        except Exception as e:
            logger.error(f"Failed to publish to {subject}: {e}")

    async def publish_deliberation_completed(
        self,
        story_id: str,
        task_id: str,
        decisions: list[dict],
    ):
        """Publish deliberation completed event using domain entity."""
        event = DeliberationCompletedEvent(
            story_id=story_id,
            task_id=task_id,
            decisions=decisions,
            timestamp=asyncio.get_event_loop().time(),
        )

        await self._adapter.publish(
            "orchestration.deliberation.completed",
            event
        )

        logger.info(f"✓ Published deliberation completed for {task_id}")

    async def publish_task_dispatched(
        self,
        story_id: str,
        task_id: str,
        agent_id: str,
        role: str,
    ):
        """Publish task dispatched event using domain entity."""
        from datetime import UTC, datetime
        
        event = TaskDispatchedEvent(
            story_id=story_id,
            task_id=task_id,
            agent_id=agent_id,
            role=role,
            timestamp=datetime.now(UTC).isoformat(),
        )

        await self._adapter.publish(
            "orchestration.task.dispatched",
            event
        )

        logger.info(f"✓ Published task dispatched: {task_id} to {agent_id}")

    async def close(self):
        """Close NATS connection."""
        await self._adapter.close()

