"""Unit tests for ListProjectsUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.list_projects_usecase import ListProjectsUseCase
from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus


@pytest.fixture
def mock_storage():
    """Create mock StoragePort."""
    return AsyncMock()


@pytest.fixture
def sample_projects():
    """Create sample projects for testing."""
    now = datetime.now(UTC)
    return [
        Project(
            project_id=ProjectId("PROJ-001"),
            name="Project 1",
            description="Description 1",
            status=ProjectStatus.ACTIVE,
            owner="owner1",
            created_at=now,
            updated_at=now,
        ),
        Project(
            project_id=ProjectId("PROJ-002"),
            name="Project 2",
            description="Description 2",
            status=ProjectStatus.COMPLETED,
            owner="owner2",
            created_at=now,
            updated_at=now,
        ),
        Project(
            project_id=ProjectId("PROJ-003"),
            name="Project 3",
            description="Description 3",
            status=ProjectStatus.PLANNING,
            owner="owner3",
            created_at=now,
            updated_at=now,
        ),
    ]


@pytest.mark.asyncio
async def test_list_projects_success(mock_storage, sample_projects):
    """Test successful project listing."""
    # Arrange
    mock_storage.list_projects.return_value = sample_projects
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    result = await use_case.execute(limit=10, offset=0)

    # Assert
    assert len(result) == 3
    assert result[0].project_id.value == "PROJ-001"
    assert result[1].project_id.value == "PROJ-002"
    mock_storage.list_projects.assert_awaited_once_with(
        status_filter=None,
        limit=10,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_projects_empty(mock_storage):
    """Test listing projects when none exist."""
    # Arrange
    mock_storage.list_projects.return_value = []
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    result = await use_case.execute()

    # Assert
    assert result == []
    assert len(result) == 0
    mock_storage.list_projects.assert_awaited_once_with(
        status_filter=None,
        limit=100,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_projects_default_pagination(mock_storage, sample_projects):
    """Test default pagination parameters."""
    # Arrange
    mock_storage.list_projects.return_value = sample_projects
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    await use_case.execute()

    # Assert
    mock_storage.list_projects.assert_awaited_once_with(
        status_filter=None,
        limit=100,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_projects_custom_pagination(mock_storage, sample_projects):
    """Test custom pagination parameters."""
    # Arrange
    mock_storage.list_projects.return_value = sample_projects[:2]  # Return only 2
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    await use_case.execute(limit=2, offset=1)

    # Assert
    mock_storage.list_projects.assert_awaited_once_with(
        status_filter=None,
        limit=2,
        offset=1,
    )


@pytest.mark.asyncio
async def test_list_projects_with_status_filter(mock_storage, sample_projects):
    """Test list_projects with status filter."""
    # Arrange
    filtered_projects = [p for p in sample_projects if p.status == ProjectStatus.COMPLETED]
    mock_storage.list_projects.return_value = filtered_projects
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    result = await use_case.execute(
        status_filter=ProjectStatus.COMPLETED,
        limit=10,
        offset=0,
    )

    # Assert
    assert len(result) == 1
    assert result[0].status == ProjectStatus.COMPLETED
    mock_storage.list_projects.assert_awaited_once_with(
        status_filter=ProjectStatus.COMPLETED,
        limit=10,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_projects_logging_with_status_filter(caplog, mock_storage, sample_projects):
    """Test that list_projects logs status_filter correctly."""
    import logging

    caplog.set_level(logging.INFO)

    # Arrange
    mock_storage.list_projects.return_value = sample_projects
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    await use_case.execute(
        status_filter=ProjectStatus.ACTIVE,
        limit=10,
        offset=0,
    )

    # Assert logging includes status_filter
    log_messages = [record.message for record in caplog.records]
    assert any("status_filter" in msg for msg in log_messages)
    assert any("active" in msg or "ACTIVE" in msg for msg in log_messages)


@pytest.mark.asyncio
async def test_list_projects_storage_returns_none(mock_storage):
    """Test that None from storage is converted to empty list (defensive programming)."""
    # Arrange
    mock_storage.list_projects.return_value = None
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    result = await use_case.execute()

    # Assert
    assert result == []
    assert len(result) == 0
    mock_storage.list_projects.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_projects_storage_error_propagates(mock_storage):
    """Test that storage errors are propagated."""
    # Arrange
    mock_storage.list_projects.side_effect = Exception("Database connection error")
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act & Assert
    with pytest.raises(Exception, match="Database connection error"):
        await use_case.execute()

    mock_storage.list_projects.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_projects_logging(caplog, mock_storage, sample_projects):
    """Test that list_projects logs correctly (info and warning)."""
    import logging

    caplog.set_level(logging.INFO)

    # Arrange
    mock_storage.list_projects.return_value = sample_projects
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    await use_case.execute(limit=10, offset=0)

    # Assert logging
    log_messages = [record.message for record in caplog.records]
    assert any("Listing projects:" in msg and "limit=10" in msg and "offset=0" in msg for msg in log_messages)
    assert any("status_filter=None" in msg for msg in log_messages)
    assert any("Found 3 projects" in msg or "✓ Found 3 projects" in msg for msg in log_messages)


@pytest.mark.asyncio
async def test_list_projects_logs_warning_when_storage_returns_none(caplog, mock_storage):
    """Test that list_projects logs warning when storage returns None (defensive programming)."""
    import logging

    caplog.set_level(logging.WARNING)

    # Arrange
    mock_storage.list_projects.return_value = None
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    result = await use_case.execute()

    # Assert
    assert result == []
    log_messages = [record.message for record in caplog.records]
    assert any("Storage returned None for list_projects" in msg for msg in log_messages)

