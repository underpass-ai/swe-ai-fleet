"""Unit tests for StartBacklogReviewCeremonyUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from planning.application.ports import MessagingPort, OrchestratorPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
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
    def orchestrator_port(self) -> OrchestratorPort:
        """Fixture providing mock OrchestratorPort."""
        mock = AsyncMock(spec=OrchestratorPort)
        # deliberate() returns ACK response immediately
        mock.deliberate = AsyncMock()
        return mock

    @pytest.fixture
    def use_case(
        self,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        orchestrator_port: OrchestratorPort,
    ) -> StartBacklogReviewCeremonyUseCase:
        """Fixture providing the use case."""
        return StartBacklogReviewCeremonyUseCase(
            storage=storage_port,
            messaging=messaging_port,
            orchestrator=orchestrator_port,
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
        orchestrator_port: OrchestratorPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test successfully starting ceremony."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        started_by = UserName("po@example.com")

        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        result = await use_case.execute(ceremony_id, started_by)

        # Verify ceremony is IN_PROGRESS (results arrive async via NATS)
        assert result.status.is_in_progress()
        assert result.started_at is not None

        # Verify Orchestrator.deliberate() called for each story × council
        # 2 stories × 3 councils = 6 deliberations
        assert orchestrator_port.deliberate.await_count == 6

        # Verify storage called once (ceremony started)
        assert storage_port.save_backlog_review_ceremony.await_count == 1

        # Verify event published
        messaging_port.publish.assert_awaited()

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
        orchestrator_port: OrchestratorPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test that if one deliberation fails, others still submitted."""
        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        # Some deliberation calls fail, others succeed
        orchestrator_port.deliberate.side_effect = [
            None,  # Success (ACK)
            None,  # Success (ACK)
            Exception("Orchestrator timeout"),  # Fail
            None,  # Success (ACK)
            None,  # Success (ACK)
            None,  # Success (ACK)
        ]

        result = await use_case.execute(
            BacklogReviewCeremonyId("BRC-12345"),
            UserName("po@example.com")
        )

        # Should still transition to IN_PROGRESS (partial failure tolerated)
        assert result.status.is_in_progress()

        # Deliberate attempted for all 6 (2 stories × 3 councils)
        assert orchestrator_port.deliberate.await_count == 6

    @pytest.mark.asyncio
    async def test_event_published_on_completion(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        orchestrator_port: OrchestratorPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test that started event is published."""
        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        await use_case.execute(
            BacklogReviewCeremonyId("BRC-12345"),
            UserName("po@example.com")
        )

        # Verify event published (ceremony.started event, status IN_PROGRESS)
        messaging_port.publish.assert_awaited_once()
        call_args = messaging_port.publish.call_args
        assert call_args[1]["subject"] == "planning.backlog_review.ceremony.started"
        assert call_args[1]["payload"]["status"] == "IN_PROGRESS"

