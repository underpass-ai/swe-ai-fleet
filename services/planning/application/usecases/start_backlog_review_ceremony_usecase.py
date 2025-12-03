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

from planning.application.ports import MessagingPort, OrchestratorPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)

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
    """

    storage: StoragePort
    orchestrator: OrchestratorPort
    messaging: MessagingPort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        started_by: UserName,
    ) -> BacklogReviewCeremony:
        """
        Start backlog review ceremony (gRPC ACK pattern).

        Calls Orchestrator via gRPC (receives ACK immediately ~30ms per call).
        Returns ceremony in IN_PROGRESS (~300ms for 9 calls).

        Final results arrive asynchronously via NATS events.

        Args:
            ceremony_id: ID of ceremony to start
            started_by: User starting the ceremony (typically PO)

        Returns:
            BacklogReviewCeremony in IN_PROGRESS status (reviews pending)

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

        # TODO: Get context for story first (Context Service)
        # For now, submit with story_id as description

        for story_id in ceremony.story_ids:
            for role in ["ARCHITECT", "QA", "DEVOPS"]:
                try:
                    from planning.application.ports.orchestrator_port import (
                        DeliberationRequest,
                        TaskConstraints,
                    )

                    # Build task_id with metadata for NATS callback
                    # Format: "ceremony-{id}:story-{id}:role-{role}"
                    # This allows BacklogReviewResultConsumer to map result back
                    task_id = f"ceremony-{ceremony_id.value}:story-{story_id.value}:role-{role}"

                    # gRPC call (returns ACK immediately ~30ms)
                    await self.orchestrator.deliberate(
                        DeliberationRequest(
                            task_description=f"[{task_id}] Review story {story_id.value} from {role} perspective",
                            role=role,
                            constraints=TaskConstraints(
                                rubric="Evaluate technical feasibility, testability, infrastructure needs",
                                requirements=(
                                    "Identify components needed",
                                    "List high-level tasks",
                                    "Estimate complexity",
                                ),
                                timeout_seconds=180,
                            ),
                            rounds=1,
                            num_agents=3,
                        )
                    )

                    logger.info(
                        f"Submitted {role} review for {story_id.value}: "
                        f"ACK received (response contains proposals)"
                    )

                except Exception as e:
                    # Log error but continue with other roles
                    logger.error(
                        f"Failed to submit {role} review for {story_id.value}: {e}",
                        exc_info=True,
                    )
                    # Continue with other deliberations (best-effort)
                    continue

        logger.info(
            f"Ceremony {ceremony_id.value} started: "
            f"submitted {len(ceremony.story_ids) * 3} deliberation requests"
        )

        # Publish ceremony started event (for UI updates)
        try:
            await self.messaging.publish(
                subject="planning.backlog_review.ceremony.started",
                payload={
                    "ceremony_id": ceremony_id.value,
                    "status": "IN_PROGRESS",
                    "total_stories": len(ceremony.story_ids),
                    "started_by": started_by.value,
                    "started_at": started_at.isoformat(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to publish ceremony.started event: {e}")

        # Return ceremony in IN_PROGRESS (deliberations running in background)
        # Background processing (~45s per role, parallel):
        # 1. Orchestrator submits jobs to Ray
        # 2. Ray Workers execute deliberations with vLLM
        # 3. Agents publish "agent.response.completed" to NATS
        # 4. BacklogReviewResultConsumer updates ceremony → REVIEWING
        return ceremony

