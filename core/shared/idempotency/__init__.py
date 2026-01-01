"""Idempotency port and adapters for persistent message deduplication.

This module provides:
- IdempotencyPort: Protocol for idempotency gate operations
- ValkeyIdempotencyAdapter: Valkey (Redis-compatible) implementation
- idempotent_consumer: Decorator/middleware for NATS consumers

All consumers should use idempotency to ensure:
- Redelivery of completed messages does not re-execute handlers
- Duplicate messages during IN_PROGRESS do not cause duplicate side-effects
- Persistent deduplication survives pod restarts
"""

from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState
from core.shared.idempotency.infrastructure.valkey_idempotency_adapter import (
    ValkeyIdempotencyAdapter,
)
from core.shared.idempotency.middleware.idempotent_consumer import (
    idempotent_consumer,
)

__all__ = [
    "IdempotencyPort",
    "IdempotencyState",
    "ValkeyIdempotencyAdapter",
    "idempotent_consumer",
]
