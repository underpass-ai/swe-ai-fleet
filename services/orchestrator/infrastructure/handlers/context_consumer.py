"""
Context Events Consumer for Orchestrator Service.

Consumes events from Context Service to react to context changes.

Refactored to follow Hexagonal Architecture:
- Removed direct access to orchestrator service
- Simplified to minimal event logging
- TODOs documented for future implementation
"""

import asyncio
import json
import logging

from services.orchestrator.domain.entities import (
    ContextUpdatedEvent,
    DecisionAddedEvent,
    MilestoneReachedEvent,
)
from services.orchestrator.domain.ports import MessagingPort

logger = logging.getLogger(__name__)


class OrchestratorContextConsumer:
    """Consumes context events to re-evaluate orchestration decisions.

    Following Hexagonal Architecture:
    - No direct dependencies on orchestrator service
    - Lightweight consumer for event logging
    - Future: Inject use cases for context re-evaluation
    """

    def __init__(
        self,
        messaging: MessagingPort,
    ):
        """
        Initialize Orchestrator Context Events Consumer.

        Following Hexagonal Architecture:
        - Only receives MessagingPort (no NATS client)
        - Fully decoupled from NATS infrastructure

        Args:
            messaging: Port for messaging operations
        """
        self.messaging = messaging

    async def start(self):
        """Start consuming context events with DURABLE PULL consumers."""
        try:
            # Create PULL subscriptions via MessagingPort (Hexagonal Architecture)
            import asyncio

            self._updated_sub = await self.messaging.pull_subscribe(
                subject="context.updated",
                durable="orch-context-updated",
                stream="CONTEXT",
            )
            logger.info("✓ Pull subscription created for context.updated (DURABLE)")

            self._milestone_sub = await self.messaging.pull_subscribe(
                subject="context.milestone.reached",
                durable="orch-context-milestone",
                stream="CONTEXT",
            )
            logger.info("✓ Pull subscription created for context.milestone.reached (DURABLE)")

            self._decision_sub = await self.messaging.pull_subscribe(
                subject="context.decision.added",
                durable="orch-context-decision",
                stream="CONTEXT",
            )
            logger.info("✓ Pull subscription created for context.decision.added (DURABLE)")

            # Start background polling tasks
            self._tasks = [
                asyncio.create_task(self._poll_context_updated()),
                asyncio.create_task(self._poll_milestones()),
                asyncio.create_task(self._poll_decisions()),
            ]

            logger.info("✓ Orchestrator Context Consumer started with DURABLE PULL consumers")

        except Exception as e:
            logger.error(f"Failed to start Orchestrator Context Consumer: {e}", exc_info=True)
            raise

    async def _poll_context_updated(self):
        """Poll for context updated messages."""
        while True:
            try:
                msgs = await self._updated_sub.fetch(batch=1, timeout=5)
                for msg in msgs:
                    await self._handle_context_updated(msg)
            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error polling context updated: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _poll_milestones(self):
        """Poll for milestone messages."""
        while True:
            try:
                msgs = await self._milestone_sub.fetch(batch=1, timeout=5)
                for msg in msgs:
                    await self._handle_milestone_reached(msg)
            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error polling milestones: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _poll_decisions(self):
        """Poll for decision messages."""
        while True:
            try:
                msgs = await self._decision_sub.fetch(batch=1, timeout=5)
                for msg in msgs:
                    await self._handle_decision_added(msg)
            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error polling decisions: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _handle_context_updated(self, msg):
        """
        Handle context update events.

        When context is updated, we may need to:
        - Re-evaluate current tasks with new context
        - Adjust priorities based on new information
        - Invalidate cached task contexts
        """
        try:
            # Parse as domain entity (Tell, Don't Ask)
            event_data = json.loads(msg.data.decode())
            event = ContextUpdatedEvent.from_dict(event_data)

            logger.info(
                f"Context updated: {event.story_id} version {event.version}"
            )

            # IMPLEMENTATION STATUS: Basic event consumption and logging.
            # FUTURE ENHANCEMENTS needed:
            # - Identify tasks currently in progress for this story
            # - Analyze if context changes affect task execution
            # - Implement pause/restart logic for affected tasks
            # - Hot-reload context for running agents

            # For now, just log
            logger.debug(
                f"Context version {event.version} available for {event.story_id}"
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
            # Parse as domain entity (Tell, Don't Ask)
            event_data = json.loads(msg.data.decode())
            event = MilestoneReachedEvent.from_dict(event_data)

            logger.info(
                f"Milestone reached: {event.milestone_name} ({event.milestone_id}) for {event.story_id}"
            )

            # IMPLEMENTATION STATUS: Basic event consumption and logging.
            # FUTURE ENHANCEMENTS needed:
            # - Send notification to Planning Service via gRPC
            # - Update progress metrics and analytics
            # - Trigger next phase planning if applicable
            # - Publish to stakeholder notification system

            await msg.ack()
            logger.debug(f"✓ Processed milestone {event.milestone_id}")

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
            # Parse as domain entity (Tell, Don't Ask)
            event_data = json.loads(msg.data.decode())
            event = DecisionAddedEvent.from_dict(event_data)

            logger.info(
                f"Decision added: {event.decision_id} ({event.decision_type}) for {event.story_id}"
            )

            # IMPLEMENTATION STATUS: Basic event consumption and logging.
            # FUTURE ENHANCEMENTS needed:
            # - Analyze decision impact on task execution order
            # - Detect if re-planning is required
            # - Adjust resource allocation based on decision
            # - Update task dependencies dynamically

            await msg.ack()
            logger.debug(f"✓ Processed decision {event.decision_id}")

        except Exception as e:
            logger.error(
                f"Error handling decision: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def stop(self):
        """Stop consuming events."""
        await asyncio.sleep(0)  # Make function truly async
        logger.info("Orchestrator Context Consumer stopped")

