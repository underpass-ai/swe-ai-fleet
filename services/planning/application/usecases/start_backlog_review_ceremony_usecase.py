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
    RayExecutorPort,
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
    5. Gets context from Context Service for each story/role
    6. Calls Ray Executor via gRPC for each role (receives ACK ~30ms each)
    7. Returns ceremony in IN_PROGRESS (~300ms total)
    8. Background processing:
       - Ray executes deliberations (~45s per role, parallel)
       - vLLM publishes "agent.response.completed" to NATS
       - BacklogReviewResultConsumer updates ceremony → REVIEWING

    Dependencies:
    - StoragePort: For ceremony persistence
    - RayExecutorPort: For gRPC calls to Ray Executor (ACK responses)
    - MessagingPort: For ceremony status events
    - ContextPort: For fetching story context before deliberations
    """

    storage: StoragePort
    ray_executor: RayExecutorPort
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
            # Get context (always returns string or raises ValueError)
            context_text = await self._get_context_for_story_and_role(story_id, role)

            # Log context for debugging
            logger.info(
                f"📋 Context retrieved for story {story_id.value}, role {role.value}:\n"
                f"   Context length: {len(context_text)} chars\n"
                f"   Context preview (first 500 chars):\n{context_text[:500]}..."
            )

            # Build task description using domain entity (Tell, Don't Ask)
            # context_text is guaranteed to be a string (not None) - method raises ValueError if unavailable
            task_description_entity = self._build_task_description(
                ceremony_id, story_id, role, context_text
            )

            # Log final task description
            logger.info(
                f"📝 Task description built for story {story_id.value}, role {role.value}:\n"
                f"   Task ID: {task_description_entity.task_id}\n"
                f"   Description length: {len(task_description_entity.description)} chars\n"
                f"   Description preview (first 1000 chars):\n{task_description_entity.description[:1000]}..."
            )

            # Build deliberation request using domain entity (Tell, Don't Ask)
            deliberation_request_entity = (
                BacklogReviewDeliberationRequest.build_for_role(
                    task_description_entity=task_description_entity,
                    role=role,
                )
            )

            # Submit deliberation directly to Ray Executor
            deliberation_id = await self._submit_to_ray_executor(
                deliberation_request_entity, story_id
            )

            # Validate deliberation_id was returned (defensive programming)
            if not deliberation_id:
                logger.error(
                    f"Failed to submit {role.value} review for {story_id.value}: "
                    "Ray Executor returned None"
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
    ) -> str:
        """
        Get context for story and role from Context Service.

        Falls back to basic story information (title + brief) if Context Service fails.
        Raises ValueError if story cannot be retrieved from storage (fail-fast).

        Args:
            story_id: Story identifier
            role: Review role

        Returns:
            Context text (never None)

        Raises:
            ValueError: If story cannot be retrieved from storage (fail-fast for client visibility)
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
                f"role {role.value}: {context_error}. Falling back to story basic info."
            )

            # Fallback: Get basic story information (title + brief) from storage
            # FAIL-FAST: If we can't get the story, raise an error so the client knows
            try:
                story = await self.storage.get_story(story_id)
                if story:
                    # Build basic context from story title and brief
                    fallback_context = (
                        f"Story Title: {story.title.value}\n\n"
                        f"Story Description:\n{story.brief.value}\n\n"
                        f"Please provide a comprehensive review from the {role.value} perspective "
                        f"based on the story information above."
                    )
                    logger.info(
                        f"Using fallback context for story {story_id.value} "
                        f"(title + brief, {len(fallback_context)} chars)"
                    )
                    return fallback_context
                else:
                    # Story not found in storage - fail fast so client knows
                    error_msg = (
                        f"Story {story_id.value} not found in storage. "
                        f"Cannot proceed with backlog review ceremony without story information."
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            except ValueError:
                # Re-raise ValueError (story not found) - fail fast
                raise
            except Exception as storage_error:
                # Storage error - fail fast so client knows
                error_msg = (
                    f"Failed to retrieve story {story_id.value} from storage: {storage_error}. "
                    f"Cannot proceed with backlog review ceremony without story information."
                )
                logger.error(error_msg, exc_info=True)
                raise ValueError(error_msg) from storage_error

    def _build_task_description(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        role: BacklogReviewRole,
        context_text: str,
    ) -> BacklogReviewTaskDescription:
        """
        Build task description using domain entity (Tell, Don't Ask).

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            role: Review role
            context_text: Context text (required, never None)

        Returns:
            BacklogReviewTaskDescription entity
        """
        # context_text is always provided (method raises ValueError if unavailable)
        return BacklogReviewTaskDescription.build_with_context(
            ceremony_id=ceremony_id,
            story_id=story_id,
            role=role,
            context_text=context_text,
        )

    async def _submit_to_ray_executor(
        self,
        deliberation_request_entity: BacklogReviewDeliberationRequest,
        story_id: StoryId,
    ) -> DeliberationId:
        """
        Submit deliberation request directly to Ray Executor via gRPC.

        Args:
            deliberation_request_entity: Domain entity for deliberation request
            story_id: Story identifier

        Returns:
            Deliberation ID from Ray Executor
        """
        # Extract task_id and task_description from entity
        task_id = deliberation_request_entity.task_description_entity.task_id
        task_description = deliberation_request_entity.task_description_entity.to_string()
        role = deliberation_request_entity.role.value  # Convert enum to string

        # Submit directly to Ray Executor
        return await self.ray_executor.submit_backlog_review_deliberation(
            task_id=task_id,
            task_description=task_description,
            role=role,
            story_id=story_id.value,
            num_agents=3,  # Default to 3 agents per role
        )

