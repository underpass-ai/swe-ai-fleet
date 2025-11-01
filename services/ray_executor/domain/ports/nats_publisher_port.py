"""Port for NATS event publishing."""

from typing import Protocol


class NATSPublisherPort(Protocol):
    """Port defining the interface for NATS event publishing.

    This port abstracts NATS messaging, allowing the domain to remain
    independent of NATS implementation details.

    Following Hexagonal Architecture (Dependency Inversion Principle):
    - Domain defines the port (this interface)
    - Infrastructure provides the adapter (NATS JetStream implementation)
    """

    async def publish_stream_event(
        self,
        event_type: str,
        agent_id: str,
        data: dict[str, any],
    ) -> None:
        """Publish a streaming event to NATS.

        Args:
            event_type: Type of event (e.g. "vllm_stream_start", "vllm_stream_chunk")
            agent_id: Agent identifier for subject routing
            data: Event payload data

        Raises:
            Exception: If publish fails (should not fail silently)
        """
        ...

    async def publish_deliberation_result(
        self,
        deliberation_id: str,
        task_id: str,
        status: str,
        result: dict[str, any] | None = None,
        error: str | None = None,
    ) -> None:
        """Publish deliberation completion result to NATS.

        Args:
            deliberation_id: Unique deliberation identifier
            task_id: Task identifier
            status: "completed" or "failed"
            result: Deliberation result if completed
            error: Error message if failed
        """
        ...

