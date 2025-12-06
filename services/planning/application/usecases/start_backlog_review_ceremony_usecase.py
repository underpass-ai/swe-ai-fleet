"""StartBacklogReviewCeremonyUseCase - Start ceremony (gRPC ACK + NATS Callback).

Use Case (Application Layer):
- Starts the backlog review ceremony
- Calls Orchestrator via gRPC (receives ACK immediately)
- Orchestrator submits jobs to Ray (background)
- Returns ceremony in IN_PROGRESS (~300ms)
- Results arrive later via NATS events (BacklogReviewResultConsumer)

Following Hybrid Architecture (Request-Acknowledge + Async Callback):
- Planning → Orchestrator: gRPC Deliberate() [ACK response ~30ms]
- Orchestrator → Ray: Submit jobs (background)
- Ray/vLLM → NATS: Publish "agent.response.completed"
- Planning consumer: Update ceremony with results
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from planning.application.ports import (
    ContextPort,
    MessagingPort,
    OrchestratorPort,
    StoragePort,
)
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.entities.backlog_review_context_request import (
    BacklogReviewContextRequest,
)
from planning.domain.entities.backlog_review_deliberation_request import (
    BacklogReviewDeliberationRequest,
)
from planning.infrastructure.mappers.backlog_review_deliberation_mapper import (
    BacklogReviewDeliberationMapper,
)
from planning.domain.entities.backlog_review_task_description import (
    BacklogReviewTaskDescription,
)
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.deliberation_id import DeliberationId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_phase import (
    BacklogReviewPhase,
)
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
from planning.domain.value_objects.statuses.token_budget import TokenBudget

logger = logging.getLogger(__name__)


@dataclass
class StartBacklogReviewCeremonyUseCase:
    """
    Start backlog review ceremony (gRPC ACK + NATS Callback).

    This use case (Hybrid Pattern):
    1. Retrieves ceremony
    2. Validates ceremony is in DRAFT status
    3. Validates ceremony has at least one story
    4. Starts ceremony (DRAFT → IN_PROGRESS)
    5. Calls Orchestrator via gRPC for each role (receives ACK ~30ms each)
    6. Returns ceremony in IN_PROGRESS (~300ms total)
    7. Background processing:
       - Orchestrator submits Ray jobs
       - Ray executes deliberations (~45s per role, parallel)
       - Agent publishes "agent.response.completed" to NATS
       - BacklogReviewResultConsumer updates ceremony → REVIEWING

    Dependencies:
    - StoragePort: For ceremony persistence
    - OrchestratorPort: For gRPC calls (ACK responses)
    - MessagingPort: For ceremony status events
    - ContextPort: For fetching story context before deliberations
    """

    storage: StoragePort
    orchestrator: OrchestratorPort
    messaging: MessagingPort
    context: ContextPort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        started_by: UserName,
    ) -> tuple[BacklogReviewCeremony, int]:
        """
        Start backlog review ceremony (gRPC ACK pattern).

        Calls Orchestrator via gRPC (receives ACK immediately ~30ms per call).
        Returns ceremony in IN_PROGRESS (~300ms for 9 calls).

        Final results arrive asynchronously via NATS events.

        Args:
            ceremony_id: ID of ceremony to start
            started_by: User starting the ceremony (typically PO)

        Returns:
            Tuple of (BacklogReviewCeremony in IN_PROGRESS, total deliberations submitted)

        Raises:
            CeremonyNotFoundError: If ceremony not found
            ValueError: If ceremony not in DRAFT or has no stories
            OrchestratorError: If gRPC call fails
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

        # Submit deliberations to Orchestrator (gRPC - returns ACK immediately)
        # Planning receives ACK (~30ms each), NOT final result
        # Final results arrive via NATS events (agent.response.completed)
        deliberations_submitted = await self._submit_all_deliberations(
            ceremony_id, ceremony.story_ids
        )

        # Publish ceremony started event (for UI updates)
        try:
            await self.messaging.publish_ceremony_started(
                ceremony_id=ceremony_id,
                status=ceremony.status,
                total_stories=len(ceremony.story_ids),
                deliberations_submitted=deliberations_submitted,
                started_by=started_by,
                started_at=started_at,
            )
        except Exception as e:
            logger.warning(f"Failed to publish ceremony.started event: {e}")

        # Return ceremony in IN_PROGRESS (deliberations running in background)
        # Background processing (~45s per role, parallel):
        # 1. Orchestrator submits jobs to Ray
        # 2. Ray Workers execute deliberations with vLLM
        # 3. Agents publish "agent.response.completed" to NATS
        # 4. BacklogReviewResultConsumer updates ceremony → REVIEWING
        return ceremony, deliberations_submitted

    async def _submit_all_deliberations(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_ids: tuple[StoryId, ...],
    ) -> int:
        """
        Submit all deliberations for all stories and roles.

        Args:
            ceremony_id: Ceremony identifier
            story_ids: Story identifiers to process

        Returns:
            Number of deliberations successfully submitted
        """
        deliberations_submitted = 0
        for story_id in story_ids:
            for role_enum in BacklogReviewRole.all_roles():
                if await self._submit_deliberation_for_story_and_role(
                    ceremony_id, story_id, role_enum
                ):
                    deliberations_submitted += 1

        logger.info(
            f"Ceremony {ceremony_id.value} started: "
            f"submitted {deliberations_submitted} of {len(story_ids) * 3} deliberation requests"
        )
        return deliberations_submitted

    async def _submit_deliberation_for_story_and_role(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        role: BacklogReviewRole,
    ) -> bool:
        """
        Submit a single deliberation for a story and role.

        Uses Tell, Don't Ask: delegates to domain entities for construction.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            role: Review role

        Returns:
            True if submission successful, False otherwise
        """
        try:
            # Get context (may be None if unavailable)
            context_text = await self._get_context_for_story_and_role(story_id, role)

            # Build task description using domain entity (Tell, Don't Ask)
            task_description_entity = self._build_task_description(
                ceremony_id, story_id, role, context_text
            )

            # Build deliberation request using domain entity (Tell, Don't Ask)
            deliberation_request_entity = (
                BacklogReviewDeliberationRequest.build_for_role(
                    task_description_entity=task_description_entity,
                    role=role,
                )
            )

            # Submit deliberation via orchestrator
            deliberation_id = await self._submit_to_orchestrator(
                deliberation_request_entity
            )

            # Validate deliberation_id was returned (defensive programming)
            if not deliberation_id:
                logger.error(
                    f"Failed to submit {role.value} review for {story_id.value}: "
                    "Orchestrator returned None"
                )
                return False

            logger.info(
                f"✅ Submitted {role.value} review for {story_id.value}: "
                f"deliberation_id={deliberation_id.value} (fire-and-forget, results via NATS)"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to submit {role.value} review for {story_id.value}: {e}",
                exc_info=True,
            )
            return False

    async def _get_context_for_story_and_role(
        self,
        story_id: StoryId,
        role: BacklogReviewRole,
    ) -> str | None:
        """
        Get context for story and role from Context Service.

        Returns None if context unavailable (allows ceremony to proceed).

        Args:
            story_id: Story identifier
            role: Review role

        Returns:
            Context text or None if unavailable
        """
        try:
            # Create domain entity for context request (Tell, Don't Ask)
            context_request = BacklogReviewContextRequest.build_for_design_phase(
                story_id=story_id,
                role=role,
                token_budget=TokenBudget.STANDARD,
            )

            # Convert to port parameters and call Context Service
            context_params = context_request.to_context_port_params()
            context_response = await self.context.get_context(**context_params)

            logger.debug(
                f"Retrieved context for story {story_id.value}, role {role.value}: "
                f"{context_response.token_count} tokens"
            )
            return context_response.context

        except Exception as context_error:
            logger.warning(
                f"Failed to retrieve context for story {story_id.value}, "
                f"role {role.value}: {context_error}. Proceeding with basic description."
            )
            return None

    def _build_task_description(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        role: BacklogReviewRole,
        context_text: str | None,
    ) -> BacklogReviewTaskDescription:
        """
        Build task description using domain entity (Tell, Don't Ask).

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            role: Review role
            context_text: Context text or None

        Returns:
            BacklogReviewTaskDescription entity
        """
        if context_text:
            return BacklogReviewTaskDescription.build_with_context(
                ceremony_id=ceremony_id,
                story_id=story_id,
                role=role,
                context_text=context_text,
            )
        else:
            return BacklogReviewTaskDescription.build_without_context(
                ceremony_id=ceremony_id,
                story_id=story_id,
                role=role,
            )

    async def _submit_to_orchestrator(
        self,
        deliberation_request_entity: BacklogReviewDeliberationRequest,
    ) -> DeliberationId:
        """
        Submit deliberation request to orchestrator via gRPC.

        Args:
            deliberation_request_entity: Domain entity for deliberation request

        Returns:
            Deliberation ID from orchestrator
        """
        # Convert domain entity to port DTO using mapper
        deliberation_request = (
            BacklogReviewDeliberationMapper.to_deliberation_request(
                deliberation_request_entity
            )
        )
        return await self.orchestrator.deliberate(deliberation_request)

