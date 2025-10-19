"""
Planning Events Consumer for Orchestrator Service.

Consumes events from Planning Service to trigger orchestration phases.
"""

import asyncio
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
        """Start consuming planning events with DURABLE PULL consumers."""
        try:
            # Create PULL subscriptions - allows multiple pods to share consumer
            import asyncio
            
            self._story_sub = await self.js.pull_subscribe(
                subject="planning.story.transitioned",
                durable="orch-planning-story-transitions",
                stream="PLANNING_EVENTS",
            )
            logger.info("✓ Pull subscription created for planning.story.transitioned (DURABLE)")

            self._plan_sub = await self.js.pull_subscribe(
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
            raw_data = msg.data.decode()
            logger.info(f"📥 Received plan approval message: {raw_data[:100]}...")
            
            # Try to parse as JSON first, fallback to text message
            try:
                event = json.loads(raw_data)
                story_id = event.get("story_id")
                plan_id = event.get("plan_id")
                approved_by = event.get("approved_by")
                roles = event.get("roles", [])
                timestamp = event.get("timestamp")
            except json.JSONDecodeError:
                # Handle text messages - create a basic event structure
                logger.info("📝 Processing text message (non-JSON format)")
                event = {
                    "story_id": "text-story-001",
                    "plan_id": "text-plan-001", 
                    "approved_by": "system",
                    "roles": ["DEV", "QA"],
                    "timestamp": "2025-10-17T19:10:00Z",
                    "message": raw_data
                }
                story_id = event["story_id"]
                plan_id = event["plan_id"]
                approved_by = event["approved_by"]
                roles = event["roles"]
                timestamp = event["timestamp"]

            logger.info(
                f"Plan approved: {plan_id} for story {story_id} by {approved_by}"
            )

            # Log roles that will be needed
            if roles:
                logger.info(f"Roles required for {story_id}: {', '.join(roles)}")
            
            # ═══════════════════════════════════════════════════════════════
            # AUTO-DISPATCH: Submit deliberations to Ray for each role
            # ═══════════════════════════════════════════════════════════════
            
            if self.orchestrator and hasattr(self.orchestrator, 'deliberate_async'):
                logger.info(f"🚀 Auto-dispatching deliberations for {len(roles)} roles...")
                
                for role in roles:
                    # Verify council exists
                    if role not in self.orchestrator.councils:
                        logger.warning(f"⚠️  Council for {role} not found, skipping")
                        continue
                    
                    council = self.orchestrator.councils[role]
                    if not council:
                        logger.warning(f"⚠️  Council {role} is empty, skipping")
                        continue
                    
                    # Get agents for this council
                    agents = self.orchestrator.council_agents.get(role, [])
                    if not agents:
                        logger.warning(f"⚠️  No agents in council {role}, skipping")
                        continue
                    
                    # Create task for this role
                    task_description = (
                        f"As a {role}, analyze and plan implementation for story: {story_id}.\n"
                        f"Plan ID: {plan_id}\n"
                        f"Your role is to contribute your expertise as {role} to this story."
                    )
                    
                    task_id = f"{story_id}-{role}-deliberation"
                    
                    try:
                        logger.info(
                            f"📤 Submitting deliberation to Ray: {task_id} "
                            f"(council: {role}, {len(agents)} agents)"
                        )
                        
                        # Submit to Ray Executor via gRPC (async method)
                        result = await self.orchestrator.deliberate_async.execute(
                            task_id=task_id,
                            task_description=task_description,
                            role=role,
                            num_agents=len(agents),
                            constraints={
                                "story_id": story_id,
                                "plan_id": plan_id,
                                "approved_by": approved_by,
                            },
                            enable_tools=False,  # Text-only deliberation for now
                        )
                        
                        logger.info(f"✅ Deliberation submitted via Ray Executor: {task_id}")
                        logger.info(f"   Deliberation ID: {result.get('deliberation_id', 'unknown')}")
                        logger.info(f"   Status: {result.get('status', 'unknown')}")
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to submit deliberation for {role}: {e}", exc_info=True)
            else:
                logger.warning("⚠️  Auto-dispatch disabled: deliberate_async not available")
            
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

