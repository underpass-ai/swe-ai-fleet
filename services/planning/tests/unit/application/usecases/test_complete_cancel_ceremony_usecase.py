"""Unit tests for Complete and Cancel ceremony use cases."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.application.usecases.cancel_backlog_review_ceremony_usecase import (
    CancelBacklogReviewCeremonyUseCase,
)
from planning.application.usecases.complete_backlog_review_ceremony_usecase import (
    CompleteBacklogReviewCeremonyUseCase,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
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


class TestCompleteBacklogReviewCeremonyUseCase:
    """Test suite for CompleteBacklogReviewCeremonyUseCase."""

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
        mock.publish = AsyncMock()
        return mock

    @pytest.fixture
    def use_case(
        self,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> CompleteBacklogReviewCeremonyUseCase:
        """Fixture providing the use case."""
        return CompleteBacklogReviewCeremonyUseCase(
            storage=storage_port,
            messaging=messaging_port,
        )

    @pytest.fixture
    def reviewing_ceremony_all_approved(self) -> BacklogReviewCeremony:
        """Fixture providing ceremony with all reviews approved."""
        approved_result = StoryReviewResult(
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
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED),
            reviewed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            approved_by=UserName("po@example.com"),
            approved_at=datetime(2025, 12, 2, 13, 0, 0, tzinfo=UTC),
        )

        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            review_results=(approved_result,),
        )

    @pytest.mark.asyncio
    async def test_complete_ceremony_success(
        self,
        use_case: CompleteBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        reviewing_ceremony_all_approved: BacklogReviewCeremony,
    ) -> None:
        """Test successfully completing ceremony."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")

        storage_port.get_backlog_review_ceremony.return_value = reviewing_ceremony_all_approved

        result = await use_case.execute(ceremony_id)

        assert result.status.is_completed()
        assert result.completed_at is not None
        storage_port.save_backlog_review_ceremony.assert_awaited_once()
        messaging_port.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_with_pending_reviews_raises(
        self,
        use_case: CompleteBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that completing with pending reviews raises error."""
        pending_result = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=None,
            architect_feedback="Good",
            qa_feedback="Good",
            devops_feedback="Good",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        ceremony_with_pending = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            review_results=(pending_result,),
        )

        storage_port.get_backlog_review_ceremony.return_value = ceremony_with_pending

        with pytest.raises(ValueError, match="still has pending approval"):
            await use_case.execute(BacklogReviewCeremonyId("BRC-12345"))


class TestCancelBacklogReviewCeremonyUseCase:
    """Test suite for CancelBacklogReviewCeremonyUseCase."""

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
        mock.publish = AsyncMock()
        return mock

    @pytest.fixture
    def use_case(
        self,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> CancelBacklogReviewCeremonyUseCase:
        """Fixture providing the use case."""
        return CancelBacklogReviewCeremonyUseCase(
            storage=storage_port,
            messaging=messaging_port,
        )

    @pytest.fixture
    def draft_ceremony(self) -> BacklogReviewCeremony:
        """Fixture providing draft ceremony."""
        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_cancel_ceremony_success(
        self,
        use_case: CancelBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        draft_ceremony: BacklogReviewCeremony,
    ) -> None:
        """Test successfully cancelling ceremony."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")

        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony

        result = await use_case.execute(ceremony_id)

        assert result.status.is_cancelled()
        storage_port.save_backlog_review_ceremony.assert_awaited_once()
        messaging_port.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ceremony_not_found_raises(
        self,
        use_case: CancelBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that non-existent ceremony raises error."""
        storage_port.get_backlog_review_ceremony.return_value = None

        with pytest.raises(CeremonyNotFoundError):
            await use_case.execute(BacklogReviewCeremonyId("BRC-99999"))

