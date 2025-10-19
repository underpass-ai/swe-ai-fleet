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
from typing import Any

from services.orchestrator.application.usecases import (
    CleanupDeliberationsUseCase,
    DeliberationResultQueryResult,
    GetDeliberationResultUseCase,
    PublishDeliberationCompletedUseCase,
    PublishDeliberationFailedUseCase,
    RecordAgentFailureUseCase,
    RecordAgentResponseUseCase,
)
from services.orchestrator.domain.entities import (
    AgentFailureMessage,
    AgentResponseMessage,
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
            # Note: Using durable + queue_group for persistent load-balanced subscriptions
            # v2 suffix to avoid conflicts with old consumers from pre-hexagonal architecture
            await self.messaging.subscribe(
                subject="agent.response.completed",
                handler=self._handle_agent_completed,
                queue_group="deliberation-collector",
                durable="deliberation-collector-completed-v2",
            )
            
            await self.messaging.subscribe(
                subject="agent.response.failed",
                handler=self._handle_agent_failed,
                queue_group="deliberation-collector",
                durable="deliberation-collector-failed-v2",
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
            # Parse as domain entity (Tell, Don't Ask)
            message_data = json.loads(msg.data.decode())
            message = AgentResponseMessage.from_dict(message_data)
            
            if not message.task_id or not message.agent_id:
                logger.warning("Invalid message: missing task_id or agent_id")
                await msg.ack()
                return
            
            logger.info(f"[{message.task_id}] Received response from {message.agent_id}")
            
            async with self._lock:
                # Use case pattern for recording response
                record_uc = RecordAgentResponseUseCase(self.registry)
                result = record_uc.execute(
                    task_id=message.task_id,
                    agent_id=message.agent_id,
                    role=message.role,
                    proposal=message.proposal,
                    duration_ms=message.duration_ms,
                    timestamp=message.timestamp,
                    expected_agents=message.num_agents,
                )
                
                # Log progress
                if message.num_agents:
                    logger.info(
                        f"[{message.task_id}] Expecting {message.num_agents} agent responses"
                    )
                
                # Check if deliberation is complete
                if result.is_complete:
                    logger.info(
                        f"[{message.task_id}] ✅ Deliberation complete: "
                        f"{result.received_count}/{result.expected_count} responses"
                    )
                    await self._publish_deliberation_complete(message.task_id)
                else:
                    logger.debug(
                        f"[{message.task_id}] Progress: {result.received_count}/"
                        f"{result.expected_count or '?'} responses"
                    )
            
            await msg.ack()
            
        except Exception as e:
            logger.error(f"Error handling agent completed: {e}", exc_info=True)
            await msg.ack()  # Ack anyway to avoid redelivery
    
    async def _handle_agent_failed(self, msg) -> None:
        """Handle agent.response.failed message."""
        try:
            # Parse as domain entity (Tell, Don't Ask)
            message_data = json.loads(msg.data.decode())
            message = AgentFailureMessage.from_dict(message_data)
            
            if not message.task_id:
                logger.warning("Invalid failure message: missing task_id")
                await msg.ack()
                return
            
            logger.error(f"[{message.task_id}] Agent {message.agent_id} failed: {message.error}")
            
            async with self._lock:
                # Use case pattern for recording failure
                record_uc = RecordAgentFailureUseCase(self.registry)
                result = record_uc.execute(
                    task_id=message.task_id,
                    agent_id=message.agent_id,
                    error=message.error,
                    timestamp=message.timestamp,
                )
                
                # Check if deliberation is complete
                if result.is_complete:
                    if result.all_failed:
                        # All agents failed
                        logger.error(
                            f"[{message.task_id}] ❌ All agents failed - "
                            f"marking deliberation as failed"
                        )
                        await self._publish_deliberation_failed(
                            message.task_id,
                            "All agents failed"
                        )
                    else:
                        # Some succeeded
                        logger.warning(
                            f"[{message.task_id}] ⚠️ Deliberation complete with failures: "
                            f"{result.received_count} succeeded, "
                            f"{result.expected_count - result.received_count} failed"
                        )
                        await self._publish_deliberation_complete(message.task_id)
            
            await msg.ack()
            
        except Exception as e:
            logger.error(f"Error handling agent failed: {e}", exc_info=True)
            await msg.ack()
    
    async def _publish_deliberation_complete(self, task_id: str) -> None:
        """Publish deliberation.completed event via use case."""
        async with self._lock:
            publish_uc = PublishDeliberationCompletedUseCase(
                registry=self.registry,
                messaging=self.messaging,
            )
            result = await publish_uc.execute(task_id)
            
            if result.published:
                logger.info(f"[{task_id}] 📢 Published deliberation.completed")
            else:
                logger.error(f"[{task_id}] Failed to publish deliberation.completed")
    
    async def _publish_deliberation_failed(
        self, task_id: str, error_message: str
    ) -> None:
        """Publish deliberation.failed event via use case."""
        async with self._lock:
            publish_uc = PublishDeliberationFailedUseCase(
                registry=self.registry,
                messaging=self.messaging,
            )
            result = await publish_uc.execute(task_id, error_message)
            
            if result.published:
                logger.error(f"[{task_id}] 📢 Published deliberation.failed")
            else:
                logger.error(f"[{task_id}] Failed to publish deliberation.failed")
    
    async def _cleanup_loop(self) -> None:
        """Background task to timeout stuck deliberations and cleanup old results."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                async with self._lock:
                    # Use case pattern for cleanup (Tell, Don't Ask)
                    cleanup_uc = CleanupDeliberationsUseCase(self.registry)
                    cleanup_result = cleanup_uc.execute(
                        timeout_seconds=self.timeout_seconds,
                        cleanup_after_seconds=self.cleanup_after_seconds,
                    )
                    
                    # Publish timeout events for timed-out deliberations
                    for task_id in cleanup_result.timed_out_tasks:
                        logger.warning(
                            f"[{task_id}] ⏰ Deliberation timed out after "
                            f"{self.timeout_seconds}s"
                        )
                        await self._publish_deliberation_failed(
                            task_id,
                            f"Timeout after {self.timeout_seconds}s"
                        )
                    
                    # Log cleanups
                    for task_id in cleanup_result.cleaned_up_tasks:
                        logger.debug(f"[{task_id}] 🧹 Cleaned up old deliberation")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
    
    def get_deliberation_result(self, task_id: str) -> DeliberationResultQueryResult | None:
        """Get deliberation result by task_id.
        
        Delegates to GetDeliberationResultUseCase for business logic.
        
        Args:
            task_id: Task identifier
            
        Returns:
            DeliberationResultQueryResult or None if not found
        """
        use_case = GetDeliberationResultUseCase(self.registry)
        return use_case.execute(task_id)
    
    def get_registry(self) -> DeliberationStateRegistry:
        """Get the deliberation state registry.
        
        This allows direct access when needed (legacy compatibility).
        Prefer using get_deliberation_result() for queries.
        
        Returns:
            DeliberationStateRegistry instance
        """
        return self.registry
    
    def get_stats(self) -> dict[str, Any]:
        """Get collector statistics using domain entity.
        
        Tell, Don't Ask: Delegate to registry's domain method.
        """
        return self.registry.to_stats_dict()

