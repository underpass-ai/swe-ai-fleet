"""Base domain event entity.

This module defines the base concept of a Domain Event following DDD principles.
All events in the orchestrator domain should inherit from or implement this protocol.

Following Domain-Driven Design:
- Events represent facts that have happened in the domain
- Events are immutable (what happened cannot change)
- Events have a clear semantic meaning
- Events can be serialized for messaging
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DomainEvent(ABC):
    """Base class for all domain events.
    
    Domain events represent facts that have occurred in the orchestration domain.
    They are immutable and carry all necessary information about what happened.
    
    Following DDD and Event-Driven Architecture principles:
    - Events are facts (past tense: PhaseChanged, TaskCompleted)
    - Events are immutable (frozen dataclasses)
    - Events carry sufficient data for consumers to react
    - Events can be serialized for messaging infrastructure
    
    All concrete event classes should:
    1. Inherit from this class
    2. Be frozen dataclasses (immutable)
    3. Implement to_dict() for serialization
    4. Have an event_type property
    """
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Get the event type identifier.
        
        This should be a unique string identifying the event type,
        typically in dot notation (e.g., "orchestration.task.completed").
        
        Returns:
            Event type string
        """
        pass
    
    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization.
        
        The dictionary should include:
        - event_type: The event type identifier
        - All event data fields
        - Any metadata (timestamp, correlation_id, etc.)
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        pass

