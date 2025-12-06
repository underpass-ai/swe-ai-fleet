"""Unit tests for RemoveStoryFromReviewUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.ports import StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.application.usecases.remove_story_from_review_usecase import (
    RemoveStoryFromReviewUseCase,
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


class TestRemoveStoryFromReviewUseCase:
    """Test suite for RemoveStoryFromReviewUseCase."""

    @pytest.fixture
    def storage_port(self) -> StoragePort:
        """Fixture providing a mock StoragePort."""
        return AsyncMock(spec=StoragePort)

    @pytest.fixture
    def use_case(self, storage_port: StoragePort) -> RemoveStoryFromReviewUseCase:
        """Fixture providing the use case."""
        return RemoveStoryFromReviewUseCase(storage=storage_port)

    @pytest.fixture
    def ceremony_with_stories(self) -> BacklogReviewCeremony:
        """Fixture providing ceremony with stories."""
        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"), StoryId("ST-002")),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_remove_story_success(
        self,
        use_case: RemoveStoryFromReviewUseCase,
        storage_port: StoragePort,
        ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test successfully removing a story."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        story_id = StoryId("ST-001")

        storage_port.get_backlog_review_ceremony.return_value = ceremony_with_stories

        result = await use_case.execute(ceremony_id, story_id)

        assert len(result.story_ids) == 1
        assert StoryId("ST-002") in result.story_ids
        assert StoryId("ST-001") not in result.story_ids
        storage_port.save_backlog_review_ceremony.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ceremony_not_found_raises(
        self,
        use_case: RemoveStoryFromReviewUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that non-existent ceremony raises error."""
        ceremony_id = BacklogReviewCeremonyId("BRC-99999")
        storage_port.get_backlog_review_ceremony.return_value = None

        with pytest.raises(CeremonyNotFoundError):
            await use_case.execute(ceremony_id, StoryId("ST-001"))

    @pytest.mark.asyncio
    async def test_story_not_in_ceremony_raises_value_error(
        self,
        use_case: RemoveStoryFromReviewUseCase,
        storage_port: StoragePort,
        ceremony_with_stories: BacklogReviewCeremony,
    ) -> None:
        """Test removing non-existent story raises error."""
        storage_port.get_backlog_review_ceremony.return_value = ceremony_with_stories

        with pytest.raises(ValueError, match="not in ceremony"):
            await use_case.execute(
                BacklogReviewCeremonyId("BRC-12345"),
                StoryId("ST-999")
            )

    @pytest.mark.asyncio
    async def test_remove_from_completed_ceremony_raises(
        self,
        use_case: RemoveStoryFromReviewUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test removing from completed ceremony raises error."""
        completed_ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            completed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        storage_port.get_backlog_review_ceremony.return_value = completed_ceremony

        with pytest.raises(ValueError, match="Cannot remove story from COMPLETED"):
            await use_case.execute(
                BacklogReviewCeremonyId("BRC-12345"),
                StoryId("ST-001")
            )

