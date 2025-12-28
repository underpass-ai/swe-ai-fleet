"""Helper functions for event envelope creation and idempotency.

Provides:
- generate_idempotency_key: Create deterministic idempotency keys
- generate_correlation_id: Create unique correlation IDs for tracing
- create_event_envelope: Convenience function to create envelopes
"""

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from core.shared.events.event_envelope import EventEnvelope


def generate_idempotency_key(
    event_type: str,
    entity_id: str,
    operation: str | None = None,
    timestamp: str | None = None,
) -> str:
    """Generate deterministic idempotency key for event deduplication.

    The idempotency key is a SHA-256 hash of:
    - event_type: Type of event (e.g., "story.created")
    - entity_id: Entity identifier (e.g., story ID, ceremony ID)
    - operation: Optional operation qualifier (e.g., "approve", "reject")
    - timestamp: Optional timestamp for time-based uniqueness

    Args:
        event_type: Event type (e.g., "story.created")
        entity_id: Entity identifier (e.g., "ST-123")
        operation: Optional operation qualifier
        timestamp: Optional ISO 8601 timestamp

    Returns:
        Deterministic idempotency key (SHA-256 hex digest)

    Raises:
        ValueError: If required parameters are empty
    """
    if not event_type:
        raise ValueError("event_type cannot be empty")

    if not entity_id:
        raise ValueError("entity_id cannot be empty")

    # Build components for hash
    components = [event_type, entity_id]

    if operation:
        components.append(operation)

    if timestamp:
        components.append(timestamp)

    # Create deterministic hash
    content = ":".join(components)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_correlation_id() -> str:
    """Generate unique correlation ID for distributed tracing.

    Returns:
        UUID v4 as correlation ID
    """
    return str(uuid.uuid4())


def create_event_envelope(
    event_type: str,
    payload: dict[str, Any],
    producer: str,
    entity_id: str,
    operation: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> EventEnvelope:
    """Create event envelope with auto-generated idempotency key.

    Convenience function that:
    - Generates idempotency_key from event_type + entity_id + operation
    - Generates correlation_id if not provided
    - Sets timestamp to current UTC time
    - Wraps payload in EventEnvelope

    Args:
        event_type: Event type (e.g., "story.created")
        payload: Event payload data
        producer: Service producing this event (e.g., "planning-service")
        entity_id: Entity identifier for idempotency key
        operation: Optional operation qualifier for idempotency key
        correlation_id: Optional correlation ID (generated if not provided)
        causation_id: Optional causation ID (for event chains)
        metadata: Optional metadata dict

    Returns:
        EventEnvelope instance

    Raises:
        ValueError: If required parameters are invalid
    """
    # Generate timestamp
    timestamp = datetime.now(UTC).isoformat()

    # Generate idempotency key (deterministic)
    idempotency_key = generate_idempotency_key(
        event_type=event_type,
        entity_id=entity_id,
        operation=operation,
        timestamp=None,  # Don't include timestamp for deterministic key
    )

    # Generate correlation ID if not provided
    if not correlation_id:
        correlation_id = generate_correlation_id()

    return EventEnvelope(
        event_type=event_type,
        payload=payload,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        timestamp=timestamp,
        producer=producer,
        causation_id=causation_id,
        metadata=metadata or {},
    )
