"""Mapper for EventEnvelope serialization/deserialization.

Following Hexagonal Architecture:
- Domain layer (EventEnvelope) is pure and immutable
- Infrastructure layer (this mapper) handles dict/JSON conversion
- Mappers are explicit and typed (no reflection)
"""

from typing import Any

from core.shared.events.event_envelope import EventEnvelope


class EventEnvelopeMapper:
    """Mapper for converting EventEnvelope to/from dict (JSON serialization).

    Responsibilities:
    - Convert EventEnvelope → dict (for JSON serialization)
    - Convert dict → EventEnvelope (for JSON deserialization)
    - Handle optional fields (causation_id, metadata)

    Following repository rules:
    - No serialization methods in domain/DTOs
    - Explicit mappers in infrastructure layer
    - Fail-fast validation
    """

    @staticmethod
    def to_dict(envelope: EventEnvelope) -> dict[str, Any]:
        """Convert EventEnvelope to dict for JSON serialization.

        Args:
            envelope: EventEnvelope instance

        Returns:
            Dict representation suitable for JSON serialization

        Raises:
            ValueError: If envelope is invalid (should not happen if envelope passed validation)
        """
        result: dict[str, Any] = {
            "event_type": envelope.event_type,
            "payload": envelope.payload,
            "idempotency_key": envelope.idempotency_key,
            "correlation_id": envelope.correlation_id,
            "timestamp": envelope.timestamp,
            "producer": envelope.producer,
            "metadata": envelope.metadata,
        }

        # Only include causation_id if present (optional field)
        if envelope.causation_id:
            result["causation_id"] = envelope.causation_id

        return result

    @staticmethod
    def from_dict(data: dict[str, Any]) -> EventEnvelope:
        """Create EventEnvelope from dict (JSON deserialization).

        Args:
            data: Dict representation of envelope (from JSON)

        Returns:
            EventEnvelope instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If envelope validation fails (from __post_init__)
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
