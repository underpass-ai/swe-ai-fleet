"""StartBacklogReviewCeremonyUseCase - Start ceremony and coordinate reviews.

Use Case (Application Layer):
- Orchestrates the complete backlog review process
- Coordinates ReviewStoryWithCouncilsUseCase for each story
- Updates ceremony status through FSM transitions
- Publishes progress events
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.application.usecases.review_story_with_councils_usecase import (
    ReviewStoryWithCouncilsUseCase,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.review.story_review_result import StoryReviewResult

logger = logging.getLogger(__name__)


@dataclass
class StartBacklogReviewCeremonyUseCase:
    """
    Start backlog review ceremony and coordinate story reviews.

    This use case (Complex Orchestration):
    1. Retrieves ceremony
    2. Validates ceremony is in DRAFT status
    3. Validates ceremony has at least one story
    4. Starts ceremony (DRAFT → IN_PROGRESS)
    5. For each story:
       - Calls ReviewStoryWithCouncilsUseCase
       - Collects StoryReviewResult
    6. Marks ceremony as REVIEWING (awaiting PO approval)
    7. Publishes planning.backlog_review.completed event
    8. Returns updated ceremony

    Dependencies:
    - StoragePort: For ceremony persistence
    - MessagingPort: For event publishing
    - ReviewStoryWithCouncilsUseCase: For coordinating council reviews
    """

    storage: StoragePort
    messaging: MessagingPort
    review_story_use_case: ReviewStoryWithCouncilsUseCase

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        started_by: UserName,
    ) -> BacklogReviewCeremony:
        """
        Start backlog review ceremony.

        This is a LONG-RUNNING operation (minutes).
        Each story review involves:
        - Fetching context (Context Service)
        - 3 deliberations (Orchestrator → Ray → vLLM)
        - Consolidating results

        Args:
            ceremony_id: ID of ceremony to start
            started_by: User starting the ceremony (typically PO)

        Returns:
            Updated BacklogReviewCeremony in REVIEWING status

        Raises:
            CeremonyNotFoundError: If ceremony not found
            ValueError: If ceremony not in DRAFT or has no stories
            OrchestratorError: If deliberation fails
            StorageError: If persistence fails
        """
        # Retrieve ceremony
        ceremony = await self.storage.get_backlog_review_ceremony(ceremony_id)

        if not ceremony:
            raise CeremonyNotFoundError(
                f"Ceremony not found: {ceremony_id.value}"
            )

        # Validate can be started
        if not ceremony.status.is_draft():
            raise ValueError(
                f"Cannot start ceremony in status {ceremony.status.to_string()}"
            )

        if not ceremony.story_ids:
            raise ValueError(
                f"Cannot start ceremony {ceremony_id.value}: No stories to review"
            )

        logger.info(
            f"Starting backlog review ceremony {ceremony_id.value} "
            f"with {len(ceremony.story_ids)} stories"
        )

        # Start ceremony (DRAFT → IN_PROGRESS)
        started_at = datetime.now(UTC)
        ceremony = ceremony.start(started_at)

        # Persist IN_PROGRESS status
        await self.storage.save_backlog_review_ceremony(ceremony)

        # Review each story with councils
        review_results: list[StoryReviewResult] = []

        for idx, story_id in enumerate(ceremony.story_ids, 1):
            logger.info(
                f"Reviewing story {idx}/{len(ceremony.story_ids)}: {story_id.value}"
            )

            try:
                # Coordinate multi-council review
                review_result = await self.review_story_use_case.execute(
                    story_id=story_id
                )

                review_results.append(review_result)

                logger.info(
                    f"Story {story_id.value} reviewed successfully"
                )

            except Exception as e:
                # Log error but continue with other stories
                logger.error(
                    f"Failed to review story {story_id.value}: {e}",
                    exc_info=True,
                )

                # TODO: Decide how to handle partial failures
                # For now, skip the story and continue
                continue

        # Mark ceremony as REVIEWING (IN_PROGRESS → REVIEWING)
        updated_at = datetime.now(UTC)
        ceremony = ceremony.mark_reviewing(tuple(review_results), updated_at)

        # Persist REVIEWING status
        await self.storage.save_backlog_review_ceremony(ceremony)

        logger.info(
            f"Ceremony {ceremony_id.value} completed: "
            f"{len(review_results)}/{len(ceremony.story_ids)} stories reviewed"
        )

        # Publish completion event (best-effort)
        try:
            await self.messaging.publish(
                subject="planning.backlog_review.completed",
                payload={
                    "ceremony_id": ceremony_id.value,
                    "status": "REVIEWING",
                    "total_stories": len(ceremony.story_ids),
                    "reviewed_stories": len(review_results),
                    "updated_at": updated_at.isoformat(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to publish backlog_review.completed event: {e}")

        return ceremony

