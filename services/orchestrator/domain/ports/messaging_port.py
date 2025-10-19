"""Messaging port for event publishing and subscription.

This port abstracts the messaging infrastructure (NATS, Kafka, etc.)
from the domain logic, following the Dependency Inversion Principle.

Following Hexagonal Architecture:
- Domain defines the contract (port)
- Infrastructure provides the implementation (adapter)
- No NATS-specific details leak into domain
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class DomainEvent:
    """Base class for domain events.
    
    All events published through MessagingPort should extend this class.
    This ensures type safety and makes events discoverable.
    
    Attributes:
        event_type: Type of the event (e.g., "deliberation.completed")
        payload: Event data as dictionary
        correlation_id: Optional ID for tracing across services
    """
    
    def __init__(
        self,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ):
        """Initialize domain event.
        
        Args:
            event_type: Event type identifier
            payload: Event data
            correlation_id: Optional correlation ID for distributed tracing
        """
        self.event_type = event_type
        self.payload = payload
        self.correlation_id = correlation_id
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization.
        
        Returns:
            Dictionary representation of the event
        """
        result = {
            "event_type": self.event_type,
            **self.payload,
        }
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        return result


class MessagingPort(ABC):
    """Port defining the interface for messaging operations.
    
    This port abstracts message publishing and subscription,
    allowing the domain to remain independent of messaging technology.
    
    Following Hexagonal Architecture:
    - Port (this interface) is in domain/ports/
    - Adapter (NATS implementation) is in infrastructure/adapters/
    - Domain logic uses this port without knowing about NATS
    """
    
    @abstractmethod
    async def publish(self, subject: str, event: DomainEvent) -> None:
        """Publish a domain event to a subject.
        
        Args:
            subject: Message subject/topic (e.g., "deliberation.completed")
            event: Domain event to publish
            
        Raises:
            MessagingError: If publishing fails
        """
        pass
    
    @abstractmethod
    async def publish_dict(self, subject: str, data: dict[str, Any]) -> None:
        """Publish raw dictionary data to a subject.
        
        Legacy method for backwards compatibility.
        Prefer using publish() with DomainEvent.
        
        Args:
            subject: Message subject/topic
            data: Dictionary to publish
            
        Raises:
            MessagingError: If publishing fails
        """
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        subject: str,
        handler: Callable,
        queue_group: str | None = None,
        durable: str | None = None,
    ) -> None:
        """Subscribe to messages on a subject.
        
        Args:
            subject: Message subject/topic to subscribe to
            handler: Async callback to handle messages
            queue_group: Optional queue group for load balancing
            durable: Optional durable name for resumable subscriptions
            
        Raises:
            MessagingError: If subscription fails
        """
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the messaging system.
        
        Must be called before publish/subscribe operations.
        
        Raises:
            MessagingError: If connection fails
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the messaging connection.
        
        Should be called during graceful shutdown.
        """
        pass


class MessagingError(Exception):
    """Exception raised for messaging-related errors.
    
    This exception provides a domain-level abstraction over
    infrastructure-specific errors (e.g., NATS connection errors).
    """
    
    def __init__(self, message: str, cause: Exception | None = None):
        """Initialize messaging error.
        
        Args:
            message: Error message
            cause: Optional underlying exception
        """
        super().__init__(message)
        self.cause = cause

