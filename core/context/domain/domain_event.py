# core/context/domain/domain_event.py
from __future__ import annotations

from dataclasses import dataclass

from .event_type import EventType


@dataclass(frozen=True)
class DomainEvent:
    """Base domain event representing something that happened in the system.

    Domain events are immutable representations of business events that have occurred.

    This is an abstract base class. Use specific event classes (StoryCreatedEvent, etc.)
    for type-safe event handling.

    Each specific event class lives in its own file for maximum cohesion.
    """

    event_type: EventType
