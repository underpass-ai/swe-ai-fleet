"""EventEnvelope: Standard wrapper for all domain events.

This envelope provides:
- idempotency_key: For deduplication (REQUIRED for create/update events)
- correlation_id: For distributed tracing across services
- causation_id: For tracking event causality chains
- event_type: Semantic event type (e.g., "story.created")
- timestamp: ISO 8601 timestamp
- producer: Service that produced this event
- payload: Actual event data
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class EventEnvelope:
    """
    Standard envelope for all domain events.

    Immutable wrapper that provides:
    - Idempotency (via idempotency_key)
    - Correlation (via correlation_id)
    - Causation tracking (via causation_id)
    - Event metadata (type, timestamp, producer)

    Following DDD + Hexagonal Architecture:
    - Domain layer defines the envelope structure
    - Infrastructure layer (publishers/consumers) use this envelope
    - All side-effect events MUST include idempotency_key
    """

    event_type: str
    payload: dict[str, Any]
    idempotency_key: str
    correlation_id: str
    timestamp: str
    producer: str
    causation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate envelope fields (fail-fast).

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if not self.event_type:
            raise ValueError("event_type cannot be empty")

        if not self.idempotency_key:
            raise ValueError("idempotency_key cannot be empty (required for idempotency)")

        if not self.correlation_id:
            raise ValueError("correlation_id cannot be empty (required for tracing)")

        if not self.timestamp:
            raise ValueError("timestamp cannot be empty")

        if not self.producer:
            raise ValueError("producer cannot be empty")

        if not isinstance(self.payload, dict):
            raise ValueError("payload must be a dict")

        # Validate timestamp format (ISO 8601)
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid timestamp format (expected ISO 8601): {self.timestamp}") from e

    def to_dict(self) -> dict[str, Any]:
        """Convert envelope to dict for serialization.

        Returns:
            Dict representation suitable for JSON serialization
        """
        result: dict[str, Any] = {
            "event_type": self.event_type,
            "payload": self.payload,
            "idempotency_key": self.idempotency_key,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "producer": self.producer,
            "metadata": self.metadata,
        }

        if self.causation_id:
            result["causation_id"] = self.causation_id

        return result

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "EventEnvelope":
        """Create envelope from dict (deserialization).

        Args:
            data: Dict representation of envelope

        Returns:
            EventEnvelope instance

        Raises:
            ValueError: If required fields are missing
            KeyError: If required keys are missing
        """
        return EventEnvelope(
            event_type=data["event_type"],
            payload=data["payload"],
            idempotency_key=data["idempotency_key"],
            correlation_id=data["correlation_id"],
            timestamp=data["timestamp"],
            producer=data["producer"],
            causation_id=data.get("causation_id"),
            metadata=data.get("metadata", {}),
        )
