"""Unit tests for CreateBacklogReviewCeremonyUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.create_backlog_review_ceremony_usecase import (
    CreateBacklogReviewCeremonyUseCase,
)
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.story_id import StoryId


class TestCreateBacklogReviewCeremonyUseCase:
    """Test suite for CreateBacklogReviewCeremonyUseCase."""

    @pytest.fixture
    def storage_port(self) -> StoragePort:
        """Fixture providing a mock StoragePort."""
        mock = AsyncMock(spec=StoragePort)
        mock.save_backlog_review_ceremony = AsyncMock()
        return mock

    @pytest.fixture
    def messaging_port(self) -> MessagingPort:
        """Fixture providing a mock MessagingPort."""
        mock = AsyncMock(spec=MessagingPort)
        mock.publish_event = AsyncMock()
        return mock

    @pytest.fixture
    def use_case(
        self,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> CreateBacklogReviewCeremonyUseCase:
        """Fixture providing the use case with mocked dependencies."""
        return CreateBacklogReviewCeremonyUseCase(
            storage=storage_port,
            messaging=messaging_port,
        )

    @pytest.mark.asyncio
    async def test_create_ceremony_without_stories_success(
        self,
        use_case: CreateBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> None:
        """Test creating ceremony without pre-selected stories."""
        created_by = UserName("po@example.com")

        ceremony = await use_case.execute(created_by=created_by)

        # Verify ceremony created with correct attributes
        assert ceremony.ceremony_id.value.startswith("BRC-")
        assert ceremony.created_by == created_by
        assert ceremony.story_ids == ()
        assert ceremony.status.is_draft()
        assert ceremony.created_at <= datetime.now(UTC)
        assert ceremony.started_at is None
        assert ceremony.completed_at is None

        # Verify storage was called
        storage_port.save_backlog_review_ceremony.assert_awaited_once()
        saved_ceremony = storage_port.save_backlog_review_ceremony.call_args[0][0]
        assert saved_ceremony == ceremony

        # Verify event was published
        messaging_port.publish_event.assert_awaited_once()
        call_args = messaging_port.publish_event.call_args
        assert call_args[1]["subject"] == "planning.backlog_review.created"
        assert call_args[1]["payload"]["created_by"] == "po@example.com"
        assert call_args[1]["payload"]["story_ids"] == []
        assert call_args[1]["payload"]["status"] == "DRAFT"

    @pytest.mark.asyncio
    async def test_create_ceremony_with_stories_success(
        self,
        use_case: CreateBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> None:
        """Test creating ceremony with pre-selected stories."""
        created_by = UserName("po@example.com")
        story_ids = (StoryId("ST-001"), StoryId("ST-002"))

        ceremony = await use_case.execute(
            created_by=created_by,
            story_ids=story_ids,
        )

        # Verify ceremony has stories
        assert len(ceremony.story_ids) == 2
        assert StoryId("ST-001") in ceremony.story_ids
        assert StoryId("ST-002") in ceremony.story_ids

        # Verify event payload includes story_ids
        call_args = messaging_port.publish_event.call_args
        assert call_args[1]["payload"]["story_ids"] == ["ST-001", "ST-002"]

    @pytest.mark.asyncio
    async def test_ceremony_id_is_unique(
        self,
        use_case: CreateBacklogReviewCeremonyUseCase,
    ) -> None:
        """Test that each ceremony gets a unique ID."""
        created_by = UserName("po@example.com")

        ceremony1 = await use_case.execute(created_by=created_by)
        ceremony2 = await use_case.execute(created_by=created_by)

        assert ceremony1.ceremony_id != ceremony2.ceremony_id

    @pytest.mark.asyncio
    async def test_created_by_validation(
        self,
        use_case: CreateBacklogReviewCeremonyUseCase,
    ) -> None:
        """Test that created_by validation is enforced."""
        with pytest.raises(ValueError, match="UserName cannot be empty"):
            await use_case.execute(created_by=UserName("   "))

    @pytest.mark.asyncio
    async def test_storage_error_propagates(
        self,
        use_case: CreateBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that storage errors propagate correctly."""
        storage_port.save_backlog_review_ceremony.side_effect = Exception(
            "Storage error"
        )
        created_by = UserName("po@example.com")

        with pytest.raises(Exception, match="Storage error"):
            await use_case.execute(created_by=created_by)

    @pytest.mark.asyncio
    async def test_messaging_error_does_not_fail_use_case(
        self,
        use_case: CreateBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> None:
        """Test that messaging errors don't fail the use case (best-effort)."""
        messaging_port.publish_event.side_effect = Exception("NATS connection error")
        created_by = UserName("po@example.com")

        # Should NOT raise - messaging is best-effort
        ceremony = await use_case.execute(created_by=created_by)

        # Verify ceremony was still created and saved
        assert ceremony is not None
        storage_port.save_backlog_review_ceremony.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_timestamps_are_consistent(
        self,
        use_case: CreateBacklogReviewCeremonyUseCase,
    ) -> None:
        """Test that created_at and updated_at are the same initially."""
        created_by = UserName("po@example.com")

        ceremony = await use_case.execute(created_by=created_by)

        assert ceremony.created_at == ceremony.updated_at

