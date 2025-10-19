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

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

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
        nc: NATS,
        js: JetStreamContext,
    ):
        """
        Initialize Orchestrator Context Events Consumer.

        Args:
            nc: NATS client
            js: JetStream context
        """
        self.nc = nc
        self.js = js

    async def start(self):
        """Start consuming context events with DURABLE PULL consumers."""
        try:
            # Create PULL subscriptions - allows multiple pods to share consumer
            import asyncio
            
            self._updated_sub = await self.js.pull_subscribe(
                subject="context.updated",
                durable="orch-context-updated",
                stream="CONTEXT",
            )
            logger.info("✓ Pull subscription created for context.updated (DURABLE)")

            self._milestone_sub = await self.js.pull_subscribe(
                subject="context.milestone.reached",
                durable="orch-context-milestone",
                stream="CONTEXT",
            )
            logger.info("✓ Pull subscription created for context.milestone.reached (DURABLE)")

            self._decision_sub = await self.js.pull_subscribe(
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

