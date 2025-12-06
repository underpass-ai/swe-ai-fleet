"""Unit tests for StartBacklogReviewCeremonyUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.ports import (
    ContextPort,
    MessagingPort,
    OrchestratorPort,
    StoragePort,
)
from planning.application.ports.context_port import ContextResponse
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.application.usecases.start_backlog_review_ceremony_usecase import (
    StartBacklogReviewCeremonyUseCase,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.deliberation_id import DeliberationId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
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
        mock.publish_ceremony_started = AsyncMock()
        return mock

    @pytest.fixture
    def orchestrator_port(self) -> OrchestratorPort:
        """Fixture providing mock OrchestratorPort."""
        mock = AsyncMock(spec=OrchestratorPort)
        # deliberate() returns ACK response immediately
        mock.deliberate = AsyncMock()
        return mock

    @pytest.fixture
    def context_port(self) -> ContextPort:
        """Fixture providing mock ContextPort."""
        mock = AsyncMock(spec=ContextPort)
        # get_context() returns ContextResponse with context string
        mock.get_context = AsyncMock(
            return_value=ContextResponse(
                context="Story context: Test story details and plan information.",
                token_count=150,
                scopes=("story", "plan"),
                version="v1.0",
            )
        )
        return mock

    @pytest.fixture
    def use_case(
        self,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        orchestrator_port: OrchestratorPort,
        context_port: ContextPort,
    ) -> StartBacklogReviewCeremonyUseCase:
        """Fixture providing the use case."""
        return StartBacklogReviewCeremonyUseCase(
            storage=storage_port,
            messaging=messaging_port,
            orchestrator=orchestrator_port,
            context=context_port,
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
        context_port: ContextPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test successfully starting ceremony."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        started_by = UserName("po@example.com")

        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        ceremony, total_deliberations = await use_case.execute(ceremony_id, started_by)

        # Verify ceremony is IN_PROGRESS (results arrive async via NATS)
        assert ceremony.status.is_in_progress()
        assert ceremony.started_at is not None

        # Verify deliberations count
        assert total_deliberations == 6  # 2 stories × 3 councils = 6

        # Verify Context.get_context() called for each story × role
        assert context_port.get_context.await_count == 6  # 2 stories × 3 roles

        # Verify Orchestrator.deliberate() called for each story × council
        assert orchestrator_port.deliberate.await_count == 6

        # Verify storage called once (ceremony started)
        assert storage_port.save_backlog_review_ceremony.await_count == 1

        # Verify event published
        messaging_port.publish_ceremony_started.assert_awaited_once()

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
        context_port: ContextPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test that if one deliberation fails, others still submitted."""
        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        # Some deliberation calls fail, others succeed
        orchestrator_port.deliberate.side_effect = [
            DeliberationId("delib-001"),  # Success (ACK)
            DeliberationId("delib-002"),  # Success (ACK)
            Exception("Orchestrator timeout"),  # Fail
            DeliberationId("delib-003"),  # Success (ACK)
            DeliberationId("delib-004"),  # Success (ACK)
            DeliberationId("delib-005"),  # Success (ACK)
        ]

        ceremony, total_deliberations = await use_case.execute(
            BacklogReviewCeremonyId("BRC-12345"),
            UserName("po@example.com")
        )

        # Should still transition to IN_PROGRESS (partial failure tolerated)
        assert ceremony.status.is_in_progress()

        # Only 5 deliberations succeeded (1 failed)
        assert total_deliberations == 5

        # Context should still be fetched for all 6 (2 stories × 3 councils)
        assert context_port.get_context.await_count == 6

        # Deliberate attempted for all 6 (2 stories × 3 councils)
        assert orchestrator_port.deliberate.await_count == 6

    @pytest.mark.asyncio
    async def test_context_retrieval_failure_continues_with_basic_description(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        orchestrator_port: OrchestratorPort,
        context_port: ContextPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test that if context retrieval fails, ceremony continues with basic description."""
        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        # Context retrieval fails for all calls
        context_port.get_context.side_effect = Exception("Context Service unavailable")

        ceremony, total_deliberations = await use_case.execute(
            BacklogReviewCeremonyId("BRC-12345"),
            UserName("po@example.com")
        )

        # Should still transition to IN_PROGRESS
        assert ceremony.status.is_in_progress()

        # All 6 deliberations should still be submitted (with basic description)
        assert total_deliberations == 6

        # Context retrieval attempted for all 6
        assert context_port.get_context.await_count == 6

        # Deliberate called for all 6 (with fallback descriptions)
        assert orchestrator_port.deliberate.await_count == 6

    @pytest.mark.asyncio
    async def test_event_published_on_completion(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        orchestrator_port: OrchestratorPort,
        context_port: ContextPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test that started event is published."""
        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        await use_case.execute(
            BacklogReviewCeremonyId("BRC-12345"),
            UserName("po@example.com")
        )

        # Verify event published (ceremony.started event, status IN_PROGRESS)
        messaging_port.publish_ceremony_started.assert_awaited_once()
        call_args = messaging_port.publish_ceremony_started.call_args
        assert call_args.kwargs["status"].is_in_progress()
        assert call_args.kwargs["total_stories"] == 2
        assert call_args.kwargs["deliberations_submitted"] == 6
        assert call_args.kwargs["ceremony_id"].value == "BRC-12345"
        assert call_args.kwargs["started_by"].value == "po@example.com"
        assert call_args.kwargs["started_at"] is not None

    @pytest.mark.asyncio
    async def test_event_publish_failure_does_not_raise(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        orchestrator_port: OrchestratorPort,
        context_port: ContextPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test that event publish failure is logged but does not raise."""
        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories
        messaging_port.publish_ceremony_started.side_effect = Exception("NATS error")

        # Should not raise, just log warning
        ceremony, total_deliberations = await use_case.execute(
            BacklogReviewCeremonyId("BRC-12345"),
            UserName("po@example.com")
        )

        # Ceremony should still be started successfully
        assert ceremony.status.is_in_progress()
        assert total_deliberations == 6

    @pytest.mark.asyncio
    async def test_uses_token_budget_standard(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        context_port: ContextPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test that TokenBudget.STANDARD is used for context requests."""
        from planning.domain.value_objects.statuses.token_budget import TokenBudget

        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        await use_case.execute(
            BacklogReviewCeremonyId("BRC-12345"),
            UserName("po@example.com")
        )

        # Verify all context calls use token_budget=2000 (STANDARD)
        for call in context_port.get_context.await_args_list:
            assert call.kwargs["token_budget"] == TokenBudget.STANDARD.value

    @pytest.mark.asyncio
    async def test_uses_backlog_review_role_enum(
        self,
        use_case: StartBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        context_port: ContextPort,
        orchestrator_port: OrchestratorPort,
        draft_ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test that BacklogReviewRole enum is used for all roles."""
        from planning.domain.value_objects.statuses.backlog_review_role import (
            BacklogReviewRole,
        )

        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony_with_stories

        await use_case.execute(
            BacklogReviewCeremonyId("BRC-12345"),
            UserName("po@example.com")
        )

        # Verify all roles are from BacklogReviewRole enum
        roles_called = set()
        for call in context_port.get_context.await_args_list:
            role_str = call.kwargs["role"]
            # Verify role is one of the enum values
            assert role_str in [r.value for r in BacklogReviewRole.all_roles()]
            roles_called.add(role_str)

        # Verify all 3 roles were called
        assert len(roles_called) == 3
        assert "ARCHITECT" in roles_called
        assert "QA" in roles_called
        assert "DEVOPS" in roles_called

