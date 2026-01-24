"""Contract tests for EventEnvelope serialization.

These tests ensure that EventEnvelope serialization/deserialization
is consistent and maintains all required fields (idempotency_key,
correlation_id, causation_id, etc.).

Following contract testing principles:
- Test round-trip serialization (envelope → dict → envelope)
- Verify all required fields are preserved
- Verify optional fields are handled correctly
- Test edge cases (empty payload, None causation_id, etc.)
"""

import json
import pytest
from datetime import datetime, UTC

from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.helpers import create_event_envelope
from core.shared.events.infrastructure.event_envelope_mapper import (
    EventEnvelopeMapper,
)


def test_envelope_to_dict_round_trip() -> None:
    """Test that envelope → dict → envelope preserves all fields."""
    original = create_event_envelope(
        event_type="ceremony.sprint_planning.started",
        payload={"instance_id": "inst-123", "sprint_id": "sprint-1"},
        producer="ceremony-engine",
        entity_id="inst-123",
        operation="start",
        correlation_id="corr-123",
        causation_id="cause-456",
        metadata={"source": "api", "user": "admin"},
    )

    # Serialize to dict
    envelope_dict = EventEnvelopeMapper.to_dict(original)

    # Deserialize back to envelope
    restored = EventEnvelopeMapper.from_dict(envelope_dict)

    # Verify all fields match
    assert restored.event_type == original.event_type
    assert restored.payload == original.payload
    assert restored.idempotency_key == original.idempotency_key
    assert restored.correlation_id == original.correlation_id
    assert restored.timestamp == original.timestamp
    assert restored.producer == original.producer
    assert restored.causation_id == original.causation_id
    assert restored.metadata == original.metadata


def test_envelope_to_dict_required_fields() -> None:
    """Test that to_dict includes all required fields."""
    envelope = create_event_envelope(
        event_type="ceremony.test",
        payload={"test": "data"},
        producer="ceremony-engine",
        entity_id="test-123",
    )

    envelope_dict = EventEnvelopeMapper.to_dict(envelope)

    # Verify required fields are present
    assert "event_type" in envelope_dict
    assert "payload" in envelope_dict
    assert "idempotency_key" in envelope_dict
    assert "correlation_id" in envelope_dict
    assert "timestamp" in envelope_dict
    assert "producer" in envelope_dict
    assert "metadata" in envelope_dict


def test_envelope_to_dict_optional_causation_id() -> None:
    """Test that causation_id is optional in serialization."""
    # Envelope without causation_id
    envelope_no_cause = create_event_envelope(
        event_type="ceremony.test",
        payload={"test": "data"},
        producer="ceremony-engine",
        entity_id="test-123",
    )

    envelope_dict = EventEnvelopeMapper.to_dict(envelope_no_cause)

    # causation_id should not be in dict if None
    assert "causation_id" not in envelope_dict or envelope_dict.get("causation_id") is None

    # Envelope with causation_id
    envelope_with_cause = create_event_envelope(
        event_type="ceremony.test",
        payload={"test": "data"},
        producer="ceremony-engine",
        entity_id="test-123",
        causation_id="cause-123",
    )

    envelope_dict = EventEnvelopeMapper.to_dict(envelope_with_cause)

    # causation_id should be in dict if present
    assert envelope_dict["causation_id"] == "cause-123"


def test_envelope_from_dict_required_fields() -> None:
    """Test that from_dict requires all required fields."""
    # Missing event_type
    with pytest.raises((KeyError, ValueError)):
        EventEnvelopeMapper.from_dict({
            "payload": {},
            "idempotency_key": "key",
            "correlation_id": "corr",
            "timestamp": datetime.now(UTC).isoformat(),
            "producer": "test",
        })

    # Missing idempotency_key
    with pytest.raises((KeyError, ValueError)):
        EventEnvelopeMapper.from_dict({
            "event_type": "test",
            "payload": {},
            "correlation_id": "corr",
            "timestamp": datetime.now(UTC).isoformat(),
            "producer": "test",
        })


def test_envelope_json_serialization() -> None:
    """Test that envelope can be serialized to JSON."""
    envelope = create_event_envelope(
        event_type="ceremony.sprint_planning.started",
        payload={"instance_id": "inst-123"},
        producer="ceremony-engine",
        entity_id="inst-123",
    )

    # Serialize to dict
    envelope_dict = EventEnvelopeMapper.to_dict(envelope)

    # Serialize to JSON
    json_str = json.dumps(envelope_dict)

    # Deserialize from JSON
    restored_dict = json.loads(json_str)

    # Deserialize to envelope
    restored = EventEnvelopeMapper.from_dict(restored_dict)

    # Verify fields match
    assert restored.event_type == envelope.event_type
    assert restored.payload == envelope.payload
    assert restored.idempotency_key == envelope.idempotency_key
    assert restored.correlation_id == envelope.correlation_id


def test_envelope_idempotency_key_present() -> None:
    """Test that all envelopes have idempotency_key (required for E0.3 AC)."""
    envelope = create_event_envelope(
        event_type="ceremony.test",
        payload={"test": "data"},
        producer="ceremony-engine",
        entity_id="test-123",
    )

    assert envelope.idempotency_key
    assert len(envelope.idempotency_key) > 0

    envelope_dict = EventEnvelopeMapper.to_dict(envelope)
    assert "idempotency_key" in envelope_dict
    assert envelope_dict["idempotency_key"] == envelope.idempotency_key


def test_envelope_correlation_id_present() -> None:
    """Test that all envelopes have correlation_id (required for E0.3 AC)."""
    envelope = create_event_envelope(
        event_type="ceremony.test",
        payload={"test": "data"},
        producer="ceremony-engine",
        entity_id="test-123",
    )

    assert envelope.correlation_id
    assert len(envelope.correlation_id) > 0

    envelope_dict = EventEnvelopeMapper.to_dict(envelope)
    assert "correlation_id" in envelope_dict
    assert envelope_dict["correlation_id"] == envelope.correlation_id


def test_envelope_causation_id_optional() -> None:
    """Test that causation_id is optional but preserved when present."""
    # Without causation_id
    envelope_no_cause = create_event_envelope(
        event_type="ceremony.test",
        payload={"test": "data"},
        producer="ceremony-engine",
        entity_id="test-123",
    )

    assert envelope_no_cause.causation_id is None

    # With causation_id
    envelope_with_cause = create_event_envelope(
        event_type="ceremony.test",
        payload={"test": "data"},
        producer="ceremony-engine",
        entity_id="test-123",
        causation_id="parent-event-123",
    )

    assert envelope_with_cause.causation_id == "parent-event-123"

    # Round-trip preserves causation_id
    envelope_dict = EventEnvelopeMapper.to_dict(envelope_with_cause)
    restored = EventEnvelopeMapper.from_dict(envelope_dict)
    assert restored.causation_id == "parent-event-123"


def test_envelope_deterministic_idempotency_key() -> None:
    """Test that idempotency_key is deterministic for same inputs."""
    from core.shared.events.helpers import generate_idempotency_key

    key1 = generate_idempotency_key(
        event_type="ceremony.test",
        entity_id="inst-123",
        operation="start",
    )

    key2 = generate_idempotency_key(
        event_type="ceremony.test",
        entity_id="inst-123",
        operation="start",
    )

    # Same inputs should produce same key
    assert key1 == key2

    # Different operation should produce different key
    key3 = generate_idempotency_key(
        event_type="ceremony.test",
        entity_id="inst-123",
        operation="complete",
    )

    assert key1 != key3
