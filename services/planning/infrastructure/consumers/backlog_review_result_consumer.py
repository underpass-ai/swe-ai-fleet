"""BacklogReviewResultConsumer - Async consumer for story review results.

Infrastructure Layer (Consumer):
- Subscribes to: planning.backlog_review.story.reviewed (from Orchestrator)
- Updates BacklogReviewCeremony with review results
- Transitions ceremony to REVIEWING when all stories completed

Following Event-Driven Architecture:
- NATS JetStream durable pull subscription
- Orchestrator publishes story.reviewed after deliberations
- Planning consumes and updates ceremony state
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from nats.aio.client import Client
from nats.js import JetStreamContext
from planning.application.ports import MessagingPort, StoragePort
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.nats_stream import NATSStream
from planning.domain.value_objects.nats_subject import NATSSubject
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title

logger = logging.getLogger(__name__)


@dataclass
class BacklogReviewResultConsumer:
    """
    NATS consumer for backlog review story review results.

    Responsibilities:
    - Subscribe to planning.backlog_review.story.reviewed events
    - Update ceremony with StoryReviewResult
    - Transition ceremony to REVIEWING when all stories reviewed
    - Publish ceremony completion events

    Following Hexagonal Architecture:
    - Uses StoragePort (not concrete adapter)
    - Uses MessagingPort (not NATS directly)
    - Domain-driven design with ValueObjects
    """

    nats_client: Client
    jetstream: JetStreamContext
    storage: StoragePort
    messaging: MessagingPort

    def __post_init__(self) -> None:
        """Initialize consumer state."""
        self._subscription = None
        self._polling_task = None

    async def start(self) -> None:
        """Start consuming review result events.

        Uses PULL subscription for reliability and load balancing.
        """
        try:
            # Create PULL subscription (durable)
            self._subscription = await self.jetstream.pull_subscribe(
                subject=str(NATSSubject.BACKLOG_REVIEW_STORY_REVIEWED),
                durable="planning-backlog-review-results",
                stream=str(NATSStream.PLANNING_EVENTS),
            )

            logger.info("✓ BacklogReviewResultConsumer: subscription created (DURABLE)")

            # Start background polling task
            self._polling_task = asyncio.create_task(self._poll_messages())

        except Exception as e:
            logger.error(
                f"Failed to start BacklogReviewResultConsumer: {e}", exc_info=True
            )
            raise

    async def stop(self) -> None:
        """Stop the consumer gracefully."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

        logger.info("✓ BacklogReviewResultConsumer stopped")

    async def _poll_messages(self) -> None:
        """Poll for messages continuously."""
        logger.info("🔄 BacklogReviewResultConsumer: polling started")

        while True:
            try:
                # Fetch messages (batch=1, timeout=5s)
                msgs = await self._subscription.fetch(batch=1, timeout=5)

                for msg in msgs:
                    await self._handle_message(msg)

            except TimeoutError:
                # No messages available - continue polling
                continue

            except Exception as e:
                logger.error(f"Error polling messages: {e}", exc_info=True)
                await asyncio.sleep(5)  # Backoff on error

    async def _handle_message(self, msg) -> None:
        """
        Handle agent.response.completed event.

        Event payload (AgentResult from Ray Workers):
        {
            "task_id": "ceremony-abc:story-ST-123:role-ARCHITECT",
            "agent_id": "ARCHITECT-agent-1",
            "role": "ARCHITECT",
            "proposal": "Technical feedback...",
            "operations": null,
            "duration_ms": 45000,
            "is_success": true,
            "error_message": null,
            "model": "Qwen/Qwen3-0.6B",
            "timestamp": "2025-12-02T10:30:00Z"
        }
        """
        try:
            data = json.loads(msg.data.decode())

            # Validate success
            if not data.get("is_success", False):
                logger.warning(f"Skipping failed agent result: {data.get('error_message')}")
                await msg.ack()  # ACK para no reintentar
                return

            # Extract metadata from task_id
            # Format: "ceremony-abc123:story-ST-456:role-ARCHITECT"
            task_id = data["task_id"]
            ceremony_id, story_id, role = self._parse_task_id(task_id)

            if not ceremony_id or not story_id:
                logger.error(f"Invalid task_id format: {task_id}")
                await msg.nak()
                return

            reviewed_at = datetime.fromisoformat(data["timestamp"])

            logger.info(
                f"📥 Received review result: "
                f"ceremony={ceremony_id.value}, story={story_id.value}"
            )

            # Retrieve ceremony
            ceremony = await self.storage.get_backlog_review_ceremony(ceremony_id)

            if not ceremony:
                logger.warning(f"Ceremony {ceremony_id.value} not found - skipping")
                await msg.ack()  # ACK to avoid infinite retry
                return

            # Build or update StoryReviewResult for this role
            # Note: We receive 3 separate events (ARCHITECT, QA, DEVOPS)
            # We need to accumulate feedback from all roles
            review_result = self._build_or_update_review_result(
                ceremony=ceremony,
                story_id=story_id,
                role=role,
                feedback=data["proposal"],
                duration_ms=data["duration_ms"],
                reviewed_at=reviewed_at,
            )

            # Update ceremony with review result
            ceremony = ceremony.update_review_result(
                story_id=story_id,
                review_result=review_result,
                updated_at=datetime.now(UTC),
            )

            # Check if all stories are reviewed
            if self._all_stories_reviewed(ceremony):
                # Transition to REVIEWING (awaiting PO approval)
                ceremony = ceremony.mark_reviewing(
                    ceremony.review_results, datetime.now(UTC)
                )
                logger.info(
                    f"✅ Ceremony {ceremony_id.value} → REVIEWING "
                    f"({len(ceremony.review_results)}/{len(ceremony.story_ids)} stories)"
                )

                # Publish completion event
                await self._publish_ceremony_completed(ceremony)

            # Persist ceremony
            await self.storage.save_backlog_review_ceremony(ceremony)

            # ACK message
            await msg.ack()

            logger.info(
                f"✓ Ceremony {ceremony_id.value} updated with review for {story_id.value}"
            )

        except Exception as e:
            logger.error(f"Failed to handle review result: {e}", exc_info=True)
            await msg.nak()  # NACK = will retry

    def _parse_task_id(self, task_id: str) -> tuple[BacklogReviewCeremonyId | None, StoryId | None, str | None]:
        """
        Parse task_id to extract ceremony_id, story_id, and role.

        Expected format: "ceremony-{id}:story-{id}:role-{role}"
        Example: "ceremony-abc123:story-ST-456:role-ARCHITECT"

        Returns:
            Tuple of (ceremony_id, story_id, role) or (None, None, None) if invalid
        """
        try:
            parts = task_id.split(":")
            if len(parts) != 3:
                return (None, None, None)

            ceremony_part = parts[0]  # "ceremony-abc123"
            story_part = parts[1]     # "story-ST-456"
            role_part = parts[2]      # "role-ARCHITECT"

            ceremony_id_str = ceremony_part.replace("ceremony-", "")
            story_id_str = story_part.replace("story-", "")
            role = role_part.replace("role-", "")

            return (
                BacklogReviewCeremonyId(ceremony_id_str),
                StoryId(story_id_str),
                role,
            )

        except Exception as e:
            logger.warning(f"Failed to parse task_id '{task_id}': {e}")
            return (None, None, None)

    def _build_or_update_review_result(
        self,
        ceremony,
        story_id: StoryId,
        role: str,
        feedback: str,
        duration_ms: int,
        reviewed_at: datetime,
    ) -> StoryReviewResult:
        """
        Build or update StoryReviewResult for a story.

        Since we receive 3 separate events (ARCHITECT, QA, DEVOPS),
        we need to accumulate feedback from all roles.

        Args:
            ceremony: Current ceremony state
            story_id: Story being reviewed
            role: Role that provided feedback (ARCHITECT, QA, DEVOPS)
            feedback: Feedback text from this role
            duration_ms: Duration of deliberation
            reviewed_at: Timestamp

        Returns:
            Updated StoryReviewResult with feedback from this role
        """
        # Find existing review result for this story
        existing_result = None
        for result in ceremony.review_results:
            if result.story_id == story_id:
                existing_result = result
                break

        # Extract tasks from feedback (simple parsing)
        tasks_outline = self._extract_tasks_from_feedback(feedback)

        if existing_result:
            # Update existing result with new role feedback
            architect_feedback = existing_result.architect_feedback
            qa_feedback = existing_result.qa_feedback
            devops_feedback = existing_result.devops_feedback

            if role == "ARCHITECT":
                architect_feedback = feedback
            elif role == "QA":
                qa_feedback = feedback
            elif role == "DEVOPS":
                devops_feedback = feedback

            # Merge tasks_outline
            existing_tasks = list(existing_result.plan_preliminary.tasks_outline)
            merged_tasks = tuple(set(existing_tasks + list(tasks_outline)))

            # Update PlanPreliminary
            plan_preliminary = PlanPreliminary(
                title=existing_result.plan_preliminary.title,
                description=existing_result.plan_preliminary.description,
                acceptance_criteria=existing_result.plan_preliminary.acceptance_criteria,
                technical_notes=existing_result.plan_preliminary.technical_notes,
                roles=existing_result.plan_preliminary.roles + (role,) if role not in existing_result.plan_preliminary.roles else existing_result.plan_preliminary.roles,
                estimated_complexity=existing_result.plan_preliminary.estimated_complexity,
                dependencies=existing_result.plan_preliminary.dependencies,
                tasks_outline=merged_tasks,
            )

            return StoryReviewResult(
                story_id=story_id,
                plan_preliminary=plan_preliminary,
                architect_feedback=architect_feedback,
                qa_feedback=qa_feedback,
                devops_feedback=devops_feedback,
                recommendations=existing_result.recommendations,
                approval_status=existing_result.approval_status,
                reviewed_at=reviewed_at,
                approved_by=existing_result.approved_by,
                approved_at=existing_result.approved_at,
                rejected_by=existing_result.rejected_by,
                rejected_at=existing_result.rejected_at,
                rejection_reason=existing_result.rejection_reason,
            )

        else:
            # Create new review result
            architect_feedback = feedback if role == "ARCHITECT" else ""
            qa_feedback = feedback if role == "QA" else ""
            devops_feedback = feedback if role == "DEVOPS" else ""

            plan_preliminary = PlanPreliminary(
                title=Title(f"Plan for {story_id.value}"),
                description=Brief("Generated from council reviews"),
                acceptance_criteria=("Review completed by councils",),
                technical_notes=feedback,
                roles=(role,),
                estimated_complexity="MEDIUM",
                dependencies=(),
                tasks_outline=tasks_outline,
            )

            return StoryReviewResult(
                story_id=story_id,
                plan_preliminary=plan_preliminary,
                architect_feedback=architect_feedback,
                qa_feedback=qa_feedback,
                devops_feedback=devops_feedback,
                recommendations=(),
                approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
                reviewed_at=reviewed_at,
                approved_by=None,
                approved_at=None,
                rejected_by=None,
                rejected_at=None,
                rejection_reason=None,
            )

    def _extract_tasks_from_feedback(self, feedback: str) -> tuple[str, ...]:
        """
        Extract high-level tasks from feedback text.

        Simple parsing for MVP. Future: Use regex or LLM parser.

        Args:
            feedback: Feedback text from council

        Returns:
            Tuple of task strings
        """
        # TODO: Implement intelligent parsing (regex/LLM)
        # For now, return placeholder based on feedback presence
        if not feedback or not feedback.strip():
            return ()

        # Simple heuristic: look for numbered lists or bullet points
        import re

        # Pattern 1: "1. Task description"
        numbered_tasks = re.findall(r"^\d+\.\s+(.+)$", feedback, re.MULTILINE)

        # Pattern 2: "- Task description"
        bullet_tasks = re.findall(r"^[-*]\s+(.+)$", feedback, re.MULTILINE)

        tasks = numbered_tasks + bullet_tasks

        return tuple(tasks[:10])  # Limit to 10 tasks

    def _build_review_result(
        self, story_id: StoryId, review_results_data: list[dict], reviewed_at: datetime
    ) -> StoryReviewResult:
        """
        Build StoryReviewResult from event data.

        Consolidates feedback from multiple roles (ARCHITECT, QA, DEVOPS)
        into a single PlanPreliminary with tasks_outline.
        """
        # Extract tasks from all roles
        tasks_outline = []
        feedbacks = []

        for review in review_results_data:
            role = review["role"]
            feedbacks.append(f"{role}: {review['winner_content']}")

            # Extract tasks if present
            if "tasks_outline" in review:
                tasks_outline.extend(review["tasks_outline"])

        # Build PlanPreliminary
        plan_preliminary = PlanPreliminary(
            title=Title(f"Plan for {story_id.value}"),
            description=Brief("Generated from council reviews"),
            acceptance_criteria=("Review completed by councils",),
            technical_notes="\n\n".join(feedbacks),
            roles=tuple(r["role"] for r in review_results_data),
            estimated_complexity="MEDIUM",  # TODO: Extract from feedbacks
            dependencies=(),  # TODO: Extract from feedbacks
            tasks_outline=tuple(tasks_outline),
        )

        # Build StoryReviewResult
        return StoryReviewResult(
            story_id=story_id,
            plan_preliminary=plan_preliminary,
            architect_feedback=self._get_feedback_for_role(review_results_data, "ARCHITECT"),
            qa_feedback=self._get_feedback_for_role(review_results_data, "QA"),
            devops_feedback=self._get_feedback_for_role(review_results_data, "DEVOPS"),
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=reviewed_at,
            approved_by=None,
            approved_at=None,
            rejected_by=None,
            rejected_at=None,
            rejection_reason=None,
        )

    def _get_feedback_for_role(
        self, review_results_data: list[dict], role: str
    ) -> str:
        """Extract feedback for a specific role."""
        for review in review_results_data:
            if review["role"] == role:
                return review.get("winner_content", "No feedback provided")
        return "No feedback provided"

    def _all_stories_reviewed(self, ceremony) -> bool:
        """Check if all stories have review results."""
        reviewed_story_ids = {r.story_id for r in ceremony.review_results}
        return set(ceremony.story_ids) == reviewed_story_ids

    async def _publish_ceremony_completed(self, ceremony) -> None:
        """Publish ceremony completion event."""
        try:
            await self.messaging.publish(
                subject=str(NATSSubject.BACKLOG_REVIEW_CEREMONY_COMPLETED),
                payload={
                    "ceremony_id": ceremony.ceremony_id.value,
                    "status": "REVIEWING",
                    "total_stories": len(ceremony.story_ids),
                    "reviewed_stories": len(ceremony.review_results),
                    "updated_at": ceremony.updated_at.isoformat(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to publish ceremony.completed event: {e}")

