"""Unit tests for DeleteStoryUseCase."""

from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.delete_story_usecase import DeleteStoryUseCase
from planning.domain.value_objects.identifiers.story_id import StoryId


@pytest.fixture
def mock_storage():
    """Create mock StoragePort."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_delete_story_success(mock_storage):
    """Test successful story deletion."""
    # Arrange
    use_case = DeleteStoryUseCase(storage=mock_storage)
    story_id = StoryId("s-TEST-001")

    # Act
    await use_case.execute(story_id)

    # Assert
    mock_storage.delete_story.assert_awaited_once_with(story_id)


@pytest.mark.asyncio
async def test_delete_story_empty_id_raises_value_error(mock_storage):
    """Test that empty story_id raises ValueError."""
    # Arrange
    use_case = DeleteStoryUseCase(storage=mock_storage)
    # StoryId validates in __post_init__, so we can't create an empty one
    # Instead, we test with None which the use case should handle

    # Act & Assert
    with pytest.raises(ValueError, match="story_id cannot be empty"):
        await use_case.execute(None)  # type: ignore[arg-type]

    # Assert storage was not called
    mock_storage.delete_story.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_story_none_id_raises_value_error(mock_storage):
    """Test that None story_id raises ValueError."""
    # Arrange
    use_case = DeleteStoryUseCase(storage=mock_storage)

    # Act & Assert
    with pytest.raises(ValueError, match="story_id cannot be empty"):
        await use_case.execute(None)  # type: ignore[arg-type]

    # Assert storage was not called
    mock_storage.delete_story.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_story_storage_error_propagates(mock_storage):
    """Test that storage errors are propagated."""
    # Arrange
    mock_storage.delete_story.side_effect = Exception("Storage connection error")
    use_case = DeleteStoryUseCase(storage=mock_storage)
    story_id = StoryId("s-ERROR")

    # Act & Assert
    with pytest.raises(Exception, match="Storage connection error"):
        await use_case.execute(story_id)

    mock_storage.delete_story.assert_awaited_once_with(story_id)


@pytest.mark.asyncio
async def test_delete_story_calls_storage_with_correct_id(mock_storage):
    """Test that storage is called with correct StoryId."""
    # Arrange
    use_case = DeleteStoryUseCase(storage=mock_storage)
    story_id = StoryId("s-SPECIFIC-123")

    # Act
    await use_case.execute(story_id)

    # Assert
    call_args = mock_storage.delete_story.call_args[0]
    assert len(call_args) == 1
    assert call_args[0] == story_id
    assert isinstance(call_args[0], StoryId)


@pytest.mark.asyncio
async def test_delete_story_initialization(mock_storage):
    """Test that use case initializes correctly."""
    # Act
    use_case = DeleteStoryUseCase(storage=mock_storage)

    # Assert
    assert use_case._storage == mock_storage


@pytest.mark.asyncio
async def test_delete_story_multiple_calls(mock_storage):
    """Test that use case can handle multiple delete calls."""
    # Arrange
    use_case = DeleteStoryUseCase(storage=mock_storage)
    story_id_1 = StoryId("s-001")
    story_id_2 = StoryId("s-002")

    # Act
    await use_case.execute(story_id_1)
    await use_case.execute(story_id_2)

    # Assert
    assert mock_storage.delete_story.await_count == 2
    mock_storage.delete_story.assert_any_await(story_id_1)
    mock_storage.delete_story.assert_any_await(story_id_2)
