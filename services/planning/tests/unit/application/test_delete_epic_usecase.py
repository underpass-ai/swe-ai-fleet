"""Unit tests for DeleteEpicUseCase."""

from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.delete_epic_usecase import DeleteEpicUseCase
from planning.domain.value_objects.identifiers.epic_id import EpicId


@pytest.fixture
def mock_storage():
    """Create mock StoragePort."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_delete_epic_success(mock_storage):
    """Test successful epic deletion."""
    # Arrange
    use_case = DeleteEpicUseCase(storage=mock_storage)
    epic_id = EpicId("E-TEST-001")

    # Act
    await use_case.execute(epic_id)

    # Assert
    mock_storage.delete_epic.assert_awaited_once_with(epic_id)


@pytest.mark.asyncio
async def test_delete_epic_empty_id_raises_value_error(mock_storage):
    """Test that empty epic_id raises ValueError."""
    # Arrange
    use_case = DeleteEpicUseCase(storage=mock_storage)
    # EpicId validates in __post_init__, so we can't create an empty one
    # Instead, we test with None which the use case should handle

    # Act & Assert
    with pytest.raises(ValueError, match="epic_id cannot be empty"):
        await use_case.execute(None)  # type: ignore[arg-type]

    # Assert storage was not called
    mock_storage.delete_epic.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_epic_none_id_raises_value_error(mock_storage):
    """Test that None epic_id raises ValueError."""
    # Arrange
    use_case = DeleteEpicUseCase(storage=mock_storage)

    # Act & Assert
    with pytest.raises(ValueError, match="epic_id cannot be empty"):
        await use_case.execute(None)  # type: ignore[arg-type]

    # Assert storage was not called
    mock_storage.delete_epic.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_epic_storage_error_propagates(mock_storage):
    """Test that storage errors are propagated."""
    # Arrange
    mock_storage.delete_epic.side_effect = Exception("Storage connection error")
    use_case = DeleteEpicUseCase(storage=mock_storage)
    epic_id = EpicId("E-ERROR")

    # Act & Assert
    with pytest.raises(Exception, match="Storage connection error"):
        await use_case.execute(epic_id)

    mock_storage.delete_epic.assert_awaited_once_with(epic_id)


@pytest.mark.asyncio
async def test_delete_epic_calls_storage_with_correct_id(mock_storage):
    """Test that storage is called with correct EpicId."""
    # Arrange
    use_case = DeleteEpicUseCase(storage=mock_storage)
    epic_id = EpicId("E-SPECIFIC-123")

    # Act
    await use_case.execute(epic_id)

    # Assert
    call_args = mock_storage.delete_epic.call_args[0]
    assert len(call_args) == 1
    assert call_args[0] == epic_id
    assert isinstance(call_args[0], EpicId)


@pytest.mark.asyncio
async def test_delete_epic_initialization(mock_storage):
    """Test that use case initializes correctly."""
    # Act
    use_case = DeleteEpicUseCase(storage=mock_storage)

    # Assert
    assert use_case._storage == mock_storage


@pytest.mark.asyncio
async def test_delete_epic_multiple_calls(mock_storage):
    """Test that use case can handle multiple delete calls."""
    # Arrange
    use_case = DeleteEpicUseCase(storage=mock_storage)
    epic_id_1 = EpicId("E-001")
    epic_id_2 = EpicId("E-002")

    # Act
    await use_case.execute(epic_id_1)
    await use_case.execute(epic_id_2)

    # Assert
    assert mock_storage.delete_epic.await_count == 2
    mock_storage.delete_epic.assert_any_await(epic_id_1)
    mock_storage.delete_epic.assert_any_await(epic_id_2)
