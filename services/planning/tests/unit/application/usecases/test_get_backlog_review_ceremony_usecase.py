"""Unit tests for GetBacklogReviewCeremonyUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.ports import StoragePort
from planning.application.usecases.get_backlog_review_ceremony_usecase import (
    GetBacklogReviewCeremonyUseCase,
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


class TestGetBacklogReviewCeremonyUseCase:
    """Test suite for GetBacklogReviewCeremonyUseCase."""

    @pytest.fixture
    def storage_port(self) -> StoragePort:
        """Fixture providing a mock StoragePort."""
        return AsyncMock(spec=StoragePort)

    @pytest.fixture
    def use_case(self, storage_port: StoragePort) -> GetBacklogReviewCeremonyUseCase:
        """Fixture providing the use case."""
        return GetBacklogReviewCeremonyUseCase(storage=storage_port)

    @pytest.fixture
    def sample_ceremony(self) -> BacklogReviewCeremony:
        """Fixture providing a sample ceremony."""
        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_get_ceremony_found(
        self,
        use_case: GetBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
        sample_ceremony: BacklogReviewCeremony,
    ) -> None:
        """Test retrieving an existing ceremony."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        storage_port.get_backlog_review_ceremony.return_value = sample_ceremony

        result = await use_case.execute(ceremony_id)

        assert result == sample_ceremony
        storage_port.get_backlog_review_ceremony.assert_awaited_once_with(ceremony_id)

    @pytest.mark.asyncio
    async def test_get_ceremony_not_found(
        self,
        use_case: GetBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test retrieving non-existent ceremony returns None."""
        ceremony_id = BacklogReviewCeremonyId("BRC-99999")
        storage_port.get_backlog_review_ceremony.return_value = None

        result = await use_case.execute(ceremony_id)

        assert result is None
        storage_port.get_backlog_review_ceremony.assert_awaited_once_with(ceremony_id)

    @pytest.mark.asyncio
    async def test_storage_error_propagates(
        self,
        use_case: GetBacklogReviewCeremonyUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that storage errors propagate correctly."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        storage_port.get_backlog_review_ceremony.side_effect = Exception("Storage error")

        with pytest.raises(Exception, match="Storage error"):
            await use_case.execute(ceremony_id)

