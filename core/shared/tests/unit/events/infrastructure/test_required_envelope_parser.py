"""Unit tests for strict EventEnvelope parsing."""

import pytest

from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper, parse_required_envelope


def test_parse_required_envelope_happy_path() -> None:
    envelope = EventEnvelope(
        event_type="test.event",
        payload={"x": 1},
        idempotency_key="idemp-123",
        correlation_id="corr-456",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="test-service",
    )

    parsed = parse_required_envelope(EventEnvelopeMapper.to_dict(envelope))

    assert parsed.event_type == "test.event"
    assert parsed.payload == {"x": 1}
    assert parsed.idempotency_key == "idemp-123"
    assert parsed.correlation_id == "corr-456"


def test_parse_required_envelope_rejects_non_dict() -> None:
    with pytest.raises(ValueError, match="must be a dict"):
        parse_required_envelope(["not", "a", "dict"])  # type: ignore[arg-type]


def test_parse_required_envelope_rejects_missing_required_fields() -> None:
    with pytest.raises(ValueError, match="Missing required EventEnvelope field"):
        parse_required_envelope({"event_type": "x"})

