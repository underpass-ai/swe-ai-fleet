"""
Planning Events Consumer for Orchestrator Service.

Consumes events from Planning Service to trigger orchestration phases.
"""

import json
import logging
from typing import Any

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class OrchestratorPlanningConsumer:
    """Consumes planning events to trigger orchestration workflows."""

    def __init__(
        self,
        nc: NATS,
        js: JetStreamContext,
        orchestrator_service: Any,
        nats_publisher: Any = None,
    ):
        """
        Initialize Orchestrator Planning Events Consumer.

        Args:
            nc: NATS client
            js: JetStream context
            orchestrator_service: OrchestratorServiceServicer instance
            nats_publisher: Optional publisher for orchestration events
        """
        self.nc = nc
        self.js = js
        self.orchestrator = orchestrator_service
        self.publisher = nats_publisher

    async def start(self):
        """Start consuming planning events."""
        try:
            # Subscribe to story transitions (phase changes)
            await self.js.subscribe(
                "planning.story.transitioned",
                queue="orchestrator-workers",
                cb=self._handle_story_transitioned,
            )
            logger.info("✓ Subscribed to planning.story.transitioned")

            # Subscribe to plan approvals
            await self.js.subscribe(
                "planning.plan.approved",
                queue="orchestrator-workers",
                cb=self._handle_plan_approved,
            )
            logger.info("✓ Subscribed to planning.plan.approved")

            logger.info("✓ Orchestrator Planning Consumer started")

        except Exception as e:
            logger.error(f"Failed to start Orchestrator Planning Consumer: {e}")
            raise

    async def _handle_story_transitioned(self, msg):
        """
        Handle story phase transition events.

        When a story transitions to a new phase, we may need to:
        - Trigger a new orchestration cycle
        - Re-prioritize existing tasks
        - Notify councils of phase change
        """
        try:
            event = json.loads(msg.data.decode())
            story_id = event.get("story_id")
            from_phase = event.get("from_phase")
            to_phase = event.get("to_phase")
            timestamp = event.get("timestamp")

            logger.info(
                f"Story transitioned: {story_id} {from_phase} → {to_phase}"
            )

            # Check if we need to trigger orchestration for the new phase
            if to_phase in ["BUILD", "TEST"]:
                logger.info(
                    f"Triggering orchestration for {story_id} in phase {to_phase}"
                )
                
                # TODO: Implement orchestration triggering
                # This would:
                # 1. Query Planning for subtasks in this phase
                # 2. Call DeriveSubtasks if needed
                # 3. Trigger Orchestrate RPC for relevant tasks
                
                # For now, just log the intent
                logger.info(
                    f"Would trigger orchestration for {story_id} in {to_phase}"
                )
            
            # Publish orchestration event if publisher is available
            if self.publisher:
                try:
                    await self.publisher.publish(
                        "orchestration.phase.changed",
                        json.dumps({
                            "story_id": story_id,
                            "from_phase": from_phase,
                            "to_phase": to_phase,
                            "timestamp": timestamp,
                        }).encode(),
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish phase change event: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed story transition for {story_id}")

        except Exception as e:
            logger.error(
                f"Error handling story transition: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def _handle_plan_approved(self, msg):
        """
        Handle plan approval events.

        When a plan is approved, we should:
        - Derive initial subtasks for orchestration
        - Initialize councils for the roles needed
        - Start task queue for execution
        """
        try:
            event = json.loads(msg.data.decode())
            story_id = event.get("story_id")
            plan_id = event.get("plan_id")
            approved_by = event.get("approved_by")
            roles = event.get("roles", [])
            timestamp = event.get("timestamp")

            logger.info(
                f"Plan approved: {plan_id} for story {story_id} by {approved_by}"
            )

            # Log roles that will be needed
            if roles:
                logger.info(f"Roles required for {story_id}: {', '.join(roles)}")
            
            # TODO: Implement task derivation
            # This would call DeriveSubtasks RPC internally
            # and populate the task queue
            
            # Publish orchestration event
            if self.publisher:
                try:
                    await self.publisher.publish(
                        "orchestration.plan.approved",
                        json.dumps({
                            "story_id": story_id,
                            "plan_id": plan_id,
                            "approved_by": approved_by,
                            "roles": roles,
                            "timestamp": timestamp,
                        }).encode(),
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish plan approval event: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed plan approval for {plan_id}")

        except Exception as e:
            logger.error(
                f"Error handling plan approval: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def stop(self):
        """Stop consuming events."""
        logger.info("Orchestrator Planning Consumer stopped")

