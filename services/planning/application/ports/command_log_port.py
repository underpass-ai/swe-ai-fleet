"""Command log port for gRPC command idempotency.

Stores and retrieves command responses to enable idempotent gRPC operations.
Following Hexagonal Architecture: this is a PORT (interface) in the application layer.
"""

from typing import Protocol


class CommandLogPort(Protocol):
    """Port for command log operations (idempotency).

    Stores command responses keyed by request_id to enable idempotent gRPC operations:
    - If a request with the same request_id is received, return the cached response
    - Prevents duplicate execution of mutating commands (CreateTask, AddAgentDeliberation, etc.)

    Key format: planning:cmd:{request_id}
    Storage: Valkey (Redis-compatible) with permanent persistence (no TTL by default)

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (ValkeyCommandLogAdapter, etc.)
    - Application depends on PORT, not concrete implementation
    """

    async def get_response(
        self,
        request_id: str,
    ) -> bytes | None:
        """Get cached response for a request_id.

        Args:
            request_id: Unique request identifier

        Returns:
            Serialized response bytes if found, None otherwise

        Raises:
            Exception: If storage operation fails
        """
        ...

    async def store_response(
        self,
        request_id: str,
        response_bytes: bytes,
    ) -> None:
        """Store response for a request_id.

        Args:
            request_id: Unique request identifier
            response_bytes: Serialized response to store

        Raises:
            ValueError: If request_id is empty
            Exception: If storage operation fails
        """
        ...
