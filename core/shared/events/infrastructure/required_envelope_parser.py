"""Strict EventEnvelope parsing utilities.

This module enforces B0.1 hard requirements for MVP:
- No legacy fallback: inbound messages MUST be wrapped in EventEnvelope.
- Fail fast: missing/invalid envelopes are treated as permanent format errors.

Notes:
- Serialization/deserialization stays in infrastructure (mapper).
- Domain model (EventEnvelope) stays pure (no to_dict/from_dict).
"""

from typing import Any

from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure.event_envelope_mapper import EventEnvelopeMapper


def parse_required_envelope(data: object) -> EventEnvelope:
    """Parse an EventEnvelope from a decoded JSON object.

    Args:
        data: Decoded JSON value (expected dict[str, Any])

    Returns:
        Parsed EventEnvelope.

    Raises:
        ValueError: If data is not a dict or envelope is missing/invalid.
    """
    if not isinstance(data, dict):
        raise ValueError(f"EventEnvelope payload must be a dict, got {type(data)}")

    try:
        # Mapper performs KeyError on missing required keys and ValueError via EventEnvelope validation.
        return EventEnvelopeMapper.from_dict(data)
    except KeyError as exc:
        raise ValueError(f"Missing required EventEnvelope field: {exc}") from exc
    except ValueError:
        # Preserve validation error message from EventEnvelope.
        raise
    except Exception as exc:
        raise ValueError(f"Invalid EventEnvelope: {exc}") from exc

