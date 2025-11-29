"""Unit tests for GetProjectUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.get_project_usecase import GetProjectUseCase
from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus


@pytest.fixture
def mock_storage():
    """Create mock StoragePort."""
    return AsyncMock()


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    now = datetime.now(UTC)
    return Project(
        project_id=ProjectId("PROJ-TEST-001"),
        name="Test Project",
        description="Test description",
        status=ProjectStatus.ACTIVE,
        owner="test-owner",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_project_success(mock_storage, sample_project):
    """Test successful project retrieval."""
    # Arrange
    mock_storage.get_project.return_value = sample_project
    use_case = GetProjectUseCase(storage=mock_storage)
    project_id = ProjectId("PROJ-TEST-001")

    # Act
    result = await use_case.execute(project_id)

    # Assert
    assert result is not None
    assert result.project_id == project_id
    assert result.name == "Test Project"
    mock_storage.get_project.assert_awaited_once_with(project_id)


@pytest.mark.asyncio
async def test_get_project_not_found(mock_storage):
    """Test project not found returns None."""
    # Arrange
    mock_storage.get_project.return_value = None
    use_case = GetProjectUseCase(storage=mock_storage)
    project_id = ProjectId("PROJ-NOTEXIST")

    # Act
    result = await use_case.execute(project_id)

    # Assert
    assert result is None
    mock_storage.get_project.assert_awaited_once_with(project_id)


@pytest.mark.asyncio
async def test_get_project_storage_error_propagates(mock_storage):
    """Test that storage errors are propagated."""
    # Arrange
    mock_storage.get_project.side_effect = Exception("Storage connection error")
    use_case = GetProjectUseCase(storage=mock_storage)
    project_id = ProjectId("PROJ-ERROR")

    # Act & Assert
    with pytest.raises(Exception, match="Storage connection error"):
        await use_case.execute(project_id)

    mock_storage.get_project.assert_awaited_once_with(project_id)


@pytest.mark.asyncio
async def test_get_project_calls_storage_with_correct_id(mock_storage, sample_project):
    """Test that storage is called with correct ProjectId."""
    # Arrange
    mock_storage.get_project.return_value = sample_project
    use_case = GetProjectUseCase(storage=mock_storage)
    project_id = ProjectId("PROJ-SPECIFIC-123")

    # Act
    await use_case.execute(project_id)

    # Assert
    call_args = mock_storage.get_project.call_args[0]
    assert len(call_args) == 1
    assert call_args[0] == project_id
    assert isinstance(call_args[0], ProjectId)

