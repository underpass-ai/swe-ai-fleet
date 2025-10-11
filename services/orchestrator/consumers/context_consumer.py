"""
Context Events Consumer for Orchestrator Service.

Consumes events from Context Service to react to context changes.
"""

import json
import logging
from typing import Any

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class OrchestratorContextConsumer:
    """Consumes context events to re-evaluate orchestration decisions."""

    def __init__(
        self,
        nc: NATS,
        js: JetStreamContext,
        orchestrator_service: Any,
    ):
        """
        Initialize Orchestrator Context Events Consumer.

        Args:
            nc: NATS client
            js: JetStream context
            orchestrator_service: OrchestratorServiceServicer instance
        """
        self.nc = nc
        self.js = js
        self.orchestrator = orchestrator_service

    async def start(self):
        """Start consuming context events."""
        try:
            # Subscribe to context updates
            await self.js.subscribe(
                "context.updated",
                queue="orchestrator-workers",
                cb=self._handle_context_updated,
            )
            logger.info("✓ Subscribed to context.updated")

            # Subscribe to context milestones
            await self.js.subscribe(
                "context.milestone.reached",
                queue="orchestrator-workers",
                cb=self._handle_milestone_reached,
            )
            logger.info("✓ Subscribed to context.milestone.reached")

            # Subscribe to decision changes
            await self.js.subscribe(
                "context.decision.added",
                queue="orchestrator-workers",
                cb=self._handle_decision_added,
            )
            logger.info("✓ Subscribed to context.decision.added")

            logger.info("✓ Orchestrator Context Consumer started")

        except Exception as e:
            logger.error(f"Failed to start Orchestrator Context Consumer: {e}")
            raise

    async def _handle_context_updated(self, msg):
        """
        Handle context update events.

        When context is updated, we may need to:
        - Re-evaluate current tasks with new context
        - Adjust priorities based on new information
        - Invalidate cached task contexts
        """
        try:
            event = json.loads(msg.data.decode())
            story_id = event.get("story_id")
            version = event.get("version")

            logger.info(
                f"Context updated: {story_id} version {version}"
            )

            # TODO: Implement context re-evaluation
            # This would:
            # 1. Identify tasks currently in progress for this story
            # 2. Check if context changes affect their execution
            # 3. Optionally pause/restart tasks with new context
            
            # For now, just log
            logger.debug(
                f"Context version {version} available for {story_id}"
            )

            await msg.ack()

        except Exception as e:
            logger.error(
                f"Error handling context update: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def _handle_milestone_reached(self, msg):
        """
        Handle milestone reached events.

        Milestones can trigger:
        - Progress reports
        - Phase transitions
        - Notification of stakeholders
        """
        try:
            event = json.loads(msg.data.decode())
            story_id = event.get("story_id")
            milestone_id = event.get("milestone_id")
            milestone_name = event.get("milestone_name")

            logger.info(
                f"Milestone reached: {milestone_name} ({milestone_id}) for {story_id}"
            )

            # TODO: Implement milestone handling
            # Could trigger:
            # - Notification to Planning Service
            # - Progress metrics update
            # - Next phase planning
            
            await msg.ack()
            logger.debug(f"✓ Processed milestone {milestone_id}")

        except Exception as e:
            logger.error(
                f"Error handling milestone: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def _handle_decision_added(self, msg):
        """
        Handle decision added events.

        New decisions can affect:
        - Task priorities
        - Task dependencies
        - Resource allocation
        """
        try:
            event = json.loads(msg.data.decode())
            story_id = event.get("story_id")
            decision_id = event.get("decision_id")
            decision_type = event.get("decision_type", "TECHNICAL")

            logger.info(
                f"Decision added: {decision_id} ({decision_type}) for {story_id}"
            )

            # TODO: Implement decision impact analysis
            # Check if this decision:
            # - Affects task execution order
            # - Requires re-planning
            # - Impacts resource allocation
            
            await msg.ack()
            logger.debug(f"✓ Processed decision {decision_id}")

        except Exception as e:
            logger.error(
                f"Error handling decision: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def stop(self):
        """Stop consuming events."""
        logger.info("Orchestrator Context Consumer stopped")

