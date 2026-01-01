"""Unit tests for event helpers."""

import hashlib
import uuid
from datetime import datetime

import pytest

from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.helpers import (
    create_event_envelope,
    generate_correlation_id,
    generate_idempotency_key,
)


def test_generate_idempotency_key_happy_path() -> None:
    """Test generate_idempotency_key with valid inputs."""
    key = generate_idempotency_key(
        event_type="story.created",
        entity_id="ST-123",
    )

    # Should be SHA-256 hex digest (64 characters)
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)


def test_generate_idempotency_key_is_deterministic() -> None:
    """Test generate_idempotency_key produces same key for same inputs."""
    key1 = generate_idempotency_key(
        event_type="story.created",
        entity_id="ST-123",
    )

    key2 = generate_idempotency_key(
        event_type="story.created",
        entity_id="ST-123",
    )

    assert key1 == key2


def test_generate_idempotency_key_with_operation() -> None:
    """Test generate_idempotency_key with operation qualifier."""
    key_without_op = generate_idempotency_key(
        event_type="story.transitioned",
        entity_id="ST-123",
    )

    key_with_op = generate_idempotency_key(
        event_type="story.transitioned",
        entity_id="ST-123",
        operation="approve",
    )

    # Keys should be different
    assert key_without_op != key_with_op


def test_generate_idempotency_key_with_timestamp() -> None:
    """Test generate_idempotency_key with timestamp."""
    key_without_ts = generate_idempotency_key(
        event_type="story.created",
        entity_id="ST-123",
    )

    key_with_ts = generate_idempotency_key(
        event_type="story.created",
        entity_id="ST-123",
        timestamp="2025-12-28T10:00:00Z",
    )

    # Keys should be different
    assert key_without_ts != key_with_ts


def test_generate_idempotency_key_different_entity_ids() -> None:
    """Test generate_idempotency_key produces different keys for different entities."""
    key1 = generate_idempotency_key(
        event_type="story.created",
        entity_id="ST-123",
    )

    key2 = generate_idempotency_key(
        event_type="story.created",
        entity_id="ST-456",
    )

    assert key1 != key2


def test_generate_idempotency_key_different_event_types() -> None:
    """Test generate_idempotency_key produces different keys for different event types."""
    key1 = generate_idempotency_key(
        event_type="story.created",
        entity_id="ST-123",
    )

    key2 = generate_idempotency_key(
        event_type="story.updated",
        entity_id="ST-123",
    )

    assert key1 != key2


def test_generate_idempotency_key_rejects_empty_event_type() -> None:
    """Test generate_idempotency_key rejects empty event_type."""
    with pytest.raises(ValueError, match="event_type cannot be empty"):
        generate_idempotency_key(
            event_type="",
            entity_id="ST-123",
        )


def test_generate_idempotency_key_rejects_empty_entity_id() -> None:
    """Test generate_idempotency_key rejects empty entity_id."""
    with pytest.raises(ValueError, match="entity_id cannot be empty"):
        generate_idempotency_key(
            event_type="story.created",
            entity_id="",
        )


def test_generate_idempotency_key_matches_expected_hash() -> None:
    """Test generate_idempotency_key produces expected SHA-256 hash."""
    key = generate_idempotency_key(
        event_type="story.created",
        entity_id="ST-123",
    )

    # Manually compute expected hash
    content = "story.created:ST-123"
    expected = hashlib.sha256(content.encode("utf-8")).hexdigest()

    assert key == expected


def test_generate_idempotency_key_with_all_components() -> None:
    """Test generate_idempotency_key with all components."""
    key = generate_idempotency_key(
        event_type="story.transitioned",
        entity_id="ST-123",
        operation="approve",
        timestamp="2025-12-28T10:00:00Z",
    )

    # Manually compute expected hash
    content = "story.transitioned:ST-123:approve:2025-12-28T10:00:00Z"
    expected = hashlib.sha256(content.encode("utf-8")).hexdigest()

    assert key == expected


def test_generate_correlation_id_returns_uuid() -> None:
    """Test generate_correlation_id returns valid UUID."""
    corr_id = generate_correlation_id()

    # Should be valid UUID v4
    parsed = uuid.UUID(corr_id)
    assert str(parsed) == corr_id
    assert parsed.version == 4


def test_generate_correlation_id_is_unique() -> None:
    """Test generate_correlation_id produces unique IDs."""
    corr_id1 = generate_correlation_id()
    corr_id2 = generate_correlation_id()

    assert corr_id1 != corr_id2


