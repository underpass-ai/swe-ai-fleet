"""JetStream adapter implementation."""
import logging
from nats.js import JetStreamContext

from services.monitoring.domain.ports.jetstream_port import JetStreamPort

logger = logging.getLogger(__name__)


class JetStreamAdapter(JetStreamPort):
    """Concrete adapter for JetStream operations."""
    
    def __init__(self, js_context: JetStreamContext | None = None):
        """Initialize JetStream adapter.
        
        Args:
            js_context: JetStream context from NATS connection (optional)
        """
        self.js = js_context
    
    def set_context(self, js_context: JetStreamContext) -> None:
        """Set or update JetStream context.
        
        Args:
            js_context: JetStream context from NATS connection
        """
        self.js = js_context
        logger.info("JetStream context set")
    
    async def pull_subscribe(self, subject: str, stream: str, durable: str | None = None):
        """Create a pull subscribe consumer.
        
        Args:
            subject: Subject filter
            stream: Stream name
            durable: Optional durable consumer name
            
        Returns:
            Consumer subscription object
            
        Raises:
            RuntimeError: If JetStream context not set
        """
        if not self.js:
            raise RuntimeError("JetStream context not set. Call set_context() first.")
        
        return await self.js.pull_subscribe(subject, stream=stream, durable=durable)
    
    async def subscribe(self, subject: str, stream: str | None = None, ordered_consumer: bool = False):
        """Create a push subscribe consumer.
        
        Args:
            subject: Subject filter
            stream: Optional stream name
            ordered_consumer: Whether to use ordered consumer
            
        Returns:
            Consumer subscription object
            
        Raises:
            RuntimeError: If JetStream context not set
        """
        if not self.js:
            raise RuntimeError("JetStream context not set. Call set_context() first.")
        
        if ordered_consumer:
            return await self.js.subscribe(subject, stream=stream, ordered_consumer=ordered_consumer)
        elif stream:
            return await self.js.subscribe(subject, stream=stream)
        else:
            return await self.js.subscribe(subject)
