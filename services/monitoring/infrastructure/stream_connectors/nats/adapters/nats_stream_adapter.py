"""NATS JetStream-specific stream adapter."""
import logging

from nats.js import JetStreamContext
from services.monitoring.domain.ports.stream import StreamPort

logger = logging.getLogger(__name__)


class NATSStreamAdapter(StreamPort):
    """NATS JetStream implementation of StreamPort."""
    
    def __init__(self, js_context: JetStreamContext | None = None):
        """Initialize NATS stream adapter.
        
        Args:
            js_context: JetStream context from NATS connection (optional)
        """
        self.js = js_context
    
    def set_context(self, js_context: JetStreamContext) -> None:
        """Set JetStream context.
        
        Args:
            js_context: JetStream context from NATS connection
        """
        self.js = js_context
        logger.info("JetStream context set")
    
    async def create_durable_consumer(
        self,
        subject_filter: str,
        stream_name: str,
        durable_name: str
    ):
        """Create a durable consumer.
        
        Args:
            subject_filter: Subject filter pattern
            stream_name: Stream name
            durable_name: Durable consumer name
            
        Returns:
            NATS Consumer subscription object
            
        Raises:
            RuntimeError: If JetStream context not set
        """
        if not self.js:
            raise RuntimeError("JetStream context not set. Call set_context() first.")
        
        return await self.js.pull_subscribe(
            subject_filter,
            stream=stream_name,
            durable=durable_name
        )
    
    async def pull_subscribe(self, request):
        """Create a pull subscription.
        
        Args:
            request: PullSubscribeRequest with subject, stream, and optional durable
            
        Returns:
            NATS Consumer subscription object
            
        Raises:
            RuntimeError: If JetStream context not set
        """
        if not self.js:
            raise RuntimeError("JetStream context not set. Call set_context() first.")
        
        return await self.js.pull_subscribe(
            request.subject,
            stream=request.stream,
            durable=request.durable
        )
    
    async def subscribe(self, subject: str, stream: str | None = None, ordered_consumer: bool = False):
        """Create a push subscribe consumer.
        
        Args:
            subject: Subject filter
            stream: Optional stream name
            ordered_consumer: Whether to use ordered consumer
            
        Returns:
            NATS Consumer subscription object
            
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
    
    async def fetch_messages(self, consumer, limit: int, timeout: int):
        """Fetch messages from a consumer.
        
        Args:
            consumer: Consumer subscription object
            limit: Maximum number of messages to fetch
            timeout: Timeout in seconds
            
        Returns:
            List of messages
            
        Raises:
            Exception: If fetch fails
        """
        return await consumer.fetch(limit, timeout=timeout)
