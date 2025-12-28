"""Unit tests for EventEnvelope."""


import pytest

from core.shared.events.event_envelope import EventEnvelope


def test_event_envelope_happy_path() -> None:
    """Test EventEnvelope creation with valid data."""
    envelope = EventEnvelope(
        event_type="story.created",
        payload={"story_id": "ST-123", "title": "Test Story"},
        idempotency_key="abc123",
        correlation_id="corr-456",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="planning-service",
    )

    assert envelope.event_type == "story.created"
    assert envelope.payload == {"story_id": "ST-123", "title": "Test Story"}
    assert envelope.idempotency_key == "abc123"
    assert envelope.correlation_id == "corr-456"
    assert envelope.timestamp == "2025-12-28T10:00:00+00:00"
    assert envelope.producer == "planning-service"
    assert envelope.causation_id is None
    assert envelope.metadata == {}


def test_event_envelope_with_causation_and_metadata() -> None:
    """Test EventEnvelope with optional causation_id and metadata."""
    envelope = EventEnvelope(
        event_type="story.transitioned",
        payload={"story_id": "ST-123", "from": "draft", "to": "ready"},
        idempotency_key="def456",
        correlation_id="corr-789",
        timestamp="2025-12-28T11:00:00+00:00",
        producer="planning-service",
        causation_id="cause-123",
        metadata={"user": "tirso", "version": "v1"},
    )

    assert envelope.causation_id == "cause-123"
    assert envelope.metadata == {"user": "tirso", "version": "v1"}


def test_event_envelope_rejects_empty_event_type() -> None:
    """Test EventEnvelope rejects empty event_type."""
    with pytest.raises(ValueError, match="event_type cannot be empty"):
        EventEnvelope(
            event_type="",
            payload={"data": "test"},
            idempotency_key="key123",
            correlation_id="corr123",
            timestamp="2025-12-28T10:00:00+00:00",
            producer="test-service",
        )


def test_event_envelope_rejects_empty_idempotency_key() -> None:
    """Test EventEnvelope rejects empty idempotency_key."""
    with pytest.raises(ValueError, match="idempotency_key cannot be empty"):
        EventEnvelope(
            event_type="test.event",
            payload={"data": "test"},
            idempotency_key="",
            correlation_id="corr123",
            timestamp="2025-12-28T10:00:00+00:00",
            producer="test-service",
        )


def test_event_envelope_rejects_empty_correlation_id() -> None:
    """Test EventEnvelope rejects empty correlation_id."""
    with pytest.raises(ValueError, match="correlation_id cannot be empty"):
        EventEnvelope(
            event_type="test.event",
            payload={"data": "test"},
            idempotency_key="key123",
            correlation_id="",
            timestamp="2025-12-28T10:00:00+00:00",
            producer="test-service",
        )


def test_event_envelope_rejects_empty_timestamp() -> None:
    """Test EventEnvelope rejects empty timestamp."""
    with pytest.raises(ValueError, match="timestamp cannot be empty"):
        EventEnvelope(
            event_type="test.event",
            payload={"data": "test"},
            idempotency_key="key123",
            correlation_id="corr123",
            timestamp="",
            producer="test-service",
        )


def test_event_envelope_rejects_empty_producer() -> None:
    """Test EventEnvelope rejects empty producer."""
    with pytest.raises(ValueError, match="producer cannot be empty"):
        EventEnvelope(
            event_type="test.event",
            payload={"data": "test"},
            idempotency_key="key123",
            correlation_id="corr123",
            timestamp="2025-12-28T10:00:00+00:00",
            producer="",
        )


def test_event_envelope_rejects_non_dict_payload() -> None:
    """Test EventEnvelope rejects non-dict payload."""
    with pytest.raises(ValueError, match="payload must be a dict"):
        EventEnvelope(
            event_type="test.event",
            payload="not a dict",  # type: ignore
            idempotency_key="key123",
            correlation_id="corr123",
            timestamp="2025-12-28T10:00:00+00:00",
            producer="test-service",
        )


def test_event_envelope_rejects_invalid_timestamp_format() -> None:
    """Test EventEnvelope rejects invalid timestamp format."""
    with pytest.raises(ValueError, match="Invalid timestamp format"):
        EventEnvelope(
            event_type="test.event",
            payload={"data": "test"},
            idempotency_key="key123",
            correlation_id="corr123",
            timestamp="not-a-timestamp",
            producer="test-service",
        )


