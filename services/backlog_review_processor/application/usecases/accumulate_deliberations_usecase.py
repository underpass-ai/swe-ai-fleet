"""AccumulateDeliberationsUseCase - Accumulate agent deliberations and detect completion.

Use Case (Application Layer):
- Accumulates agent deliberations for a story
- Detects when all role deliberations are complete (ARCHITECT, QA, DEVOPS)
- Publishes event when all deliberations complete
- Manages in-memory state (no persistence)

Following Event-Driven Architecture:
- Called by BacklogReviewResultConsumer (async callback pattern)
- Publishes planning.backlog_review.deliberations.complete when ready
"""

import logging
from dataclasses import dataclass

from backlog_review_processor.application.ports.messaging_port import MessagingPort
from backlog_review_processor.application.ports.planning_port import (
    AddAgentDeliberationRequest,
    PlanningPort,
    PlanningServiceError,
)
from backlog_review_processor.application.ports.storage_port import StoragePort
from backlog_review_processor.domain.entities.backlog_review_result import (
    BacklogReviewResult,
)
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.nats_subject import NATSSubject
from backlog_review_processor.domain.value_objects.review.agent_deliberation import (
    AgentDeliberation,
)
from backlog_review_processor.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)

logger = logging.getLogger(__name__)


@dataclass
class AccumulateDeliberationsUseCase:
    """
    Accumulate agent deliberations and detect completion.

    This use case (Event-Driven Pattern):
    1. Persists each deliberation to Neo4j as it arrives
    2. Queries Neo4j to check if all role deliberations are complete (3 roles)
    3. Publishes planning.backlog_review.deliberations.complete event when ready

    Dependencies:
    - MessagingPort: For event publishing
    - StoragePort: For persisting and querying deliberations in Neo4j
    - PlanningPort: For persisting deliberations to Planning Service

    State Management:
    - No in-memory state (rehydratable from Neo4j)
    - Each deliberation is persisted immediately
    - Completion check queries Neo4j to verify all roles are present
    """

    messaging: MessagingPort
    storage: StoragePort
    planning: PlanningPort

    async def execute(self, result: BacklogReviewResult) -> None:
        """
        Accumulate agent deliberation and check for completion.

        Args:
            result: Backlog review result containing ceremony, story, agent, role, proposal, and timestamp

        Raises:
            ValueError: If validation fails
        """
        # Extract values from domain entity
        ceremony_id = result.ceremony_id
        story_id = result.story_id
        agent_id = result.agent_id
        role = result.role
        proposal = result.proposal
        reviewed_at = result.reviewed_at

        # Create AgentDeliberation
        deliberation = AgentDeliberation(
            agent_id=agent_id,
            role=role,
            proposal=proposal,
            deliberated_at=reviewed_at,
        )

        # Persist deliberation to storage (Neo4j) first
        await self.storage.save_agent_deliberation(
            ceremony_id=ceremony_id,
            story_id=story_id,
            deliberation=deliberation,
        )

        # Persist deliberation to Planning Service (for review results)
        # Extract feedback from proposal if available, otherwise use proposal as feedback
        feedback = ""
        if isinstance(proposal, dict):
            # Try to extract feedback from proposal dict
            feedback = proposal.get("feedback", proposal.get("content", str(proposal)))
        else:
            feedback = str(proposal)

        try:
            await self.planning.add_agent_deliberation(
                AddAgentDeliberationRequest(
                    ceremony_id=ceremony_id,
                    story_id=story_id,
                    role=role.value,
                    agent_id=agent_id,
                    feedback=feedback,
                    proposal=proposal,
                    reviewed_at=reviewed_at.isoformat(),
                )
            )
            logger.info(
                f"✅ Deliberation persisted to Planning Service: "
                f"ceremony={ceremony_id.value}, story={story_id.value}, "
                f"role={role.value}, agent={agent_id}"
            )
        except PlanningServiceError as e:
            # Log error but don't fail the use case (deliberation is already in Neo4j)
            # This ensures resilience if Planning Service is temporarily unavailable
            logger.warning(
                f"⚠️ Failed to persist deliberation to Planning Service: {e}. "
                f"Deliberation was still saved to Neo4j. "
                f"This may cause review results to be incomplete."
            )

        logger.info(
            f"📥 Saved deliberation: ceremony={ceremony_id.value}, "
            f"story={story_id.value}, role={role.value}, agent={agent_id}"
        )

        # Check if all role deliberations are complete (query Neo4j)
        has_all_roles = await self.storage.has_all_role_deliberations(
            ceremony_id=ceremony_id,
            story_id=story_id,
        )

        if has_all_roles:
            logger.info(
                f"✅ All role deliberations complete for story {story_id.value} "
                f"in ceremony {ceremony_id.value}. "
                f"Publishing deliberations complete event."
            )

            # Publish event for task extraction
            await self._publish_deliberations_complete_event(
                ceremony_id=ceremony_id,
                story_id=story_id,
            )

    async def _publish_deliberations_complete_event(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
    ) -> None:
        """
        Publish deliberations.complete event for Task Extraction Service.

        Event payload:
        {
            "ceremony_id": "ceremony-abc123",
            "story_id": "ST-456",
            "agent_deliberations": [
                {
                    "agent_id": "agent-architect-001",
                    "role": "ARCHITECT",
                    "proposal": {...},
                    "deliberated_at": "2025-12-02T10:30:00Z"
                },
                ...
            ]
        }

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
        """
        # Query Neo4j for all deliberations (rehydratable)
        deliberations = await self.storage.get_agent_deliberations(
            ceremony_id=ceremony_id,
            story_id=story_id,
        )

        if not deliberations:
            logger.warning(
                f"No deliberations found for ceremony {ceremony_id.value}, "
                f"story {story_id.value}"
            )
            return

        # Serialize deliberations to dict
        agent_deliberations = []
        for d in deliberations:
            # Convert proposal to JSON string if dict
            import json as json_module

            if isinstance(d.proposal, dict):
                proposal_str = json_module.dumps(d.proposal)
            else:
                proposal_str = str(d.proposal)

            agent_deliberations.append(
                {
                    "agent_id": d.agent_id,
                    "role": d.role.value,
                    "proposal": proposal_str,
                    "deliberated_at": d.deliberated_at.isoformat(),
                }
            )

        # Build event payload
        payload = {
            "ceremony_id": ceremony_id.value,
            "story_id": story_id.value,
            "agent_deliberations": agent_deliberations,
        }

        await self.messaging.publish_event(
            subject=str(NATSSubject.DELIBERATIONS_COMPLETE),
            payload=payload,
        )

        logger.info(
            f"✅ Published deliberations complete event for story {story_id.value} "
            f"in ceremony {ceremony_id.value} with {len(agent_deliberations)} deliberations"
        )
