"""Unit tests for ApproveReviewPlanUseCase and RejectReviewPlanUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.application.usecases.approve_review_plan_usecase import (
    ApproveReviewPlanUseCase,
)
from planning.application.usecases.reject_review_plan_usecase import (
    RejectReviewPlanUseCase,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_approval import PlanApproval
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)


class TestApproveReviewPlanUseCase:
    """Test suite for ApproveReviewPlanUseCase."""

    @pytest.fixture
    def storage_port(self) -> StoragePort:
        """Fixture providing mock StoragePort."""
        mock = AsyncMock(spec=StoragePort)
        mock.save_plan = AsyncMock()
        mock.save_backlog_review_ceremony = AsyncMock()
        mock.save_task_with_decision = AsyncMock()
        return mock

    @pytest.fixture
    def messaging_port(self) -> MessagingPort:
        """Fixture providing mock MessagingPort."""
        mock = AsyncMock(spec=MessagingPort)
        mock.publish_event = AsyncMock()
        return mock

    @pytest.fixture
    def use_case(
        self,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> ApproveReviewPlanUseCase:
        """Fixture providing the use case."""
        return ApproveReviewPlanUseCase(
            storage=storage_port,
            messaging=messaging_port,
        )

    @pytest.fixture
    def ceremony_with_review_result(self) -> BacklogReviewCeremony:
        """Fixture providing ceremony with pending review result."""
        review_result = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=PlanPreliminary(
                title=Title("Auth Plan"),
                description=Brief("Implement authentication"),
                acceptance_criteria=("User can login",),
                technical_notes="Use JWT",
                roles=("DEVELOPER", "QA"),
                estimated_complexity="MEDIUM",
                dependencies=("Redis",),
                tasks_outline=("Setup JWT", "Implement registration"),
            ),
            architect_feedback="Good",
            qa_feedback="Good",
            devops_feedback="Good",
            recommendations=("Add error handling",),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            review_results=(review_result,),
        )

    @pytest.mark.asyncio
    async def test_approve_plan_success(
        self,
        use_case: ApproveReviewPlanUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        ceremony_with_review_result: BacklogReviewCeremony,
    ) -> None:
        """Test successfully approving a plan."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        story_id = StoryId("ST-001")

        # Create PlanApproval value object
        approval = PlanApproval(
            approved_by=UserName("po@example.com"),
            po_notes="Approved because critical for MVP launch",
            po_concerns="Monitor timeline closely",
            priority_adjustment="HIGH",
            po_priority_reason="Authentication blocks other user features",
        )

        storage_port.get_backlog_review_ceremony.return_value = ceremony_with_review_result

        plan, updated_ceremony = await use_case.execute(
            ceremony_id,
            story_id,
            approval,
        )

        # Verify Plan created
        assert plan.plan_id.value.startswith("PL-")
        assert story_id in plan.story_ids

        # Verify ceremony returned
        assert updated_ceremony.ceremony_id == ceremony_id

        # Verify Plan saved
        storage_port.save_plan.assert_awaited_once()

        # Verify ceremony updated
        storage_port.save_backlog_review_ceremony.assert_awaited_once()

        # Verify that updated ceremony has plan_id in review_result
        saved_ceremony = storage_port.save_backlog_review_ceremony.call_args[0][0]
        assert isinstance(saved_ceremony, BacklogReviewCeremony)
        assert len(saved_ceremony.review_results) == 1
        approved_review_result = saved_ceremony.review_results[0]
        assert approved_review_result.plan_id == plan.plan_id
        assert approved_review_result.approval_status.is_approved()

        # Verify event published
        messaging_port.publish_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ceremony_not_found_raises(
        self,
        use_case: ApproveReviewPlanUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that non-existent ceremony raises error."""
        storage_port.get_backlog_review_ceremony.return_value = None

        approval = PlanApproval(
            approved_by=UserName("po@example.com"),
            po_notes="Approved",
        )

        with pytest.raises(CeremonyNotFoundError):
            await use_case.execute(
                BacklogReviewCeremonyId("BRC-99999"),
                StoryId("ST-001"),
                approval,
            )

    @pytest.mark.asyncio
    async def test_story_not_in_ceremony_raises(
        self,
        use_case: ApproveReviewPlanUseCase,
        storage_port: StoragePort,
        ceremony_with_review_result: BacklogReviewCeremony,
    ) -> None:
        """Test that approving non-existent story raises error."""
        storage_port.get_backlog_review_ceremony.return_value = ceremony_with_review_result

        approval = PlanApproval(
            approved_by=UserName("po@example.com"),
            po_notes="Approved",
        )

        with pytest.raises(ValueError, match="No review result found"):
            await use_case.execute(
                BacklogReviewCeremonyId("BRC-12345"),
                StoryId("ST-999"),  # Not in ceremony!
                approval,
            )


class TestRejectReviewPlanUseCase:
    """Test suite for RejectReviewPlanUseCase."""

    @pytest.fixture
    def storage_port(self) -> StoragePort:
        """Fixture providing mock StoragePort."""
        mock = AsyncMock(spec=StoragePort)
        mock.save_backlog_review_ceremony = AsyncMock()
        return mock

    @pytest.fixture
    def messaging_port(self) -> MessagingPort:
        """Fixture providing mock MessagingPort."""
        mock = AsyncMock(spec=MessagingPort)
        mock.publish_event = AsyncMock()
        return mock

    @pytest.fixture
    def use_case(
        self,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> RejectReviewPlanUseCase:
        """Fixture providing the use case."""
        return RejectReviewPlanUseCase(
            storage=storage_port,
            messaging=messaging_port,
        )

    @pytest.fixture
    def ceremony_with_review_result(self) -> BacklogReviewCeremony:
        """Fixture providing ceremony with pending review result."""
        review_result = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=PlanPreliminary(
                title=Title("Plan"),
                description=Brief("Description"),
                acceptance_criteria=("Criterion",),
                technical_notes="Notes",
                roles=("DEVELOPER",),
                estimated_complexity="LOW",
                dependencies=(),
            ),
            architect_feedback="Good",
            qa_feedback="Good",
            devops_feedback="Good",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            review_results=(review_result,),
        )

    @pytest.mark.asyncio
    async def test_reject_plan_success(
        self,
        use_case: RejectReviewPlanUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        ceremony_with_review_result: BacklogReviewCeremony,
    ) -> None:
        """Test successfully rejecting a plan."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        story_id = StoryId("ST-001")
        rejected_by = UserName("po@example.com")

        storage_port.get_backlog_review_ceremony.return_value = ceremony_with_review_result

        result = await use_case.execute(
            ceremony_id,
            story_id,
            rejected_by,
            "Needs more details"
        )

        # Verify ceremony updated
        assert result.ceremony_id == ceremony_id
        storage_port.save_backlog_review_ceremony.assert_awaited_once()

        # Verify event published
        messaging_port.publish_event.assert_awaited_once()

