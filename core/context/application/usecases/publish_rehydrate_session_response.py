"""Use case for publishing RehydrateSession response.

Following Hexagonal Architecture:
- Application layer use case
- Depends on MessagingPort (interface)
- Orchestrates response publishing
"""

import logging

from core.context.infrastructure.dtos.rehydrate_session_response_dto import (
    RehydrateSessionResponseDTO,
)
from core.context.ports.messaging_port import MessagingPort

logger = logging.getLogger(__name__)


class PublishRehydrateSessionResponseUseCase:
    """Use case for publishing RehydrateSession response.

    Responsibility:
    - Orchestrate publishing of RehydrateSession response
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

    async def execute(self, response_dto: RehydrateSessionResponseDTO) -> None:
        """Publish RehydrateSession response.

        Args:
            response_dto: RehydrateSession response DTO

        Raises:
            ValueError: If response_dto is invalid
            RuntimeError: If publishing fails
        """
        # Fail-fast validation
        if not response_dto.case_id or not response_dto.case_id.strip():
            raise ValueError("response_dto.case_id cannot be empty")

        if response_dto.generated_at_ms < 0:
            raise ValueError(
                f"response_dto.generated_at_ms must be >= 0, got {response_dto.generated_at_ms}"
            )

        try:
            await self._messaging.publish_rehydrate_session_response(response_dto)
            logger.debug(
                f"Published rehydrate session response: case_id={response_dto.case_id}, "
                f"packs={response_dto.packs_count}"
            )
        except Exception as e:
            logger.error(
                f"Failed to publish rehydrate session response: case_id={response_dto.case_id}, "
                f"packs={response_dto.packs_count}, error={e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Failed to publish rehydrate session response: {e}"
            ) from e

