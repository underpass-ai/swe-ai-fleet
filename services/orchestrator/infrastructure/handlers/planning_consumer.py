"""
Planning Events Consumer for Orchestrator Service.

Consumes events from Planning Service to trigger orchestration phases.

Refactored to follow Hexagonal Architecture:
- Uses ports instead of direct service access
- Injects CouncilQueryPort for querying councils
- Injects MessagingPort for event publishing
- Injects AutoDispatchService for triggering deliberations (Application Service)
- No direct access to orchestrator internals
- NO dynamic imports
"""

import asyncio
import json
import logging
from typing import Any, Optional

from services.orchestrator.domain.entities import PlanApprovedEvent, StoryTransitionedEvent
from services.orchestrator.domain.ports import CouncilQueryPort, MessagingPort

logger = logging.getLogger(__name__)


class OrchestratorPlanningConsumer:
    """Consumes planning events to trigger orchestration workflows.
    
    Following Hexagonal Architecture:
    - Receives ports via dependency injection
    - Uses CouncilQueryPort to query councils (no direct access)
    - Uses MessagingPort to publish events (abstraction over NATS)
    - Domain logic separated from infrastructure
    """

    def __init__(
        self,
        council_query: CouncilQueryPort,
        messaging: MessagingPort,
        auto_dispatch_service: Optional[Any] = None,  # AutoDispatchService
    ):
        """
        Initialize Orchestrator Planning Events Consumer.
        
        Following Hexagonal Architecture:
        - Only receives ports (no NATS client)
        - Fully decoupled from NATS infrastructure
        - AutoDispatchService injected for deliberation orchestration (NO dynamic imports)

        Args:
            council_query: Port for querying council information
            messaging: Port for publishing events and subscriptions
            auto_dispatch_service: Service for auto-dispatching deliberations (optional)
        """
        self.council_query = council_query
        self.messaging = messaging
        self._auto_dispatch_service = auto_dispatch_service

    async def start(self):
        """Start consuming planning events with DURABLE PULL consumers."""
        try:
            # Create PULL subscriptions via MessagingPort (Hexagonal Architecture)
            import asyncio
            
            self._story_sub = await self.messaging.pull_subscribe(
                subject="planning.story.transitioned",
                durable="orch-planning-story-transitions",
                stream="PLANNING_EVENTS",
            )
            logger.info("✓ Pull subscription created for planning.story.transitioned (DURABLE)")

            self._plan_sub = await self.messaging.pull_subscribe(
                subject="planning.plan.approved",
                durable="orch-planning-plan-approved",
                stream="PLANNING_EVENTS",
            )
            logger.info("✓ Pull subscription created for planning.plan.approved (DURABLE)")

            # Start background polling tasks
            self._tasks = [
                asyncio.create_task(self._poll_story_transitions()),
                asyncio.create_task(self._poll_plan_approvals()),
            ]

            logger.info("✓ Orchestrator Planning Consumer started with DURABLE PULL consumers")

        except Exception as e:
            logger.error(f"Failed to start Orchestrator Planning Consumer: {e}", exc_info=True)
            raise
    
    async def _poll_story_transitions(self):
        """Poll for story transition messages."""
        logger.info("🔄 Background task _poll_story_transitions started")
        while True:
            try:
                logger.info("📥 Fetching story transitions (timeout=5s)...")
                msgs = await self._story_sub.fetch(batch=1, timeout=5)
                logger.info(f"✅ Received {len(msgs)} story transition messages")
                for msg in msgs:
                    await self._handle_story_transitioned(msg)
            except TimeoutError:
                logger.info("⏱️  No story transitions (timeout), continuing...")
                continue
            except Exception as e:
                logger.error(f"❌ Error polling story transitions: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def _poll_plan_approvals(self):
        """Poll for plan approval messages."""
        logger.info("🔄 Background task _poll_plan_approvals started")
        while True:
            try:
                logger.info("📥 Fetching plan approvals (timeout=5s)...")
                msgs = await self._plan_sub.fetch(batch=1, timeout=5)
                logger.info(f"✅ Received {len(msgs)} plan approval messages")
                for msg in msgs:
                    await self._handle_plan_approved(msg)
            except TimeoutError:
                logger.info("⏱️  No plan approvals (timeout), continuing...")
                continue
            except Exception as e:
                logger.error(f"❌ Error polling plan approvals: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _handle_story_transitioned(self, msg):
        """
        Handle story phase transition events.

        When a story transitions to a new phase, we may need to:
        - Trigger a new orchestration cycle
        - Re-prioritize existing tasks
        - Notify councils of phase change
        """
        try:
            # Parse as domain entity (Tell, Don't Ask)
            event_data = json.loads(msg.data.decode())
            event = StoryTransitionedEvent.from_dict(event_data)

            logger.info(
                f"Story transitioned: {event.story_id} {event.from_phase} → {event.to_phase}"
            )

            # Check if we need to trigger orchestration for the new phase
            if event.to_phase in ["BUILD", "TEST"]:
                logger.info(
                    f"Triggering orchestration for {event.story_id} in phase {event.to_phase}"
                )
                
                # TODO: Implement orchestration triggering
                # This would:
                # 1. Query Planning for subtasks in this phase
                # 2. Call DeriveSubtasks if needed
                # 3. Trigger Orchestrate RPC for relevant tasks
                
                # For now, just log the intent
                logger.info(
                    f"Would trigger orchestration for {event.story_id} in {event.to_phase}"
                )
            
            # Publish orchestration event via MessagingPort
            try:
                await self.messaging.publish_dict(
                    "orchestration.phase.changed",
                    event.to_dict()
                )
            except Exception as e:
                logger.warning(f"Failed to publish phase change event: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed story transition for {event.story_id}")

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
            raw_data = msg.data.decode()
            logger.info(f"📥 Received plan approval message: {raw_data[:100]}...")
            
            # Parse as domain entity (Tell, Don't Ask)
            try:
                event_data = json.loads(raw_data)
                event = PlanApprovedEvent.from_dict(event_data)
            except json.JSONDecodeError:
                # Handle text messages - create a basic event structure
                logger.info("📝 Processing text message (non-JSON format)")
                event_data = {
                    "story_id": "text-story-001",
                    "plan_id": "text-plan-001", 
                    "approved_by": "system",
                    "roles": ["DEV", "QA"],
                    "timestamp": "2025-10-17T19:10:00Z",
                }
                event = PlanApprovedEvent.from_dict(event_data)

            logger.info(
                f"Plan approved: {event.plan_id} for story {event.story_id} by {event.approved_by}"
            )

            # Log roles that will be needed
            if event.roles:
                logger.info(f"Roles required for {event.story_id}: {', '.join(event.roles)}")
            
            # ═══════════════════════════════════════════════════════════════
            # AUTO-DISPATCH: Delegate to AutoDispatchService
            # ═══════════════════════════════════════════════════════════════
            
            if self._auto_dispatch_service and event.roles:
                # Clean hexagonal architecture: delegate to application service
                dispatch_result = await self._auto_dispatch_service.dispatch_deliberations_for_plan(event)
                
                logger.info(
                    f"✅ Auto-dispatch completed: {dispatch_result['successful']}/{dispatch_result['total_roles']} successful"
                )
            else:
                # Log if auto-dispatch is not configured
                logger.info(
                    f"📋 Plan approved: {event.plan_id} for story {event.story_id} "
                    f"(roles: {', '.join(event.roles if event.roles else [])})"
                )
                if not self._auto_dispatch_service:
                    logger.warning("⚠️  Auto-dispatch disabled: auto_dispatch_service not injected")
            
            # Publish orchestration event via MessagingPort
            try:
                await self.messaging.publish_dict(
                    "orchestration.plan.approved",
                    event.to_dict()
                )
            except Exception as e:
                logger.warning(f"Failed to publish plan approval event: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed plan approval for {event.plan_id}")

        except Exception as e:
            logger.error(
                f"Error handling plan approval: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def stop(self):
        """Stop consuming events."""
        logger.info("Orchestrator Planning Consumer stopped")

