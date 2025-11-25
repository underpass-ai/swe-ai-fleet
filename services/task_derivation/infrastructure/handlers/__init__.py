"""NATS event handlers for Task Derivation Service.

Each handler is a standalone function that:
- Receives (payload, use_case)
- Returns void (handlers are fire-and-forget)
- Uses mappers for all payload conversions
- Follows single responsibility principle
- Zero business logic (delegated to use cases)
"""

from .derive_tasks_handler import derive_tasks_handler
from .process_result_handler import process_result_handler

__all__ = [
    "derive_tasks_handler",
    "process_result_handler",
]

