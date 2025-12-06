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

        deliberations_submitted = 0
        for story_id in ceremony.story_ids:
            for role_enum in BacklogReviewRole.all_roles():
                try:
                    # Get context for story from Context Service
                    # This provides role-specific context including story details,
                    # plan information, relevant decisions, and task dependencies
                    try:
                        # Create domain entity for context request using builder
                        context_request = BacklogReviewContextRequest.build_for_design_phase(
                            story_id=story_id,
                            role=role_enum,
                            token_budget=TokenBudget.STANDARD,
                        )

                        # Convert to port parameters and call Context Service
                        context_params = context_request.to_context_port_params()
                        context_response = await self.context.get_context(**context_params)
                        context_text = context_response.context
                        logger.debug(
                            f"Retrieved context for story {story_id.value}, role {role_enum.value}: "
                            f"{context_response.token_count} tokens"
                        )
                    except Exception as context_error:
                        # Log context retrieval failure but continue with basic description
                        # This allows ceremony to proceed even if context service is unavailable
                        logger.warning(
                            f"Failed to retrieve context for story {story_id.value}, "
                            f"role {role_enum.value}: {context_error}. Proceeding with basic description."
                        )
                        context_text = None

                    # Build task description using domain entity builder
                    if context_text:
                        task_description_entity = (
                            BacklogReviewTaskDescription.build_with_context(
                                ceremony_id=ceremony_id,
                                story_id=story_id,
                                role=role_enum,
                                context_text=context_text,
                            )
                        )
                    else:
                        # Fallback to basic description if context unavailable
                        task_description_entity = (
                            BacklogReviewTaskDescription.build_without_context(
                                ceremony_id=ceremony_id,
                                story_id=story_id,
                                role=role_enum,
                            )
                        )

                    # Build deliberation request using domain entity builder
                    deliberation_request_entity = (
                        BacklogReviewDeliberationRequest.build_for_role(
                            task_description_entity=task_description_entity,
                            role=role_enum,
                        )
                    )

                    # Convert domain entity to port DTO using mapper
                    # gRPC call (returns ACK immediately ~30ms, fire-and-forget)
                    deliberation_request = (
                        BacklogReviewDeliberationMapper.to_deliberation_request(
                            deliberation_request_entity
                        )
                    )
                    deliberation_id = await self.orchestrator.deliberate(
                        deliberation_request
                    )

                    deliberations_submitted += 1
                    logger.info(
                        f"✅ Submitted {role_enum.value} review for {story_id.value}: "
                        f"deliberation_id={deliberation_id.value} (fire-and-forget, results via NATS)"
                    )

                except Exception as e:
                    # Log error but continue with other roles
                    logger.error(
                        f"Failed to submit {role_enum.value} review for {story_id.value}: {e}",
                        exc_info=True,
                    )
                    # Continue with other deliberations (best-effort)
                    continue

        logger.info(
            f"Ceremony {ceremony_id.value} started: "
            f"submitted {deliberations_submitted} of {len(ceremony.story_ids) * 3} deliberation requests"
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

