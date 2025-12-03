"""Unit tests for StartBacklogReviewCeremonyUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.application.usecases.review_story_with_councils_usecase import (
    ReviewStoryWithCouncilsUseCase,
)
from planning.application.usecases.start_backlog_review_ceremony_usecase import (
    StartBacklogReviewCeremonyUseCase,
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


class TestStartBacklogReviewCeremonyUseCase:
    """Test suite for StartBacklogReviewCeremonyUseCase."""

    @pytest.fixture
    def storage_port(self) -> StoragePort:
        """Fixture providing mock StoragePort."""
        return AsyncMock(spec=StoragePort)

    @pytest.fixture
    def messaging_port(self) -> MessagingPort:
        """Fixture providing mock MessagingPort."""
        mock = AsyncMock(spec=MessagingPort)
        mock.publish = AsyncMock()
        return mock

    @pytest.fixture
    def review_story_use_case(self) -> ReviewStoryWithCouncilsUseCase:
        """Fixture providing mock ReviewStoryWithCouncilsUseCase."""
        mock = AsyncMock(spec=ReviewStoryWithCouncilsUseCase)

        # Return a valid StoryReviewResult
        mock.execute.return_value = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=PlanPreliminary(
                title=Title("Plan"),
                description=Brief("Description"),
                acceptance_criteria=("Criterion",),
                technical_notes="Notes",
                roles=("DEVELOPER",),
                estimated_complexity="MEDIUM",
                dependencies=(),
            ),
            architect_feedback="Good architecture",
            qa_feedback="Good testability",
            devops_feedback="Good infrastructure",
            recommendations=("Add error handling",),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        return mock

    @pytest.fixture
    def use_case(
        self,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        review_story_use_case: ReviewStoryWithCouncilsUseCase,
    ) -> StartBacklogReviewCeremonyUseCase:
        """Fixture providing the use case."""
        return StartBacklogReviewCeremonyUseCase(
            storage=storage_port,
            messaging=messaging_port,
            review_story_use_case=review_story_use_case,
        )

    @pytest.fixture
    def draft_ceremony_with_stories(self) -> BacklogReviewCeremony:
        """Fixture providing draft ceremony with stories."""
        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"), StoryId("ST-002")),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_start_ceremony_success(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        review_story_use_case: ReviewStoryWithCouncilsUseCase,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test successfully starting ceremony."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        started_by = UserName("po@example.com")

        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        result = await use_case.execute(ceremony_id, started_by)

        # Verify ceremony is REVIEWING
        assert result.status.is_reviewing()
        assert result.started_at is not None

        # Verify review_story called for each story
        assert review_story_use_case.execute.await_count == 2

        # Verify results collected
        assert len(result.review_results) == 2

        # Verify storage called (2 times: start + mark_reviewing)
        assert storage_port.save_backlog_review_ceremony.await_count == 2

    @pytest.mark.asyncio
    async def test_ceremony_not_found_raises(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that non-existent ceremony raises error."""
        ceremony_id = BacklogReviewCeremonyId("BRC-99999")
        storage_port.get_backlog_review_ceremony.return_value = None

        with pytest.raises(CeremonyNotFoundError):
            await use_case.execute(ceremony_id, UserName("po@example.com"))

    @pytest.mark.asyncio
    async def test_ceremony_not_draft_raises(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that starting non-draft ceremony raises error."""
        in_progress_ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

        storage_port.get_backlog_review_ceremony.return_value = in_progress_ceremony

        with pytest.raises(ValueError, match="Cannot start ceremony in status"):
            await use_case.execute(
                BacklogReviewCeremonyId("BRC-12345"),
                UserName("po@example.com")
            )

    @pytest.mark.asyncio
    async def test_ceremony_without_stories_raises(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that ceremony without stories raises error."""
        empty_ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(),  # Empty!
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

        storage_port.get_backlog_review_ceremony.return_value = empty_ceremony

        with pytest.raises(ValueError, match="No stories to review"):
            await use_case.execute(
                BacklogReviewCeremonyId("BRC-12345"),
                UserName("po@example.com")
            )

    @pytest.mark.asyncio
    async def test_partial_failure_continues_with_other_stories(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        review_story_use_case: ReviewStoryWithCouncilsUseCase,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test that if one story fails, others still processed."""
        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        # First story succeeds, second fails
        review_story_use_case.execute.side_effect = [
            StoryReviewResult(
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
            ),
            Exception("Orchestrator timeout"),  # Second story fails
        ]

        result = await use_case.execute(
            BacklogReviewCeremonyId("BRC-12345"),
            UserName("po@example.com")
        )

        # Should still complete with 1 result
        assert result.status.is_reviewing()
        assert len(result.review_results) == 1  # Only successful one

    @pytest.mark.asyncio
    async def test_event_published_on_completion(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test that completion event is published."""
        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        await use_case.execute(
            BacklogReviewCeremonyId("BRC-12345"),
            UserName("po@example.com")
        )

        # Verify event published
        messaging_port.publish.assert_awaited_once()
        call_args = messaging_port.publish.call_args
        assert call_args[1]["subject"] == "planning.backlog_review.completed"
        assert call_args[1]["payload"]["status"] == "REVIEWING"

