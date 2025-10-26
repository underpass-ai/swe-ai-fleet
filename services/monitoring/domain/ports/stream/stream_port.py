"""Port for stream operations (technology-agnostic)."""
from abc import ABC, abstractmethod


class StreamPort(ABC):
    """Abstract port for stream operations."""

    @abstractmethod
    def set_context(self, stream_context) -> None:
        """Set stream processing context.

        Args:
            stream_context: Stream context from connection
        """
        pass

    @abstractmethod
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
            Consumer subscription object
        """
        pass

    @abstractmethod
    async def pull_subscribe(self, request):
        """Create a pull subscription.

        Args:
            request: PullSubscribeRequest with subject, stream, and optional durable

        Returns:
            Consumer subscription object
        """
        pass

    @abstractmethod
    async def subscribe(self, subject: str, stream: str | None = None, ordered_consumer: bool = False):
        """Create a push subscription.

        Args:
            subject: Subject filter
            stream: Optional stream name
            ordered_consumer: Whether to use ordered consumer

        Returns:
            Consumer subscription object
        """
        pass

    @abstractmethod
    async def fetch_messages(self, consumer, limit: int, timeout: int = 1):
        """Fetch messages from a consumer.

        Args:
            consumer: Consumer subscription object
            limit: Maximum number of messages to fetch
            timeout: Timeout in seconds (default: 1)

        Returns:
            List of messages
        """
        pass
