"""Idempotent consumer middleware for NATS message handlers.

Provides a decorator that wraps NATS message handlers with idempotency checks:
- Prevents re-execution of completed messages
- Handles concurrent processing (IN_PROGRESS)
- Detects and recovers from stale locks

Following Hexagonal Architecture:
- Middleware is in infrastructure layer
- Uses IdempotencyPort (application port)
- Wraps handler functions (infrastructure → application boundary)
"""

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from core.shared.events.infrastructure import parse_required_envelope
from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState

logger = logging.getLogger(__name__)


class _IdempotencyHandler:
    """Internal handler for idempotency logic.

    Extracted to reduce cognitive complexity of the decorator function.
    """

    def __init__(
        self,
        idempotency_port: IdempotencyPort,
        key_fn: Callable[[Any], str],
        in_progress_ttl_seconds: int,
        stale_max_age_seconds: int,
    ):
        """Initialize idempotency handler.

        Args:
            idempotency_port: Port for idempotency operations
            key_fn: Function to extract idempotency_key from message
            in_progress_ttl_seconds: TTL for IN_PROGRESS state
            stale_max_age_seconds: Max age before IN_PROGRESS is considered stale
        """
        self._port = idempotency_port
        self._key_fn = key_fn
        self._ttl_seconds = in_progress_ttl_seconds
        self._stale_max_age = stale_max_age_seconds

    def extract_key(self, msg: Any) -> str | None:
        """Extract idempotency key from message."""
        key = self._key_fn(msg)
        if not key:
            logger.warning(
                "No idempotency_key extracted from message, skipping idempotency check"
            )
        return key

    def handle_completed_state(self, idempotency_key: str) -> None:
        """Handle COMPLETED state: log and skip handler."""
        logger.info(
            f"Message already processed (COMPLETED), skipping handler: "
            f"idempotency_key={idempotency_key[:16]}..."
        )

    async def handle_in_progress_state(self, idempotency_key: str) -> bool:
        """Handle IN_PROGRESS state: check if stale and decide whether to skip.

        Returns:
            True if should skip handler, False if should retry (stale)
        """
        is_stale = await self._port.is_stale(idempotency_key, self._stale_max_age)

        if is_stale:
            logger.warning(
                f"IN_PROGRESS state is stale, clearing and retrying: "
                f"idempotency_key={idempotency_key[:16]}..."
            )
            return False  # Don't skip, allow retry

        logger.info(
            f"Message already IN_PROGRESS (not stale), skipping handler: "
            f"idempotency_key={idempotency_key[:16]}..."
        )
        return True  # Skip handler

    async def try_mark_in_progress(self, idempotency_key: str) -> bool:
        """Try to mark as IN_PROGRESS and handle race conditions.

        Returns:
            True if should continue with handler, False if should skip
        """
        marked = await self._port.mark_in_progress(idempotency_key, self._ttl_seconds)

        if not marked:
            # Race condition: re-check status
            final_state = await self._port.check_status(idempotency_key)
            if final_state == IdempotencyState.COMPLETED:
                logger.info(
                    f"Message became COMPLETED during race, skipping handler: "
                    f"idempotency_key={idempotency_key[:16]}..."
                )
            else:
                logger.info(
                    f"Failed to mark IN_PROGRESS (already processed), skipping handler: "
                    f"idempotency_key={idempotency_key[:16]}..."
                )
            return False  # Skip handler

        return True  # Continue with handler

    async def execute_with_completion(
        self, handler: Callable[[Any], Awaitable[None]], msg: Any, idempotency_key: str
    ) -> None:
        """Execute handler and mark as COMPLETED on success."""
        try:
            await handler(msg)
            await self._port.mark_completed(idempotency_key)
            logger.debug(
                f"Handler completed successfully, marked COMPLETED: "
                f"idempotency_key={idempotency_key[:16]}..."
            )
        except Exception as handler_error:
            logger.error(
                f"Handler failed, leaving IN_PROGRESS state (will expire or be detected as stale): "
                f"idempotency_key={idempotency_key[:16]}..., error={handler_error}",
                exc_info=True,
            )
            raise

    async def process_message(
        self, handler: Callable[[Any], Awaitable[None]], msg: Any
    ) -> None:
        """Process message with idempotency checks.

        Main orchestration method that handles the complete idempotency flow.

        Args:
            handler: Message handler function to execute
            msg: NATS message

        Raises:
            ValueError: If idempotency_key is missing or empty
            Exception: If handler execution fails (re-raised)
        """
        # Extract idempotency key
        idempotency_key = self.extract_key(msg)
        if not idempotency_key:
            raise ValueError(
                "idempotency_key is required. Message must contain a valid idempotency_key."
            )

        # Check current status
        current_state = await self._port.check_status(idempotency_key)

        # Handle COMPLETED state
        if current_state == IdempotencyState.COMPLETED:
            self.handle_completed_state(idempotency_key)
            return

        # Handle IN_PROGRESS state
        if current_state == IdempotencyState.IN_PROGRESS:
            should_skip = await self.handle_in_progress_state(idempotency_key)
            if should_skip:
                return

        # Try to mark as IN_PROGRESS
        should_continue = await self.try_mark_in_progress(idempotency_key)
        if not should_continue:
            return

        # Execute handler
        await self.execute_with_completion(handler, msg, idempotency_key)

    @staticmethod
    def is_handler_error(exception: Exception) -> bool:
        """Check if exception is from handler execution."""
        import traceback

        tb_str = traceback.format_exc()
        return "Handler failed" in tb_str or "await handler(msg)" in tb_str


