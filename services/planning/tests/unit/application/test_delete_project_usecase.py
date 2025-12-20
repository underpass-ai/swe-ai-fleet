"""Unit tests for DeleteProjectUseCase."""

from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.delete_project_usecase import DeleteProjectUseCase
from planning.domain.value_objects.identifiers.project_id import ProjectId


@pytest.fixture
def mock_storage():
    """Create mock StoragePort."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_delete_project_success(mock_storage):
    """Test successful project deletion."""
    # Arrange
    use_case = DeleteProjectUseCase(storage=mock_storage)
    project_id = ProjectId("PROJ-TEST-001")

    # Act
    await use_case.execute(project_id)

    # Assert
    mock_storage.delete_project.assert_awaited_once_with(project_id)


@pytest.mark.asyncio
async def test_delete_project_empty_id_raises_value_error(mock_storage):
    """Test that empty project_id raises ValueError."""
    # Arrange
    use_case = DeleteProjectUseCase(storage=mock_storage)
    # ProjectId validates in __post_init__, so we can't create an empty one
    # Instead, we test with None which the use case should handle
    # Note: ProjectId("") would raise ValueError in constructor, so we test None

    # Act & Assert
    with pytest.raises(ValueError, match="project_id cannot be empty"):
        await use_case.execute(None)  # type: ignore[arg-type]

    # Assert storage was not called
    mock_storage.delete_project.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_project_none_id_raises_value_error(mock_storage):
    """Test that None project_id raises ValueError."""
    # Arrange
    use_case = DeleteProjectUseCase(storage=mock_storage)

    # Act & Assert
    with pytest.raises(ValueError, match="project_id cannot be empty"):
        await use_case.execute(None)  # type: ignore[arg-type]

    # Assert storage was not called
    mock_storage.delete_project.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_project_storage_error_propagates(mock_storage):
    """Test that storage errors are propagated."""
    # Arrange
    mock_storage.delete_project.side_effect = Exception("Storage connection error")
    use_case = DeleteProjectUseCase(storage=mock_storage)
    project_id = ProjectId("PROJ-ERROR")

    # Act & Assert
    with pytest.raises(Exception, match="Storage connection error"):
        await use_case.execute(project_id)

    mock_storage.delete_project.assert_awaited_once_with(project_id)


@pytest.mark.asyncio
async def test_delete_project_calls_storage_with_correct_id(mock_storage):
    """Test that storage is called with correct ProjectId."""
    # Arrange
    use_case = DeleteProjectUseCase(storage=mock_storage)
    project_id = ProjectId("PROJ-SPECIFIC-123")

    # Act
    await use_case.execute(project_id)

    # Assert
    call_args = mock_storage.delete_project.call_args[0]
    assert len(call_args) == 1
    assert call_args[0] == project_id
    assert isinstance(call_args[0], ProjectId)


@pytest.mark.asyncio
async def test_delete_project_initialization(mock_storage):
    """Test that use case initializes correctly."""
    # Act
    use_case = DeleteProjectUseCase(storage=mock_storage)

    # Assert
    assert use_case._storage == mock_storage


@pytest.mark.asyncio
async def test_delete_project_different_storage_instances(mock_storage):
    """Test that use case works with different storage instances."""
    # Arrange
    use_case_1 = DeleteProjectUseCase(storage=mock_storage)
    use_case_2 = DeleteProjectUseCase(storage=mock_storage)
    project_id = ProjectId("PROJ-SHARED")

    # Act
    await use_case_1.execute(project_id)
    await use_case_2.execute(project_id)

    # Assert
    assert mock_storage.delete_project.await_count == 2
