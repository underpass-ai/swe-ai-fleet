"""
NATS Handler for Orchestrator Service.

Manages NATS JetStream connection and event publishing.
"""

import asyncio
import json
import logging
from typing import Any

import nats
from nats.aio.client import Client as NATS

logger = logging.getLogger(__name__)


class OrchestratorNATSHandler:
    """Handles NATS messaging for Orchestrator Service."""

    def __init__(
        self,
        nats_url: str,
        orchestrator_service: Any,
    ):
        """
        Initialize NATS handler.

        Args:
            nats_url: NATS server URL
            orchestrator_service: OrchestratorServiceServicer instance
        """
        self.nats_url = nats_url
        self.orchestrator_service = orchestrator_service
        self.nc: NATS | None = None
        self.js = None

    async def connect(self):
        """Connect to NATS and setup JetStream."""
        try:
            logger.info(f"Connecting to NATS at {self.nats_url}")
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()

            logger.info("✓ Connected to NATS successfully")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise

    async def publish(self, subject: str, data: bytes):
        """
        Publish a message to a NATS subject.

        Args:
            subject: NATS subject
            data: Message data (bytes)
        """
        if not self.js:
            logger.warning("NATS not connected, skipping publish")
            return

        try:
            await self.js.publish(subject, data)
            logger.debug(f"✓ Published to {subject}")
        except Exception as e:
            logger.error(f"Failed to publish to {subject}: {e}")

    async def publish_deliberation_completed(
        self,
        story_id: str,
        task_id: str,
        decisions: list[dict],
    ):
        """Publish deliberation completed event."""
        event = {
            "event_type": "orchestration.deliberation.completed",
            "story_id": story_id,
            "task_id": task_id,
            "decisions": decisions,
            "timestamp": asyncio.get_event_loop().time(),
        }

        await self.publish(
            "orchestration.deliberation.completed",
            json.dumps(event).encode(),
        )

        logger.info(f"✓ Published deliberation completed for {task_id}")

    async def publish_task_dispatched(
        self,
        story_id: str,
        task_id: str,
        agent_id: str,
        role: str,
    ):
        """Publish task dispatched event."""
        event = {
            "event_type": "orchestration.task.dispatched",
            "story_id": story_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "role": role,
            "timestamp": asyncio.get_event_loop().time(),
        }

        await self.publish(
            "orchestration.task.dispatched",
            json.dumps(event).encode(),
        )

        logger.info(f"✓ Published task dispatched: {task_id} to {agent_id}")

    async def close(self):
        """Close NATS connection."""
        if self.nc:
            await self.nc.close()
            logger.info("✓ NATS connection closed")