def test_event_envelope_to_dict_without_causation() -> None:
    """Test EventEnvelope.to_dict() without causation_id."""
    envelope = EventEnvelope(
        event_type="story.created",
        payload={"story_id": "ST-123"},
        idempotency_key="key123",
        correlation_id="corr456",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="planning-service",
    )

    result = envelope.to_dict()

    assert result == {
        "event_type": "story.created",
        "payload": {"story_id": "ST-123"},
        "idempotency_key": "key123",
        "correlation_id": "corr456",
        "timestamp": "2025-12-28T10:00:00+00:00",
        "producer": "planning-service",
        "metadata": {},
    }
    assert "causation_id" not in result


def test_event_envelope_to_dict_with_causation() -> None:
    """Test EventEnvelope.to_dict() with causation_id."""
    envelope = EventEnvelope(
        event_type="story.transitioned",
        payload={"story_id": "ST-123"},
        idempotency_key="key123",
        correlation_id="corr456",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="planning-service",
        causation_id="cause-789",
        metadata={"user": "tirso"},
    )

    result = envelope.to_dict()

    assert result["causation_id"] == "cause-789"
    assert result["metadata"] == {"user": "tirso"}


def test_event_envelope_from_dict_without_causation() -> None:
    """Test EventEnvelope.from_dict() without causation_id."""
    data = {
        "event_type": "story.created",
        "payload": {"story_id": "ST-123"},
        "idempotency_key": "key123",
        "correlation_id": "corr456",
        "timestamp": "2025-12-28T10:00:00+00:00",
        "producer": "planning-service",
    }

    envelope = EventEnvelope.from_dict(data)

    assert envelope.event_type == "story.created"
    assert envelope.payload == {"story_id": "ST-123"}
    assert envelope.idempotency_key == "key123"
    assert envelope.correlation_id == "corr456"
    assert envelope.timestamp == "2025-12-28T10:00:00+00:00"
    assert envelope.producer == "planning-service"
    assert envelope.causation_id is None
    assert envelope.metadata == {}


def test_event_envelope_from_dict_with_causation() -> None:
    """Test EventEnvelope.from_dict() with causation_id."""
    data = {
        "event_type": "story.transitioned",
        "payload": {"story_id": "ST-123"},
        "idempotency_key": "key123",
        "correlation_id": "corr456",
        "timestamp": "2025-12-28T10:00:00+00:00",
        "producer": "planning-service",
        "causation_id": "cause-789",
        "metadata": {"user": "tirso"},
    }

    envelope = EventEnvelope.from_dict(data)

    assert envelope.causation_id == "cause-789"
    assert envelope.metadata == {"user": "tirso"}


def test_event_envelope_from_dict_missing_required_field() -> None:
    """Test EventEnvelope.from_dict() raises on missing required field."""
    data = {
        "event_type": "story.created",
        "payload": {"story_id": "ST-123"},
        # Missing idempotency_key
        "correlation_id": "corr456",
        "timestamp": "2025-12-28T10:00:00+00:00",
        "producer": "planning-service",
    }

    with pytest.raises(KeyError):
        EventEnvelope.from_dict(data)


def test_event_envelope_immutability() -> None:
    """Test EventEnvelope is immutable (frozen dataclass)."""
    envelope = EventEnvelope(
        event_type="story.created",
        payload={"story_id": "ST-123"},
        idempotency_key="key123",
        correlation_id="corr456",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="planning-service",
    )

    with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError
        envelope.event_type = "modified"  # type: ignore


def test_event_envelope_accepts_iso8601_with_z_suffix() -> None:
    """Test EventEnvelope accepts ISO 8601 timestamp with Z suffix."""
    envelope = EventEnvelope(
        event_type="test.event",
        payload={"data": "test"},
        idempotency_key="key123",
        correlation_id="corr123",
        timestamp="2025-12-28T10:00:00Z",  # Z suffix
        producer="test-service",
    )

    assert envelope.timestamp == "2025-12-28T10:00:00Z"


def test_event_envelope_roundtrip_serialization() -> None:
    """Test EventEnvelope roundtrip: to_dict() -> from_dict()."""
    original = EventEnvelope(
        event_type="story.created",
        payload={"story_id": "ST-123", "title": "Test"},
        idempotency_key="key123",
        correlation_id="corr456",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="planning-service",
        causation_id="cause-789",
        metadata={"user": "tirso", "version": "v1"},
    )

    # Serialize
    data = original.to_dict()

    # Deserialize
    restored = EventEnvelope.from_dict(data)

    # Verify equality
    assert restored.event_type == original.event_type
    assert restored.payload == original.payload
    assert restored.idempotency_key == original.idempotency_key
    assert restored.correlation_id == original.correlation_id
    assert restored.timestamp == original.timestamp
    assert restored.producer == original.producer
    assert restored.causation_id == original.causation_id
    assert restored.metadata == original.metadata
