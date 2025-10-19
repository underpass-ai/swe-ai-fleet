"""NATS consumer for collecting deliberation results from Ray agents.

Refactored to follow Hexagonal Architecture:
- Uses DeliberationStateRegistry (domain entity) instead of dict[str, dict]
- Uses MessagingPort for subscriptions
- Uses DeliberationTrackerPort for state management
- No direct NATS access
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from services.orchestrator.domain.entities import (
    AgentFailure,
    AgentResponse,
    DeliberationStateRegistry,
)
from services.orchestrator.domain.ports import MessagingPort

logger = logging.getLogger(__name__)


class DeliberationResultCollector:
    """
    NATS consumer that collects agent responses and publishes final deliberation results.
    
    This consumer:
    1. Subscribes to agent.response.completed and agent.response.failed
    2. Accumulates results by task_id
    3. When all expected agents respond → publishes deliberation.completed
    4. Stores results in memory for GetDeliberationResult queries
    5. Handles timeouts for stuck deliberations
    
    Design decisions:
    - In-memory storage (can be replaced with Redis/DB for production)
    - Timeout mechanism to handle missing agent responses
    - Thread-safe with asyncio locks
    """
    
    def __init__(
        self,
        messaging: MessagingPort,
        timeout_seconds: int = 300,  # 5 minutes
        cleanup_after_seconds: int = 3600,  # 1 hour
    ):
        """Initialize the deliberation result collector.
        
        Following Hexagonal Architecture:
        - Receives MessagingPort via dependency injection
        - Uses DeliberationStateRegistry (domain entity) instead of dict
        - No direct NATS access
        
        Args:
            messaging: MessagingPort for subscriptions and publishing
            timeout_seconds: Timeout for deliberations (default: 300s)
            cleanup_after_seconds: Time to keep completed results (default: 3600s)
        """
        self.timeout_seconds = timeout_seconds
        self.cleanup_after_seconds = cleanup_after_seconds
        self.messaging = messaging
        
        # Domain entity for tracking deliberations (replaces dict[str, dict])
        self.registry = DeliberationStateRegistry()
        self._lock = asyncio.Lock()
        
        # Background task for timeout/cleanup
        self._cleanup_task: asyncio.Task | None = None
        
        logger.info(
            f"DeliberationResultCollector initialized: "
            f"timeout={timeout_seconds}s, cleanup={cleanup_after_seconds}s"
        )
    
    async def start(self) -> None:
        """Start the consumer via MessagingPort (Hexagonal Architecture)."""
        try:
            # Subscribe to agent responses via MessagingPort only (no direct NATS)
            await self.messaging.subscribe(
                subject="agent.response.completed",
                handler=self._handle_agent_completed,
                queue_group="deliberation-collector",
                durable="deliberation-collector-completed",
            )
            
            await self.messaging.subscribe(
                subject="agent.response.failed",
                handler=self._handle_agent_failed,
                queue_group="deliberation-collector",
                durable="deliberation-collector-failed",
            )
            
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info("✅ DeliberationResultCollector started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start DeliberationResultCollector: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the consumer and cleanup."""
        logger.info("Stopping DeliberationResultCollector...")
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ DeliberationResultCollector stopped")
    
    async def _handle_agent_completed(self, msg) -> None:
        """Handle agent.response.completed message."""
        try:
            data = json.loads(msg.data.decode())
            task_id = data.get("task_id")
            agent_id = data.get("agent_id")
            
            if not task_id or not agent_id:
                logger.warning("Invalid message: missing task_id or agent_id")
                await msg.ack()
                return
            
            logger.info(f"[{task_id}] Received response from {agent_id}")
            
            async with self._lock:
                # Get or create deliberation state (domain entity)
                state = self.registry.get_or_create(task_id)
                
                # Set expected count from first message (if available)
                if "num_agents" in data:
                    state.set_expected_agents(data["num_agents"])
                    logger.info(
                        f"[{task_id}] Expecting {data['num_agents']} agent responses"
                    )
                
                # Add response (using domain entity)
                response = AgentResponse(
                    agent_id=agent_id,
                    role=data.get("role", "unknown"),
                    proposal=data.get("proposal", {}),
                    duration_ms=data.get("duration_ms", 0),
                    timestamp=data.get("timestamp", ""),
                )
                state.add_response(response)
                
                # Check if deliberation is complete (Tell, Don't Ask)
                if state.is_complete():
                    received_count, expected_count = state.get_progress_count()
                    logger.info(
                        f"[{task_id}] ✅ Deliberation complete: "
                        f"{received_count}/{expected_count} responses"
                    )
                    await self._publish_deliberation_complete(task_id)
                else:
                    received_count, expected_count = state.get_progress_count()
                    logger.debug(
                        f"[{task_id}] Progress: {received_count}/"
                        f"{expected_count or '?'} responses"
                    )
            
            await msg.ack()
            
        except Exception as e:
            logger.error(f"Error handling agent completed: {e}", exc_info=True)
            await msg.ack()  # Ack anyway to avoid redelivery
    
    async def _handle_agent_failed(self, msg) -> None:
        """Handle agent.response.failed message."""
        try:
            data = json.loads(msg.data.decode())
            task_id = data.get("task_id")
            agent_id = data.get("agent_id")
            error = data.get("error", "Unknown error")
            
            if not task_id:
                logger.warning("Invalid failure message: missing task_id")
                await msg.ack()
                return
            
            logger.error(f"[{task_id}] Agent {agent_id} failed: {error}")
            
            async with self._lock:
                # Get or create deliberation state (domain entity)
                state = self.registry.get_or_create(task_id)
                
                # Add failure (using domain entity)
                failure = AgentFailure(
                    agent_id=agent_id,
                    error=error,
                    timestamp=data.get("timestamp", ""),
                )
                state.add_failure(failure)
                
                # Check if deliberation is complete (Tell, Don't Ask)
                if state.is_complete():
                    if state.all_failed():
                        # All agents failed
                        logger.error(
                            f"[{task_id}] ❌ All agents failed - "
                            f"marking deliberation as failed"
                        )
                        await self._publish_deliberation_failed(
                            task_id,
                            "All agents failed"
                        )
                    else:
                        # Some succeeded
                        logger.warning(
                            f"[{task_id}] ⚠️ Deliberation complete with failures: "
                            f"{len(state.received)} succeeded, "
                            f"{len(state.failed)} failed"
                        )
                        await self._publish_deliberation_complete(task_id)
            
            await msg.ack()
            
        except Exception as e:
            logger.error(f"Error handling agent failed: {e}", exc_info=True)
            await msg.ack()
    
    async def _publish_deliberation_complete(self, task_id: str) -> None:
        """Publish deliberation.completed event."""
        async with self._lock:
            state = self.registry.get_state(task_id)
            if not state:
                return
            
            # Calculate total duration (using domain entity)
            duration_ms = state.get_duration_ms()
            
            # Prepare result
            result = {
                "task_id": task_id,
                "status": "completed",
                "results": [r.__dict__ for r in state.received],  # Convert to dict
                "failed_agents": [f.__dict__ for f in state.failed],
                "total_agents": state.expected_agents,
                "successful_responses": len(state.received),
                "failed_responses": len(state.failed),
                "duration_ms": duration_ms,
                "completed_at": datetime.now(UTC).isoformat(),
            }
            
            # Mark state as completed (Tell, Don't Ask)
            state.mark_completed(result)
            
            # Publish via MessagingPort (Hexagonal Architecture)
            if self.messaging:
                try:
                    await self.messaging.publish_dict(
                        subject="deliberation.completed",
                        data=result,
                    )
                    logger.info(
                        f"[{task_id}] 📢 Published deliberation.completed "
                        f"({len(state.received)} results)"
                    )
                except Exception as e:
                    logger.error(
                        f"[{task_id}] Failed to publish deliberation.completed: {e}"
                    )
    
    async def _publish_deliberation_failed(
        self, task_id: str, error_message: str
    ) -> None:
        """Publish deliberation.failed event."""
        async with self._lock:
            state = self.registry.get_state(task_id)
            if not state:
                return
            
            result = {
                "task_id": task_id,
                "status": "failed",
                "error": error_message,
                "failed_agents": [f.__dict__ for f in state.failed],
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            # Mark state as failed (Tell, Don't Ask)
            state.mark_failed(error_message)
            
            # Publish via MessagingPort (Hexagonal Architecture)
            if self.messaging:
                try:
                    await self.messaging.publish_dict(
                        subject="deliberation.failed",
                        data=result,
                    )
                    logger.error(f"[{task_id}] 📢 Published deliberation.failed")
                except Exception as e:
                    logger.error(
                        f"[{task_id}] Failed to publish deliberation.failed: {e}"
                    )
    
    async def _cleanup_loop(self) -> None:
        """Background task to timeout stuck deliberations and cleanup old results."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                async with self._lock:
                    # Use domain entity methods (Tell, Don't Ask)
                    timed_out_states = self.registry.get_timed_out(self.timeout_seconds)
                    cleanup_states = self.registry.get_for_cleanup(self.cleanup_after_seconds)
                    
                    # Timeout stuck deliberations
                    for state in timed_out_states:
                        logger.warning(
                            f"[{state.task_id}] ⏰ Deliberation timed out after "
                            f"{self.timeout_seconds}s"
                        )
                        await self._publish_deliberation_failed(
                            state.task_id,
                            f"Timeout after {self.timeout_seconds}s"
                        )
                    
                    # Cleanup old deliberations
                    for state in cleanup_states:
                        logger.debug(f"[{state.task_id}] 🧹 Cleaning up old deliberation")
                        self.registry.remove_state(state.task_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
    
    def get_deliberation_result(self, task_id: str) -> dict[str, Any] | None:
        """
        Get deliberation result by task_id (for GetDeliberationResult RPC).
        
        Uses DeliberationState domain entity instead of raw dict.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dictionary with deliberation result or None if not found
        """
        state = self.registry.get_state(task_id)
        if not state:
            return None
        
        # Map internal status to proto enum
        status_map = {
            "in_progress": "DELIBERATION_STATUS_IN_PROGRESS",
            "completed": "DELIBERATION_STATUS_COMPLETED",
            "failed": "DELIBERATION_STATUS_FAILED",
        }
        
        return {
            "task_id": task_id,
            "status": status_map.get(state.status, "DELIBERATION_STATUS_PENDING"),
            "results": [r.__dict__ for r in state.received],
            "error_message": state.final_result.get("error", "") if state.final_result else "",
            "duration_ms": state.get_duration_ms(),
            "total_agents": state.expected_agents,
            "received_count": len(state.received),
            "failed_count": len(state.failed),
        }
    
    def get_stats(self) -> dict[str, Any]:
        """Get collector statistics using domain entity."""
        # Use registry's domain methods (Tell, Don't Ask)
        counts = self.registry.count_by_status()
        
        return {
            "total_deliberations": self.registry.count(),
            "in_progress": counts["in_progress"],
            "completed": counts["completed"],
            "failed": counts["failed"],
        }

