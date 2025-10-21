"""Pull subscription port for message consumption.

This port abstracts pull-based message consumption, allowing handlers to
fetch messages without depending on NATS-specific subscription objects.

Following Hexagonal Architecture:
- Domain defines the contract (port)
- Infrastructure provides the implementation (adapter)
- Handlers use this port without knowing about NATS PullSubscription
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PullSubscriptionPort(ABC):
    """Port defining the interface for pull-based message consumption.
    
    Pull subscriptions allow consumers to fetch messages on demand,
    which is ideal for load balancing across multiple pods in Kubernetes.
    
    Following Hexagonal Architecture:
    - Port (this interface) is in domain/ports/
    - Adapter (NATS PullSubscription wrapper) is in infrastructure/adapters/
    - Handlers use this port without NATS dependencies
    """
    
    @abstractmethod
    async def fetch(
        self,
        batch: int = 1,
        timeout: float = 5.0,
    ) -> list[Any]:
        """Fetch messages from the subscription.
        
        This is a pull-based consumption model where the consumer explicitly
        requests messages, rather than having them pushed.
        
        Args:
            batch: Number of messages to fetch
            timeout: Timeout in seconds to wait for messages
            
        Returns:
            List of messages (max `batch` messages)
            
        Raises:
            TimeoutError: If no messages available within timeout
            MessagingError: If fetch operation fails
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the subscription and release resources.
        
        This should be called during graceful shutdown to ensure
        proper cleanup of subscription resources.
        """
        pass


class MessagePort(ABC):
    """Port defining the interface for individual messages.
    
    This abstracts message acknowledgment and access to message data,
    allowing handlers to process messages without NATS-specific details.
    """
    
    @property
    @abstractmethod
    def data(self) -> bytes:
        """Get message data as bytes.
        
        Returns:
            Raw message data
        """
        pass
    
    @abstractmethod
    async def ack(self) -> None:
        """Acknowledge successful message processing.
        
        This tells the messaging system that the message was processed
        successfully and should not be redelivered.
        """
        pass
    
    @abstractmethod
    async def nak(self) -> None:
        """Negative acknowledge (reject) message processing.
        
        This tells the messaging system that the message was not processed
        successfully and should be redelivered later.
        """
        pass

