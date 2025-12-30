"""Infrastructure layer for event envelope serialization.

This module contains mappers for converting EventEnvelope to/from external formats (dict/JSON).
Following Hexagonal Architecture: serialization logic lives in infrastructure, not domain.
"""

from core.shared.events.infrastructure.event_envelope_mapper import (
    EventEnvelopeMapper,
)
from core.shared.events.infrastructure.required_envelope_parser import (
    parse_required_envelope,
)

__all__ = ["EventEnvelopeMapper", "parse_required_envelope"]
