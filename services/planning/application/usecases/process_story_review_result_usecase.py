"""ProcessStoryReviewResultUseCase - Update ceremony with story review result.

Use Case (Application Layer):
- Updates ceremony with review result from one council (ARCHITECT, QA, or DEVOPS)
- Accumulates feedback from multiple roles
- Transitions to REVIEWING when all stories reviewed
- Publishes ceremony.reviewing event

Following Event-Driven Architecture:
- Called by BacklogReviewResultConsumer (async callback pattern)
- Orchestrator publishes story.reviewed after deliberations
- Planning consumes and updates ceremony state via this use case
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from planning.application.dto import StoryReviewResultDTO
from planning.application.ports import ContextPort, MessagingPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.agent_deliberation import AgentDeliberation
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessStoryReviewResultUseCase:
    """
    Process story review result from Orchestrator (async callback).

    This use case (Event-Driven Pattern):
    1. Retrieves ceremony
    2. Builds or updates StoryReviewResult for specific role
    3. Updates ceremony with review result
    4. Checks if all stories reviewed (3 roles × N stories)
    5. Transitions to REVIEWING if complete
    6. Publishes ceremony.reviewing event
    7. Persists ceremony

    Dependencies:
    - StoragePort: For ceremony persistence
    - MessagingPort: For event publishing
    - ContextPort: For saving deliberation results to Context Service
    """

    storage: StoragePort
    messaging: MessagingPort
    context: ContextPort

    async def execute(
        self,
        review_result_dto: StoryReviewResultDTO,
    ) -> BacklogReviewCeremony:
        """
        Process story review result from one council.

        Args:
            review_result_dto: DTO containing review result data

        Returns:
            Updated BacklogReviewCeremony entity

        Raises:
            CeremonyNotFoundError: If ceremony not found
            ValueError: If ceremony not in IN_PROGRESS or invalid DTO
            StorageError: If persistence fails
        """
        # Extract data from DTO
        ceremony_id = review_result_dto.ceremony_id
        story_id = review_result_dto.story_id
        role = review_result_dto.role
        feedback = review_result_dto.feedback
        proposal = review_result_dto.proposal
        agent_id = review_result_dto.agent_id
        reviewed_at = review_result_dto.reviewed_at

        # Retrieve ceremony
        ceremony = await self.storage.get_backlog_review_ceremony(ceremony_id)

        if not ceremony:
            raise CeremonyNotFoundError(
                f"Ceremony not found: {ceremony_id.value}"
            )

        if not ceremony.status.is_in_progress():
            logger.warning(
                f"Received review for ceremony {ceremony_id.value} "
                f"in status {ceremony.status.to_string()} (expected IN_PROGRESS)"
            )
            # Don't raise - tolerate late arrivals
            return ceremony

        # Build or update StoryReviewResult for this role
        review_result = self._build_or_update_review_result(
            ceremony=ceremony,
            story_id=story_id,
            role=role,
            agent_id=agent_id,
            feedback=feedback,
            proposal=proposal,
            reviewed_at=reviewed_at,
        )

        # Update ceremony with review result (immutably)
        ceremony = ceremony.update_review_result(
            story_id=story_id,
            review_result=review_result,
            updated_at=datetime.now(UTC),
        )

        # Check if this story has all role deliberations complete
        review_result = ceremony.find_review_result_by_story_id(story_id)
        if review_result and review_result.has_all_role_deliberations():
            logger.info(
                f"✅ All role deliberations complete for story {story_id.value} "
                f"in ceremony {ceremony_id.value}. "
                f"Publishing deliberations complete event for task extraction."
            )
            # Publish event for Task Extraction Service to process
            await self._publish_deliberations_complete_event(
                ceremony_id=ceremony_id,
                story_id=story_id,
                review_result=review_result,
            )

        # Check if all stories are reviewed
        if self._all_stories_reviewed(ceremony):
            # Transition to REVIEWING (awaiting PO approval)
            ceremony = ceremony.mark_reviewing(
                ceremony.review_results, datetime.now(UTC)
            )
            logger.info(
                f"✅ Ceremony {ceremony_id.value} → REVIEWING "
                f"({len(ceremony.review_results)}/{len(ceremony.story_ids)} stories reviewed)"
            )

            # Publish ceremony.reviewing event
            await self._publish_ceremony_reviewing_event(ceremony)

        # Persist ceremony
        await self.storage.save_backlog_review_ceremony(ceremony)

        # Save deliberation to Context Service (step 8 of flow)
        # Extract task_id from ceremony (format: "ceremony-{id}:story-{id}:role-{role}")
        task_id = f"ceremony-{ceremony_id.value}:story-{story_id.value}:role-{role.value}"
        try:
            await self.context.save_deliberation(
                story_id=story_id.value,
                task_id=task_id,
                role=role.value,
                feedback=feedback,
                timestamp=reviewed_at.isoformat(),
            )
            logger.info(
                f"✓ Saved deliberation to Context Service: story_id={story_id.value}, "
                f"task_id={task_id}, role={role.value}"
            )
        except Exception as e:
            # Log error but don't fail the use case (deliberation is already persisted in ceremony)
            logger.error(
                f"Failed to save deliberation to Context Service: {e}. "
                f"Ceremony was still updated successfully.",
                exc_info=True
            )

        logger.info(
            f"✓ Ceremony {ceremony_id.value} updated with {role.value} review for {story_id.value}"
        )

        return ceremony

    def _build_or_update_review_result(
        self,
        ceremony: BacklogReviewCeremony,
        story_id: StoryId,
        role: BacklogReviewRole,
        agent_id: str,
        feedback: str,
        proposal: dict | str,
        reviewed_at: datetime,
    ) -> StoryReviewResult:
        """
        Build or update StoryReviewResult with role feedback.

        If review result exists, update it with new role feedback.
        If not, create new one.

        Args:
            ceremony: Current ceremony
            story_id: Story being reviewed
            role: Council role (BacklogReviewRole enum)
            feedback: Role feedback
            reviewed_at: Review timestamp

        Returns:
            Updated StoryReviewResult
        """
        # Find existing review result (Tell, Don't Ask)
        existing_result = ceremony.find_review_result_by_story_id(story_id)

        # Parse feedback to extract components
        # Expected format from Orchestrator (simplified for now):
        # - Title: ...
        # - Description: ...
        # - Acceptance Criteria: ...
        # - Technical Notes: ...
        # - Roles: ...
        # - Complexity: ...
        # - Dependencies: ...
        # - Tasks: ...
        components = self._parse_feedback(feedback)
        tasks_outline = tuple(components.get("tasks", []))

        # Create AgentDeliberation from DTO
        agent_deliberation = AgentDeliberation(
            agent_id=agent_id,
            role=role,
            proposal=proposal,
            deliberated_at=reviewed_at,
        )

        if existing_result:
            # Tell, Don't Ask: delegate update to the entity
            return existing_result.add_agent_deliberation(
                deliberation=agent_deliberation,
                feedback=feedback,
                tasks_outline=tasks_outline,
                reviewed_at=reviewed_at,
            )
        else:
            # Create initial result using factory method, then add deliberation
            result = StoryReviewResult.create_from_role_feedback(
                story_id=story_id,
                role=role,
                feedback=feedback,
                tasks_outline=tasks_outline,
                reviewed_at=reviewed_at,
            )
            # Add the agent deliberation
            return result.add_agent_deliberation(
                deliberation=agent_deliberation,
                feedback=feedback,
                tasks_outline=tasks_outline,
                reviewed_at=reviewed_at,
            )

    def _parse_feedback(self, feedback: str) -> dict[str, str | list[str]]:
        """
        Parse feedback string to extract components.

        This is a simplified parser. In production, feedback should be
        structured JSON from Orchestrator.

        Args:
            feedback: Raw feedback string

        Returns:
            Dictionary with parsed components
        """
        # Extract tasks from feedback (simple heuristic)
        tasks = self._extract_tasks_from_feedback(feedback)

        # Simplified parser (TODO: improve with structured format)
        return {
            "title": "Implementation Plan",
            "description": feedback[:200] if len(feedback) > 200 else feedback,
            "acceptance_criteria": ["Council review completed"],  # At least one criterion
            "technical_notes": "",
            "roles": ["DEVELOPER"],
            "complexity": "MEDIUM",
            "dependencies": [],
            "tasks": list(tasks),
        }

    def _extract_tasks_from_feedback(self, feedback: str) -> tuple[str, ...]:
        """
        Extract tasks from feedback using simple pattern matching.

        Uses line-by-line processing to avoid regex backtracking vulnerabilities.

        Args:
            feedback: Feedback text

        Returns:
            Tuple of extracted task strings
        """
        if not feedback or not feedback.strip():
            return ()

        # Limit input length to prevent ReDoS attacks
        MAX_FEEDBACK_LENGTH = 10000
        if len(feedback) > MAX_FEEDBACK_LENGTH:
            logger.warning(
                f"Feedback length ({len(feedback)}) exceeds maximum ({MAX_FEEDBACK_LENGTH}), truncating"
            )
            feedback = feedback[:MAX_FEEDBACK_LENGTH]

        import re

        # Process line-by-line to avoid regex backtracking issues
        # This is more efficient and safer than MULTILINE mode
        tasks: list[str] = []
        lines = feedback.splitlines()

        # Limit number of lines to process (additional safety)
        MAX_LINES = 1000
        if len(lines) > MAX_LINES:
            logger.warning(
                f"Feedback has {len(lines)} lines, limiting to {MAX_LINES}"
            )
            lines = lines[:MAX_LINES]

        # Simple patterns - use non-greedy quantifier with max length to prevent backtracking
        # Match up to 500 chars per task description (reasonable limit)
        numbered_pattern = re.compile(r"^\d+\.\s+(.{1,500})$")
        bullet_pattern = re.compile(r"^[-*]\s+(.{1,500})$")

        for line in lines:
            if len(tasks) >= 10:  # Limit to 10 tasks
                break

            line = line.strip()
            if not line:
                continue

            # Try numbered pattern
            match = numbered_pattern.match(line)
            if match:
                tasks.append(match.group(1).strip())
                continue

            # Try bullet pattern
            match = bullet_pattern.match(line)
            if match:
                tasks.append(match.group(1).strip())

        return tuple(tasks)

    def _all_stories_reviewed(self, ceremony: BacklogReviewCeremony) -> bool:
        """
        Check if all stories have been reviewed by all councils.

        A story is fully reviewed when it has review results from all 3 councils:
        - ARCHITECT
        - QA
        - DEVOPS

        Args:
            ceremony: Ceremony to check

        Returns:
            True if all stories reviewed by all councils
        """
        # All stories must have review results
        if len(ceremony.review_results) < len(ceremony.story_ids):
            return False

        # Each story should have feedback from all 3 councils
        for story_id in ceremony.story_ids:
            result = ceremony.find_review_result_by_story_id(story_id)

            if not result:
                return False

            # Check all councils provided feedback
            if not result.architect_feedback or not result.qa_feedback or not result.devops_feedback:
                return False

        return True

    async def _publish_ceremony_reviewing_event(
        self, ceremony: BacklogReviewCeremony
    ) -> None:
        """
        Publish ceremony.reviewing event (best-effort).

        Args:
            ceremony: Ceremony that transitioned to REVIEWING
        """
        try:
            await self.messaging.publish(
                subject="planning.backlog_review.ceremony.reviewing",
                payload={
                    "ceremony_id": ceremony.ceremony_id.value,
                    "status": "REVIEWING",
                    "total_stories": len(ceremony.story_ids),
                    "total_reviews": len(ceremony.review_results),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to publish ceremony.reviewing event: {e}")

    async def _publish_deliberations_complete_event(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        review_result: StoryReviewResult,
    ) -> None:
        """
        Publish deliberations.complete event for Task Extraction Service.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            review_result: Review result with all agent deliberations
        """
        try:
            # Convert agent deliberations to serializable format
            agent_deliberations = []
            for deliberation in review_result.agent_deliberations:
                agent_deliberations.append({
                    "agent_id": deliberation.agent_id,
                    "role": deliberation.role.value,
                    "proposal": deliberation.proposal,
                    "deliberated_at": deliberation.deliberated_at.isoformat(),
                })

            await self.messaging.publish(
                subject="planning.backlog_review.deliberations.complete",
                payload={
                    "ceremony_id": ceremony_id.value,
                    "story_id": story_id.value,
                    "agent_deliberations": agent_deliberations,
                },
            )
            logger.info(
                f"Published deliberations complete event for story {story_id.value} "
                f"in ceremony {ceremony_id.value}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to publish deliberations.complete event: {e}",
                exc_info=True,
            )

