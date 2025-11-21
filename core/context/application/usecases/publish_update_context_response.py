"""Use case for publishing UpdateContext response.

Following Hexagonal Architecture:
- Application layer use case
- Depends on MessagingPort (interface)
- Orchestrates response publishing
"""

import logging

from core.context.infrastructure.dtos.update_context_response_dto import (
    UpdateContextResponseDTO,
)
from core.context.ports.messaging_port import MessagingPort

logger = logging.getLogger(__name__)


class PublishUpdateContextResponseUseCase:
    """Use case for publishing UpdateContext response.

    Responsibility:
    - Orchestrate publishing of UpdateContext response
    - Handle errors gracefully
    - Validate DTO (fail-fast)

    Following Hexagonal Architecture:
    - Application layer (orchestration)
    - Depends on MessagingPort (interface, not concrete adapter)
    - No domain logic, just coordination
    """

    def __init__(self, messaging_port: MessagingPort) -> None:
        """Initialize use case with messaging port.

        Args:
            messaging_port: MessagingPort implementation (injected)
        """
        self._messaging = messaging_port

    async def execute(self, response_dto: UpdateContextResponseDTO) -> None:
        """Publish UpdateContext response.

        Args:
            response_dto: UpdateContext response DTO

        Raises:
            ValueError: If response_dto is invalid
            RuntimeError: If publishing fails
        """
        # Fail-fast validation
        if not response_dto.story_id or not response_dto.story_id.strip():
            raise ValueError("response_dto.story_id cannot be empty")

        if response_dto.version < 0:
            raise ValueError(f"response_dto.version must be >= 0, got {response_dto.version}")

        try:
            await self._messaging.publish_update_context_response(response_dto)
            logger.debug(
                f"Published update context response: story_id={response_dto.story_id}, "
                f"version={response_dto.version}"
            )
        except Exception as e:
            logger.error(
                f"Failed to publish update context response: story_id={response_dto.story_id}, "
                f"version={response_dto.version}, error={e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Failed to publish update context response: {e}"
            ) from e

