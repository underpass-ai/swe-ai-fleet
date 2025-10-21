"""NATS Pull Subscription adapter.

This adapter wraps NATS PullSubscription to implement PullSubscriptionPort,
abstracting NATS-specific subscription operations from domain handlers.

Following Hexagonal Architecture:
- Implements PullSubscriptionPort from domain/ports/
- Wraps NATS-specific subscription object
- Handlers depend on port, not NATS implementation
"""

from __future__ import annotations

import logging
from typing import Any

from services.orchestrator.domain.ports.pull_subscription_port import (
    MessagePort,
    PullSubscriptionPort,
)

logger = logging.getLogger(__name__)


class NATSMessageAdapter(MessagePort):
    """Adapter wrapping a NATS message.
    
    This adapter implements MessagePort by wrapping a NATS message object,
    providing a technology-agnostic interface for message handling.
    
    Attributes:
        _msg: Underlying NATS message
    """
    
    def __init__(self, nats_msg: Any):
        """Initialize adapter with NATS message.
        
        Args:
            nats_msg: NATS message object
        """
        self._msg = nats_msg
    
    @property
    def data(self) -> bytes:
        """Get message data as bytes."""
        return self._msg.data
    
    async def ack(self) -> None:
        """Acknowledge message processing."""
        await self._msg.ack()
    
    async def nak(self) -> None:
        """Negative acknowledge message."""
        await self._msg.nak()


class NATSPullSubscriptionAdapter(PullSubscriptionPort):
    """NATS implementation of PullSubscriptionPort.
    
    This adapter wraps a NATS pull subscription and provides the
    PullSubscriptionPort interface for fetching messages.
    
    Attributes:
        _subscription: Underlying NATS pull subscription
        _subject: Subject being subscribed to
    """
    
    def __init__(self, nats_subscription: Any, subject: str):
        """Initialize adapter with NATS subscription.
        
        Args:
            nats_subscription: NATS pull subscription object
            subject: Subject name (for logging)
        """
        self._subscription = nats_subscription
        self._subject = subject
    
    async def fetch(
        self,
        batch: int = 1,
        timeout: float = 5.0,
    ) -> list[MessagePort]:
        """Fetch messages from NATS subscription.
        
        Args:
            batch: Number of messages to fetch
            timeout: Timeout in seconds
            
        Returns:
            List of MessagePort wrappers around NATS messages
            
        Raises:
            TimeoutError: If no messages available within timeout
        """
        # Fetch from NATS (raises TimeoutError if none available)
        nats_messages = await self._subscription.fetch(
            batch=batch,
            timeout=timeout
        )
        
        # Wrap NATS messages in MessagePort adapters
        return [NATSMessageAdapter(msg) for msg in nats_messages]
    
    async def close(self) -> None:
        """Close the subscription.
        
        NATS pull subscriptions don't have explicit close,
        but we log for consistency.
        """
        logger.debug(f"✓ Pull subscription closed: {self._subject}")