class IdempotentConsumer:
    """Decorator class for idempotent NATS message handlers.

    Wraps a message handler function to provide persistent idempotency:
    - Extracts idempotency_key from message (via key_fn)
    - Checks if message was already processed (COMPLETED) → skip handler
    - Checks if message is IN_PROGRESS → skip handler (or handle stale)
    - Marks as IN_PROGRESS before handler execution
    - Marks as COMPLETED after successful handler execution

    Following Hexagonal Architecture:
    - This is a middleware component (infrastructure layer)
    - Uses IdempotencyPort (application port)
    - Can be injected as a dependency

    Example:
        ```python
        async def extract_key(msg) -> str:
            data = json.loads(msg.data.decode("utf-8"))
            envelope = parse_required_envelope(data)
            return envelope.idempotency_key

        idempotent_consumer = IdempotentConsumer(
            idempotency_port=idempotency_port,
            key_fn=extract_key,
        )

        @idempotent_consumer
        async def handle_message(msg):
            # Handler logic here
            pass
        ```
    """

    def __init__(
        self,
        idempotency_port: IdempotencyPort,
        key_fn: Callable[[Any], str],
        in_progress_ttl_seconds: int = 300,  # 5 minutes default
        stale_max_age_seconds: int = 600,  # 10 minutes default
    ):
        """Initialize idempotent consumer.

        Args:
            idempotency_port: Port for idempotency operations
            key_fn: Function to extract idempotency_key from message
                    Signature: (msg: Any) -> str
                    Should extract from EventEnvelope or message metadata
            in_progress_ttl_seconds: TTL for IN_PROGRESS state (default: 300s = 5min)
            stale_max_age_seconds: Max age before IN_PROGRESS is considered stale (default: 600s = 10min)

        Raises:
            ValueError: If ttl_seconds or stale_max_age_seconds are not positive
        """
        if in_progress_ttl_seconds <= 0:
            raise ValueError("in_progress_ttl_seconds must be positive")

        if stale_max_age_seconds <= 0:
            raise ValueError("stale_max_age_seconds must be positive")

        self._handler_logic = _IdempotencyHandler(
            idempotency_port=idempotency_port,
            key_fn=key_fn,
            in_progress_ttl_seconds=in_progress_ttl_seconds,
            stale_max_age_seconds=stale_max_age_seconds,
        )

    def __call__(
        self, handler: Callable[[Any], Awaitable[None]]
    ) -> Callable[[Any], Awaitable[None]]:
        """Wrap handler with idempotency checks.

        Args:
            handler: Message handler function to wrap

        Returns:
            Wrapped handler function with idempotency checks
        """
        @functools.wraps(handler)
        async def wrapped_handler(msg: Any) -> None:
            """Wrapped handler with idempotency gate."""
            try:
                await self._handler_logic.process_message(handler, msg)
            except ValueError as validation_error:
                # Validation errors (e.g., missing idempotency_key) should propagate
                if "idempotency_key is required" in str(validation_error):
                    raise
                # Other ValueError: treat as handler error
                logger.error(
                    f"Handler failed: {validation_error}",
                    exc_info=True,
                )
                raise
            except Exception as handler_error:
                # Check if this is a handler error (re-raise) or idempotency error (fallback)
                if _IdempotencyHandler.is_handler_error(handler_error):
                    # Log handler failure
                    logger.error(
                        f"Handler failed, leaving IN_PROGRESS state (will expire or be detected as stale): "
                        f"error={handler_error}",
                        exc_info=True,
                    )
                    raise

                # Idempotency error: fail-open fallback
                logger.error(
                    f"Idempotency check failed, proceeding without idempotency: {handler_error}",
                    exc_info=True,
                )
                await handler(msg)

        return wrapped_handler


# Backward compatibility: function wrapper for existing code
def idempotent_consumer(
    idempotency_port: IdempotencyPort,
    key_fn: Callable[[Any], str],
    in_progress_ttl_seconds: int = 300,  # 5 minutes default
    stale_max_age_seconds: int = 600,  # 10 minutes default
) -> Callable[[Callable[[Any], Awaitable[None]]], Callable[[Any], Awaitable[None]]]:
    """Function wrapper for backward compatibility.

    Creates an IdempotentConsumer instance and returns it as a decorator.

    Args:
        idempotency_port: Port for idempotency operations
        key_fn: Function to extract idempotency_key from message
        in_progress_ttl_seconds: TTL for IN_PROGRESS state (default: 300s = 5min)
        stale_max_age_seconds: Max age before IN_PROGRESS is considered stale (default: 600s = 10min)

    Returns:
        Decorator function that wraps the handler

    Note:
        Prefer using IdempotentConsumer class directly for dependency injection.
    """
    consumer = IdempotentConsumer(
        idempotency_port=idempotency_port,
        key_fn=key_fn,
        in_progress_ttl_seconds=in_progress_ttl_seconds,
        stale_max_age_seconds=stale_max_age_seconds,
    )
    return consumer


def extract_idempotency_key_from_envelope(msg: Any) -> str:
    """Extract idempotency_key from NATS message with EventEnvelope.

    Helper function for key_fn parameter of idempotent_consumer.

    Args:
        msg: NATS message object

    Returns:
        Idempotency key from EventEnvelope

    Raises:
        ValueError: If message doesn't contain valid EventEnvelope
    """
    import json

    data = json.loads(msg.data.decode("utf-8"))
    envelope = parse_required_envelope(data)
    return envelope.idempotency_key
