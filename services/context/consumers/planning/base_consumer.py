"""Base consumer for Planning events.

Provides common polling logic and error handling.
"""

import asyncio
import logging
from typing import Any, Callable

from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class BasePlanningConsumer:
    """Base class for planning event consumers.

    Provides:
    - Common polling loop
    - Error handling with exponential backoff
    - Structured logging

    Subclasses must implement:
    - start(): Create subscription and start polling
    - _handle_message(msg): Process single message
    """

    def __init__(
        self,
        js: JetStreamContext,
        graph_command: Any,
        cache_service: Any | None = None,
    ) -> None:
        """Initialize base consumer.

        Args:
            js: JetStream context for NATS
            graph_command: Neo4j command store (GraphCommandPort)
            cache_service: Optional Valkey/Redis client
        """
        self.js = js
        self.graph = graph_command
        self.cache = cache_service
        self._subscription = None
        self._polling_task = None

    async def _poll_messages(
        self,
        subscription,
        handler: Callable,
        batch_size: int = 10,
        timeout: float = 5.0,
    ) -> None:
        """Generic polling loop with error handling.

        Args:
            subscription: NATS pull subscription
            handler: Async function to handle each message
            batch_size: Number of messages to fetch per batch
            timeout: Timeout in seconds for fetch operation
        """
        consumer_name = self.__class__.__name__
        logger.info(f"🔄 {consumer_name} polling started (batch={batch_size}, timeout={timeout}s)")

        error_count = 0
        max_errors = 5
        backoff_seconds = 1

        while True:
            try:
                # Fetch batch of messages
                msgs = await subscription.fetch(batch=batch_size, timeout=timeout)

                if msgs:
                    logger.debug(f"✅ {consumer_name} received {len(msgs)} messages")

                    # Process each message
                    for msg in msgs:
                        try:
                            await handler(msg)
                        except Exception as e:
                            logger.error(
                                f"❌ {consumer_name} failed to process message: {e}",
                                exc_info=True,
                            )
                            # NAK will be handled by individual handler

                    # Reset error count on successful batch
                    error_count = 0
                    backoff_seconds = 1

            except TimeoutError:
                # No messages available, continue polling
                logger.debug(f"⏱️  {consumer_name} timeout (no messages)")
                continue

            except Exception as e:
                error_count += 1
                logger.error(
                    f"❌ {consumer_name} polling error ({error_count}/{max_errors}): {e}",
                    exc_info=True,
                )

                # Exponential backoff on repeated errors
                if error_count >= max_errors:
                    logger.critical(
                        f"🚨 {consumer_name} exceeded max errors ({max_errors}), "
                        f"backing off for {backoff_seconds}s"
                    )
                    await asyncio.sleep(backoff_seconds)
                    backoff_seconds = min(backoff_seconds * 2, 60)  # Max 60s
                    error_count = 0  # Reset after backoff
                else:
                    await asyncio.sleep(1)

    async def start(self) -> None:
        """Start consuming events.

        Must be implemented by subclasses to:
        1. Create pull subscription
        2. Start polling task
        """
        raise NotImplementedError("Subclasses must implement start()")

    async def _handle_message(self, msg) -> None:
        """Handle a single message.

        Must be implemented by subclasses.

        Args:
            msg: NATS message to process
        """
        raise NotImplementedError("Subclasses must implement _handle_message()")

    async def stop(self) -> None:
        """Stop consuming events."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

        logger.info(f"✓ {self.__class__.__name__} stopped")

