"""Messaging port for publishing events to NATS.

Following Hexagonal Architecture: port defines the interface for
messaging operations, adapters implement it.
"""

from typing import Protocol

from core.context.infrastructure.dtos.rehydrate_session_response_dto import (
    RehydrateSessionResponseDTO,
)
from core.context.infrastructure.dtos.update_context_response_dto import (
    UpdateContextResponseDTO,
)


class MessagingPort(Protocol):
    """Port for publishing messages to NATS.

    Following Hexagonal Architecture:
    - Port defines the interface (application layer)
    - Adapters implement it (infrastructure layer)
    - Handlers depend on port, not concrete adapter
    """

    async def publish_update_context_response(
        self, response: UpdateContextResponseDTO
    ) -> None:
        """Publish UpdateContext response to NATS.

        Args:
            response: UpdateContext response DTO

        Raises:
            RuntimeError: If publishing fails
        """
        ...

    async def publish_rehydrate_session_response(
        self, response: RehydrateSessionResponseDTO
    ) -> None:
        """Publish RehydrateSession response to NATS.

        Args:
            response: RehydrateSession response DTO

        Raises:
            RuntimeError: If publishing fails
        """
        ...

    async def publish_context_updated(self, story_id: str, version: int) -> None:
        """Publish context updated event to NATS.

        Args:
            story_id: Story identifier
            version: Context version number

        Raises:
            RuntimeError: If publishing fails
        """
        ...

