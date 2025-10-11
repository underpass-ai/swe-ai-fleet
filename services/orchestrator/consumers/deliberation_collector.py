"""NATS consumer for collecting deliberation results from Ray agents."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

import nats
from nats.js import JetStreamContext

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
        nats_url: str = "nats://nats:4222",
        timeout_seconds: int = 300,  # 5 minutes
        cleanup_after_seconds: int = 3600,  # 1 hour
    ):
        """Initialize the deliberation result collector.
        
        Args:
            nats_url: URL of the NATS server
            timeout_seconds: Timeout for deliberations (default: 300s)
            cleanup_after_seconds: Time to keep completed results (default: 3600s)
        """
        self.nats_url = nats_url
        self.timeout_seconds = timeout_seconds
        self.cleanup_after_seconds = cleanup_after_seconds
        
        # NATS connection
        self.nc: nats.NATS | None = None
        self.js: JetStreamContext | None = None
        
        # Storage for deliberations in progress
        # Format: {task_id: {"expected": N, "received": [], "started_at": datetime, ...}}
        self.deliberations: dict[str, dict[str, Any]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        
        # Background task for timeout/cleanup
        self._cleanup_task: asyncio.Task | None = None
        
        logger.info(
            f"DeliberationResultCollector initialized: "
            f"nats={nats_url}, timeout={timeout_seconds}s"
        )
    
    async def start(self) -> None:
        """Start the consumer and connect to NATS."""
        try:
            # Connect to NATS
            logger.info(f"Connecting to NATS at {self.nats_url}")
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            
            # Subscribe to agent responses (completed)
            await self.js.subscribe(
                subject="agent.response.completed",
                cb=self._handle_agent_completed,
                stream="AGENT_RESPONSES",
                durable="deliberation-collector-completed",
                manual_ack=True,
            )
            
            # Subscribe to agent responses (failed)
            await self.js.subscribe(
                subject="agent.response.failed",
                cb=self._handle_agent_failed,
                stream="AGENT_RESPONSES",
                durable="deliberation-collector-failed",
                manual_ack=True,
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
        
        # Close NATS connection
        if self.nc:
            await self.nc.close()
        
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
                # Initialize deliberation if first message
                if task_id not in self.deliberations:
                    self.deliberations[task_id] = {
                        "expected": None,  # Will be set from first message
                        "received": [],
                        "failed": [],
                        "started_at": datetime.utcnow(),
                        "status": "in_progress",
                    }
                
                delib = self.deliberations[task_id]
                
                # Set expected count from first message (if available)
                if delib["expected"] is None and "num_agents" in data:
                    delib["expected"] = data["num_agents"]
                    logger.info(
                        f"[{task_id}] Expecting {delib['expected']} agent responses"
                    )
                
                # Add result
                delib["received"].append({
                    "agent_id": agent_id,
                    "role": data.get("role"),
                    "proposal": data.get("proposal"),
                    "duration_ms": data.get("duration_ms", 0),
                    "timestamp": data.get("timestamp"),
                })
                
                # Check if deliberation is complete
                received_count = len(delib["received"])
                expected_count = delib["expected"]
                
                if expected_count and received_count >= expected_count:
                    logger.info(
                        f"[{task_id}] ✅ Deliberation complete: "
                        f"{received_count}/{expected_count} responses"
                    )
                    await self._publish_deliberation_complete(task_id)
                else:
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
                if task_id not in self.deliberations:
                    self.deliberations[task_id] = {
                        "expected": None,
                        "received": [],
                        "failed": [],
                        "started_at": datetime.utcnow(),
                        "status": "in_progress",
                    }
                
                delib = self.deliberations[task_id]
                delib["failed"].append({
                    "agent_id": agent_id,
                    "error": error,
                    "timestamp": data.get("timestamp"),
                })
                
                # Check if we should still wait for more responses
                # or fail the entire deliberation
                total_responses = len(delib["received"]) + len(delib["failed"])
                expected = delib["expected"]
                
                if expected and total_responses >= expected:
                    # All agents responded (some failed)
                    if len(delib["received"]) == 0:
                        # All failed
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
                            f"{len(delib['received'])} succeeded, "
                            f"{len(delib['failed'])} failed"
                        )
                        await self._publish_deliberation_complete(task_id)
            
            await msg.ack()
            
        except Exception as e:
            logger.error(f"Error handling agent failed: {e}", exc_info=True)
            await msg.ack()
    
    async def _publish_deliberation_complete(self, task_id: str) -> None:
        """Publish deliberation.completed event."""
        async with self._lock:
            delib = self.deliberations.get(task_id)
            if not delib:
                return
            
            # Calculate total duration
            started_at = delib.get("started_at", datetime.utcnow())
            duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
            
            # Prepare result
            result = {
                "task_id": task_id,
                "status": "completed",
                "results": delib["received"],
                "failed_agents": delib.get("failed", []),
                "total_agents": delib.get("expected"),
                "successful_responses": len(delib["received"]),
                "failed_responses": len(delib.get("failed", [])),
                "duration_ms": duration_ms,
                "completed_at": datetime.utcnow().isoformat(),
            }
            
            # Update status
            delib["status"] = "completed"
            delib["result"] = result
            delib["completed_at"] = datetime.utcnow()
            
            # Publish to NATS
            if self.js:
                try:
                    await self.js.publish(
                        subject="deliberation.completed",
                        payload=json.dumps(result).encode(),
                    )
                    logger.info(
                        f"[{task_id}] 📢 Published deliberation.completed "
                        f"({len(delib['received'])} results)"
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
            delib = self.deliberations.get(task_id)
            if not delib:
                return
            
            result = {
                "task_id": task_id,
                "status": "failed",
                "error": error_message,
                "failed_agents": delib.get("failed", []),
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Update status
            delib["status"] = "failed"
            delib["result"] = result
            delib["completed_at"] = datetime.utcnow()
            
            # Publish to NATS
            if self.js:
                try:
                    await self.js.publish(
                        subject="deliberation.failed",
                        payload=json.dumps(result).encode(),
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
                
                now = datetime.utcnow()
                
                async with self._lock:
                    tasks_to_timeout = []
                    tasks_to_cleanup = []
                    
                    for task_id, delib in list(self.deliberations.items()):
                        started_at = delib.get("started_at")
                        completed_at = delib.get("completed_at")
                        status = delib.get("status")
                        
                        # Check for timeout (in progress)
                        if status == "in_progress" and started_at:
                            age = (now - started_at).total_seconds()
                            if age > self.timeout_seconds:
                                tasks_to_timeout.append(task_id)
                        
                        # Check for cleanup (completed/failed)
                        if status in ["completed", "failed"] and completed_at:
                            age = (now - completed_at).total_seconds()
                            if age > self.cleanup_after_seconds:
                                tasks_to_cleanup.append(task_id)
                    
                    # Timeout stuck deliberations
                    for task_id in tasks_to_timeout:
                        logger.warning(
                            f"[{task_id}] ⏰ Deliberation timed out after "
                            f"{self.timeout_seconds}s"
                        )
                        await self._publish_deliberation_failed(
                            task_id,
                            f"Timeout after {self.timeout_seconds}s"
                        )
                    
                    # Cleanup old deliberations
                    for task_id in tasks_to_cleanup:
                        logger.debug(f"[{task_id}] 🧹 Cleaning up old deliberation")
                        del self.deliberations[task_id]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
    
    def get_deliberation_result(self, task_id: str) -> dict[str, Any] | None:
        """
        Get deliberation result by task_id (for GetDeliberationResult RPC).
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dictionary with deliberation result or None if not found
        """
        delib = self.deliberations.get(task_id)
        if not delib:
            return None
        
        status = delib.get("status", "pending")
        
        # Map internal status to proto enum
        status_map = {
            "in_progress": "DELIBERATION_STATUS_IN_PROGRESS",
            "completed": "DELIBERATION_STATUS_COMPLETED",
            "failed": "DELIBERATION_STATUS_FAILED",
        }
        
        return {
            "task_id": task_id,
            "status": status_map.get(status, "DELIBERATION_STATUS_PENDING"),
            "results": delib.get("received", []),
            "error_message": delib.get("result", {}).get("error", ""),
            "duration_ms": delib.get("result", {}).get("duration_ms", 0),
            "total_agents": delib.get("expected"),
            "received_count": len(delib.get("received", [])),
            "failed_count": len(delib.get("failed", [])),
        }
    
    def get_stats(self) -> dict[str, Any]:
        """Get collector statistics."""
        in_progress = sum(
            1 for d in self.deliberations.values() if d.get("status") == "in_progress"
        )
        completed = sum(
            1 for d in self.deliberations.values() if d.get("status") == "completed"
        )
        failed = sum(
            1 for d in self.deliberations.values() if d.get("status") == "failed"
        )
        
        return {
            "total_deliberations": len(self.deliberations),
            "in_progress": in_progress,
            "completed": completed,
            "failed": failed,
            "connected": self.nc is not None and not self.nc.is_closed,
        }

