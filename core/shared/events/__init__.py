"""Event envelope and helpers for idempotent event processing.

This module provides:
- EventEnvelope: Standard wrapper for all domain events
- Idempotency key generation helpers
- Correlation/causation tracking

All publishers/consumers should use EventEnvelope to ensure:
- Deduplication (via idempotency_key)
- Distributed tracing (via correlation_id)
- Event causality tracking (via causation_id)
"""

from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.helpers import (
    create_event_envelope,
    generate_correlation_id,
    generate_idempotency_key,
)

__all__ = [
    "EventEnvelope",
    "generate_idempotency_key",
    "generate_correlation_id",
    "create_event_envelope",
]
