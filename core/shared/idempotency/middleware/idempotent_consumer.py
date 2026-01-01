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

import asyncio
import functools
import logging
from typing import Any, Awaitable, Callable

from core.shared.events.infrastructure import parse_required_envelope
from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState

logger = logging.getLogger(__name__)


def idempotent_consumer(
    idempotency_port: IdempotencyPort,
    key_fn: Callable[[Any], str],
    in_progress_ttl_seconds: int = 300,  # 5 minutes default
    stale_max_age_seconds: int = 600,  # 10 minutes default
) -> Callable[[Callable[[Any], Awaitable[None]]], Callable[[Any], Awaitable[None]]]:
    """Decorator for idempotent NATS message handlers.

    Wraps a message handler function to provide persistent idempotency:
    - Extracts idempotency_key from message (via key_fn)
    - Checks if message was already processed (COMPLETED) → skip handler
    - Checks if message is IN_PROGRESS → skip handler (or handle stale)
    - Marks as IN_PROGRESS before handler execution
    - Marks as COMPLETED after successful handler execution

    Args:
        idempotency_port: Port for idempotency operations
        key_fn: Function to extract idempotency_key from message
                Signature: (msg: Any) -> str
                Should extract from EventEnvelope or message metadata
        in_progress_ttl_seconds: TTL for IN_PROGRESS state (default: 300s = 5min)
        stale_max_age_seconds: Max age before IN_PROGRESS is considered stale (default: 600s = 10min)

    Returns:
        Decorator function that wraps the handler

    Example:
        ```python
        async def extract_key(msg) -> str:
            data = json.loads(msg.data.decode("utf-8"))
            envelope = parse_required_envelope(data)
            return envelope.idempotency_key

        @idempotent_consumer(
            idempotency_port=idempotency_port,
            key_fn=extract_key,
        )
        async def handle_message(msg):
            # Handler logic here
            pass
        ```
    """
    if in_progress_ttl_seconds <= 0:
        raise ValueError("in_progress_ttl_seconds must be positive")

    if stale_max_age_seconds <= 0:
        raise ValueError("stale_max_age_seconds must be positive")

    def decorator(
        handler: Callable[[Any], Awaitable[None]]
    ) -> Callable[[Any], Awaitable[None]]:
        """Wrap handler with idempotency checks."""

        @functools.wraps(handler)
        async def wrapped_handler(msg: Any) -> None:
            """Wrapped handler with idempotency gate."""
            try:
                # Extract idempotency key from message
                idempotency_key = key_fn(msg)

                if not idempotency_key:
                    logger.warning(
                        "No idempotency_key extracted from message, skipping idempotency check"
                    )
                    # Proceed without idempotency (legacy support)
                    await handler(msg)
                    return

                # Check current status
                current_state = await idempotency_port.check_status(idempotency_key)

                # Handle COMPLETED state: skip handler (already processed)
                if current_state == IdempotencyState.COMPLETED:
                    logger.info(
                        f"Message already processed (COMPLETED), skipping handler: "
                        f"idempotency_key={idempotency_key[:16]}..."
                    )
                    return  # Skip handler execution

                # Handle IN_PROGRESS state: check if stale
                if current_state == IdempotencyState.IN_PROGRESS:
                    is_stale = await idempotency_port.is_stale(
                        idempotency_key, stale_max_age_seconds
                    )

                    if is_stale:
                        logger.warning(
                            f"IN_PROGRESS state is stale, clearing and retrying: "
                            f"idempotency_key={idempotency_key[:16]}..."
                        )
                        # Stale state: delete key to allow retry (will be set by mark_in_progress below)
                        # Note: We rely on mark_in_progress to overwrite stale state
                    else:
                        logger.info(
                            f"Message already IN_PROGRESS (not stale), skipping handler: "
                            f"idempotency_key={idempotency_key[:16]}..."
                        )
                        return  # Skip handler execution (concurrent processing)

                # Try to mark as IN_PROGRESS (atomic operation)
                # If stale, this will overwrite the stale state
                marked = await idempotency_port.mark_in_progress(
                    idempotency_key, in_progress_ttl_seconds
                )

                if not marked:
                    # Another process already marked it (race condition or not stale)
                    # Re-check status to see if it's still IN_PROGRESS or became COMPLETED
                    final_state = await idempotency_port.check_status(idempotency_key)
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
                    return  # Skip handler execution

                # Execute handler
                try:
                    await handler(msg)

                    # Mark as COMPLETED after successful execution
                    await idempotency_port.mark_completed(idempotency_key)

                    logger.debug(
                        f"Handler completed successfully, marked COMPLETED: "
                        f"idempotency_key={idempotency_key[:16]}..."
                    )

                except Exception as handler_error:
                    # Handler failed: don't mark as COMPLETED
                    # IN_PROGRESS state will expire (TTL) or be detected as stale
                    logger.error(
                        f"Handler failed, leaving IN_PROGRESS state (will expire or be detected as stale): "
                        f"idempotency_key={idempotency_key[:16]}..., error={handler_error}",
                        exc_info=True,
                    )
                    # Re-raise handler error (don't fall into outer except)
                    raise

            except Exception as e:
                # Error in idempotency logic (not handler)
                # Check if this exception was re-raised from handler (has __cause__ or is ValueError/KeyError from handler)
                # If handler was already executed and failed, don't fallback (re-raise)
                import traceback
                tb_str = traceback.format_exc()
                if "Handler failed" in tb_str or "await handler(msg)" in tb_str:
                    # This is a handler error that was re-raised, don't fallback
                    raise

                logger.error(
                    f"Idempotency check failed, proceeding without idempotency: {e}",
                    exc_info=True,
                )
                # Fallback: execute handler without idempotency (fail-open)
                # Only if this is truly an idempotency error, not a handler error
                await handler(msg)

        return wrapped_handler

    return decorator


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