def test_create_event_envelope_happy_path() -> None:
    """Test create_event_envelope with minimal required parameters."""
    envelope = create_event_envelope(
        event_type="story.created",
        payload={"story_id": "ST-123", "title": "Test Story"},
        producer="planning-service",
        entity_id="ST-123",
    )

    assert isinstance(envelope, EventEnvelope)
    assert envelope.event_type == "story.created"
    assert envelope.payload == {"story_id": "ST-123", "title": "Test Story"}
    assert envelope.producer == "planning-service"
    assert len(envelope.idempotency_key) == 64  # SHA-256 hash
    assert len(envelope.correlation_id) == 36  # UUID v4
    assert envelope.causation_id is None
    assert envelope.metadata == {}


def test_create_event_envelope_with_operation() -> None:
    """Test create_event_envelope with operation qualifier."""
    envelope = create_event_envelope(
        event_type="story.transitioned",
        payload={"story_id": "ST-123"},
        producer="planning-service",
        entity_id="ST-123",
        operation="approve",
    )

    # Idempotency key should include operation
    expected_key = generate_idempotency_key(
        event_type="story.transitioned",
        entity_id="ST-123",
        operation="approve",
    )

    assert envelope.idempotency_key == expected_key


def test_create_event_envelope_with_correlation_id() -> None:
    """Test create_event_envelope with provided correlation_id."""
    envelope = create_event_envelope(
        event_type="story.created",
        payload={"story_id": "ST-123"},
        producer="planning-service",
        entity_id="ST-123",
        correlation_id="custom-corr-123",
    )

    assert envelope.correlation_id == "custom-corr-123"


def test_create_event_envelope_with_causation_id() -> None:
    """Test create_event_envelope with causation_id."""
    envelope = create_event_envelope(
        event_type="story.transitioned",
        payload={"story_id": "ST-123"},
        producer="planning-service",
        entity_id="ST-123",
        causation_id="cause-456",
    )

    assert envelope.causation_id == "cause-456"


def test_create_event_envelope_with_metadata() -> None:
    """Test create_event_envelope with metadata."""
    envelope = create_event_envelope(
        event_type="story.created",
        payload={"story_id": "ST-123"},
        producer="planning-service",
        entity_id="ST-123",
        metadata={"user": "tirso", "version": "v1"},
    )

    assert envelope.metadata == {"user": "tirso", "version": "v1"}


def test_create_event_envelope_timestamp_is_iso8601() -> None:
    """Test create_event_envelope generates ISO 8601 timestamp."""
    envelope = create_event_envelope(
        event_type="story.created",
        payload={"story_id": "ST-123"},
        producer="planning-service",
        entity_id="ST-123",
    )

    # Should be parseable as ISO 8601
    parsed = datetime.fromisoformat(envelope.timestamp.replace("Z", "+00:00"))
    assert isinstance(parsed, datetime)


def test_create_event_envelope_idempotency_key_is_deterministic() -> None:
    """Test create_event_envelope produces deterministic idempotency key."""
    envelope1 = create_event_envelope(
        event_type="story.created",
        payload={"story_id": "ST-123"},
        producer="planning-service",
        entity_id="ST-123",
    )

    envelope2 = create_event_envelope(
        event_type="story.created",
        payload={"story_id": "ST-123"},
        producer="planning-service",
        entity_id="ST-123",
    )

    # Idempotency keys should be same (deterministic)
    assert envelope1.idempotency_key == envelope2.idempotency_key

    # But correlation IDs should be different (unique)
    assert envelope1.correlation_id != envelope2.correlation_id


def test_create_event_envelope_validates_via_envelope() -> None:
    """Test create_event_envelope validates via EventEnvelope.__post_init__."""
    # Should raise if event_type is empty (validated by EventEnvelope)
    with pytest.raises(ValueError, match="event_type cannot be empty"):
        create_event_envelope(
            event_type="",
            payload={"data": "test"},
            producer="test-service",
            entity_id="test-123",
        )


def test_create_event_envelope_full_example() -> None:
    """Test create_event_envelope with all parameters."""
    envelope = create_event_envelope(
        event_type="story.transitioned",
        payload={"story_id": "ST-123", "from": "draft", "to": "ready"},
        producer="planning-service",
        entity_id="ST-123",
        operation="approve",
        correlation_id="corr-789",
        causation_id="cause-456",
        metadata={"user": "tirso", "version": "v2"},
    )

    assert envelope.event_type == "story.transitioned"
    assert envelope.payload == {"story_id": "ST-123", "from": "draft", "to": "ready"}
    assert envelope.producer == "planning-service"
    assert envelope.correlation_id == "corr-789"
    assert envelope.causation_id == "cause-456"
    assert envelope.metadata == {"user": "tirso", "version": "v2"}

    # Idempotency key should be deterministic based on inputs
    expected_key = generate_idempotency_key(
        event_type="story.transitioned",
        entity_id="ST-123",
        operation="approve",
    )
    assert envelope.idempotency_key == expected_key
