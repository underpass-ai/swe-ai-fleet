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
    mock_storage.list_projects.assert_awaited_once_with(limit=10, offset=0)


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
    mock_storage.list_projects.assert_awaited_once_with(limit=100, offset=0)


@pytest.mark.asyncio
async def test_list_projects_default_pagination(mock_storage, sample_projects):
    """Test default pagination parameters."""
    # Arrange
    mock_storage.list_projects.return_value = sample_projects
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    await use_case.execute()

    # Assert
    mock_storage.list_projects.assert_awaited_once_with(limit=100, offset=0)


@pytest.mark.asyncio
async def test_list_projects_custom_pagination(mock_storage, sample_projects):
    """Test custom pagination parameters."""
    # Arrange
    mock_storage.list_projects.return_value = sample_projects[:2]  # Return only 2
    use_case = ListProjectsUseCase(storage=mock_storage)

    # Act
    result = await use_case.execute(limit=2, offset=1)

    # Assert
    mock_storage.list_projects.assert_awaited_once_with(limit=2, offset=1)


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

