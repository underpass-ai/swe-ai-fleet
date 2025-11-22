"""Use case for publishing context updated events.

Following Hexagonal Architecture:
- Application layer use case
- Depends on MessagingPort (interface)
- Orchestrates event publishing
"""

import logging

from core.context.ports.messaging_port import MessagingPort

logger = logging.getLogger(__name__)


class PublishContextUpdatedUseCase:
    """Use case for publishing context updated events.

    Responsibility:
    - Orchestrate publishing of context.updated events
    - Handle errors gracefully (log but don't fail)
    - Validate inputs (fail-fast)

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

    async def execute(self, story_id: str, version: int) -> None:
        """Publish context updated event.

        Args:
            story_id: Story identifier
            version: Context version number

        Raises:
            ValueError: If story_id is empty or version is invalid
        """
        # Fail-fast validation
        if not story_id or not story_id.strip():
            raise ValueError("story_id cannot be empty")

        if version < 0:
            raise ValueError(f"version must be >= 0, got {version}")

        try:
            await self._messaging.publish_context_updated(story_id, version)
            logger.info(f"✓ Published context.updated event: story_id={story_id}, version={version}")
        except Exception as e:
            # Log error but don't fail - event publishing is best-effort
            logger.error(
                f"Failed to publish context.updated event: story_id={story_id}, "
                f"version={version}, error={e}",
                exc_info=True,
            )
            # Re-raise to allow caller to handle if needed
            raise

