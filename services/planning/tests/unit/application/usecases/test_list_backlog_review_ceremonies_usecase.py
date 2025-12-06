"""Unit tests for ListBacklogReviewCeremoniesUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.ports import StoragePort
from planning.application.usecases.list_backlog_review_ceremonies_usecase import (
    ListBacklogReviewCeremoniesUseCase,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)


class TestListBacklogReviewCeremoniesUseCase:
    """Test suite for ListBacklogReviewCeremoniesUseCase."""

    @pytest.fixture
    def storage_port(self) -> StoragePort:
        """Fixture providing a mock StoragePort."""
        return AsyncMock(spec=StoragePort)

    @pytest.fixture
    def use_case(
        self, storage_port: StoragePort
    ) -> ListBacklogReviewCeremoniesUseCase:
        """Fixture providing the use case."""
        return ListBacklogReviewCeremoniesUseCase(storage=storage_port)

    @pytest.fixture
    def sample_ceremonies(self) -> list[BacklogReviewCeremony]:
        """Fixture providing sample ceremonies."""
        base_time = datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC)
        return [
            BacklogReviewCeremony(
                ceremony_id=BacklogReviewCeremonyId("BRC-001"),
                created_by=UserName("po1@example.com"),
                story_ids=(),
                status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
                created_at=base_time,
                updated_at=base_time,
            ),
            BacklogReviewCeremony(
                ceremony_id=BacklogReviewCeremonyId("BRC-002"),
                created_by=UserName("po1@example.com"),
                story_ids=(),
                status=BacklogReviewCeremonyStatus(
                    BacklogReviewCeremonyStatusEnum.IN_PROGRESS
                ),
                created_at=base_time,
                updated_at=base_time,
                started_at=base_time,
            ),
            BacklogReviewCeremony(
                ceremony_id=BacklogReviewCeremonyId("BRC-003"),
                created_by=UserName("po2@example.com"),
                story_ids=(),
                status=BacklogReviewCeremonyStatus(
                    BacklogReviewCeremonyStatusEnum.COMPLETED
                ),
                created_at=base_time,
                updated_at=base_time,
                started_at=base_time,
                completed_at=base_time,
            ),
        ]

    @pytest.mark.asyncio
    async def test_list_all_ceremonies(
        self,
        use_case: ListBacklogReviewCeremoniesUseCase,
        storage_port: StoragePort,
        sample_ceremonies: list[BacklogReviewCeremony],
    ) -> None:
        """Test listing all ceremonies without filters."""
        storage_port.list_backlog_review_ceremonies.return_value = sample_ceremonies

        result = await use_case.execute(limit=100, offset=0)

        assert len(result) == 3
        assert result == sample_ceremonies
        storage_port.list_backlog_review_ceremonies.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_with_status_filter(
        self,
        use_case: ListBacklogReviewCeremoniesUseCase,
        storage_port: StoragePort,
        sample_ceremonies: list[BacklogReviewCeremony],
    ) -> None:
        """Test listing ceremonies filtered by status."""
        storage_port.list_backlog_review_ceremonies.return_value = sample_ceremonies
        status_filter = BacklogReviewCeremonyStatus(
            BacklogReviewCeremonyStatusEnum.DRAFT
        )

        result = await use_case.execute(
            status_filter=status_filter, limit=100, offset=0
        )

        assert len(result) == 1
        assert result[0].ceremony_id.value == "BRC-001"
        assert result[0].status.is_draft()

    @pytest.mark.asyncio
    async def test_list_with_created_by_filter(
        self,
        use_case: ListBacklogReviewCeremoniesUseCase,
        storage_port: StoragePort,
        sample_ceremonies: list[BacklogReviewCeremony],
    ) -> None:
        """Test listing ceremonies filtered by creator."""
        storage_port.list_backlog_review_ceremonies.return_value = sample_ceremonies
        created_by = UserName("po1@example.com")

        result = await use_case.execute(created_by=created_by, limit=100, offset=0)

        assert len(result) == 2
        assert all(c.created_by == created_by for c in result)
        assert result[0].ceremony_id.value == "BRC-001"
        assert result[1].ceremony_id.value == "BRC-002"

    @pytest.mark.asyncio
    async def test_list_with_both_filters(
        self,
        use_case: ListBacklogReviewCeremoniesUseCase,
        storage_port: StoragePort,
        sample_ceremonies: list[BacklogReviewCeremony],
    ) -> None:
        """Test listing ceremonies with both status and created_by filters."""
        storage_port.list_backlog_review_ceremonies.return_value = sample_ceremonies
        status_filter = BacklogReviewCeremonyStatus(
            BacklogReviewCeremonyStatusEnum.IN_PROGRESS
        )
        created_by = UserName("po1@example.com")

        result = await use_case.execute(
            status_filter=status_filter,
            created_by=created_by,
            limit=100,
            offset=0,
        )

        assert len(result) == 1
        assert result[0].ceremony_id.value == "BRC-002"
        assert result[0].status.is_in_progress()
        assert result[0].created_by == created_by

    @pytest.mark.asyncio
    async def test_list_with_pagination(
        self,
        use_case: ListBacklogReviewCeremoniesUseCase,
        storage_port: StoragePort,
        sample_ceremonies: list[BacklogReviewCeremony],
    ) -> None:
        """Test listing ceremonies with pagination."""
        storage_port.list_backlog_review_ceremonies.return_value = sample_ceremonies

        result = await use_case.execute(limit=2, offset=1)

        assert len(result) == 2
        assert result[0].ceremony_id.value == "BRC-002"
        assert result[1].ceremony_id.value == "BRC-003"

    @pytest.mark.asyncio
    async def test_list_empty_result(
        self,
        use_case: ListBacklogReviewCeremoniesUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test listing when no ceremonies exist."""
        storage_port.list_backlog_review_ceremonies.return_value = []

        result = await use_case.execute(limit=100, offset=0)

        assert len(result) == 0
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_limit_raises_error(
        self,
        use_case: ListBacklogReviewCeremoniesUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that invalid limit raises ValueError."""
        with pytest.raises(ValueError, match="limit must be >= 1"):
            await use_case.execute(limit=0, offset=0)

        with pytest.raises(ValueError, match="limit must be <= 1000"):
            await use_case.execute(limit=1001, offset=0)

    @pytest.mark.asyncio
    async def test_invalid_offset_raises_error(
        self,
        use_case: ListBacklogReviewCeremoniesUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that invalid offset raises ValueError."""
        with pytest.raises(ValueError, match="offset must be >= 0"):
            await use_case.execute(limit=100, offset=-1)

    @pytest.mark.asyncio
    async def test_storage_error_propagates(
        self,
        use_case: ListBacklogReviewCeremoniesUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that storage errors propagate correctly."""
        storage_port.list_backlog_review_ceremonies.side_effect = Exception(
            "Storage error"
        )

        with pytest.raises(Exception, match="Storage error"):
            await use_case.execute(limit=100, offset=0)
