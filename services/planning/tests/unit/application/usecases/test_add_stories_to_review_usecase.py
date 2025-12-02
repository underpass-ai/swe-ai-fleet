"""Unit tests for AddStoriesToReviewUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from planning.application.ports import StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    AddStoriesToReviewUseCase,
    CeremonyNotFoundError,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)


class TestAddStoriesToReviewUseCase:
    """Test suite for AddStoriesToReviewUseCase."""

    @pytest.fixture
    def storage_port(self) -> StoragePort:
        """Fixture providing a mock StoragePort."""
        return AsyncMock(spec=StoragePort)

    @pytest.fixture
    def use_case(self, storage_port: StoragePort) -> AddStoriesToReviewUseCase:
        """Fixture providing the use case."""
        return AddStoriesToReviewUseCase(storage=storage_port)

    @pytest.fixture
    def draft_ceremony(self) -> BacklogReviewCeremony:
        """Fixture providing a draft ceremony."""
        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_add_single_story_success(
        self,
        use_case: AddStoriesToReviewUseCase,
        storage_port: StoragePort,
        draft_ceremony: BacklogReviewCeremony,
    ) -> None:
        """Test adding a single story to ceremony."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        story_ids = (StoryId("ST-001"),)
        
        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony

        result = await use_case.execute(ceremony_id, story_ids)

        assert len(result.story_ids) == 1
        assert StoryId("ST-001") in result.story_ids
        storage_port.save_backlog_review_ceremony.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_multiple_stories_success(
        self,
        use_case: AddStoriesToReviewUseCase,
        storage_port: StoragePort,
        draft_ceremony: BacklogReviewCeremony,
    ) -> None:
        """Test adding multiple stories to ceremony."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        story_ids = (StoryId("ST-001"), StoryId("ST-002"), StoryId("ST-003"))
        
        storage_port.get_backlog_review_ceremony.return_value = draft_ceremony

        result = await use_case.execute(ceremony_id, story_ids)

        assert len(result.story_ids) == 3

    @pytest.mark.asyncio
    async def test_ceremony_not_found_raises(
        self,
        use_case: AddStoriesToReviewUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that non-existent ceremony raises CeremonyNotFoundError."""
        ceremony_id = BacklogReviewCeremonyId("BRC-99999")
        storage_port.get_backlog_review_ceremony.return_value = None

        with pytest.raises(CeremonyNotFoundError, match="Ceremony not found"):
            await use_case.execute(ceremony_id, (StoryId("ST-001"),))

    @pytest.mark.asyncio
    async def test_duplicate_story_raises_value_error(
        self,
        use_case: AddStoriesToReviewUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that adding duplicate story raises ValueError."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        existing_story = StoryId("ST-001")
        
        ceremony_with_story = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=UserName("po@example.com"),
            story_ids=(existing_story,),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )
        
        storage_port.get_backlog_review_ceremony.return_value = ceremony_with_story

        with pytest.raises(ValueError, match="already in ceremony"):
            await use_case.execute(ceremony_id, (existing_story,))

    @pytest.mark.asyncio
    async def test_add_to_completed_ceremony_raises_value_error(
        self,
        use_case: AddStoriesToReviewUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that adding to completed ceremony raises ValueError."""
        completed_ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            completed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )
        
        storage_port.get_backlog_review_ceremony.return_value = completed_ceremony

        with pytest.raises(ValueError, match="Cannot add story to COMPLETED ceremony"):
            await use_case.execute(
                BacklogReviewCeremonyId("BRC-12345"),
                (StoryId("ST-001"),)
            )

