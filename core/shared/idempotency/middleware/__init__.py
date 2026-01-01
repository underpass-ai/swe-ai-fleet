"""Middleware for idempotent NATS message consumption."""

from core.shared.idempotency.middleware.idempotent_consumer import (
    idempotent_consumer,
)

__all__ = [
    "idempotent_consumer",
]
