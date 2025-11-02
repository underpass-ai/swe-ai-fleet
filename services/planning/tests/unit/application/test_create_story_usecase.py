"""Unit tests for CreateStoryUseCase."""

from unittest.mock import AsyncMock

import pytest

from planning.application.usecases import CreateStoryUseCase
from planning.domain import StoryStateEnum


@pytest.mark.asyncio
async def test_create_story_success():
    """Test successful story creation."""
    # Arrange
    storage_mock = AsyncMock()
    messaging_mock = AsyncMock()

    use_case = CreateStoryUseCase(
        storage=storage_mock,
        messaging=messaging_mock,
    )

    # Act
    story = await use_case.execute(
        title="As a user, I want to login",
        brief="Login functionality with AC1 and AC2",
        created_by="po-user",
    )

    # Assert
    assert story.title == "As a user, I want to login"
    assert story.brief == "Login functionality with AC1 and AC2"
    assert story.state.value == StoryStateEnum.DRAFT
    assert story.dor_score.value == 0
    assert story.created_by == "po-user"
    assert story.story_id.value.startswith("s-")  # Auto-generated

    storage_mock.save_story.assert_awaited_once()
    messaging_mock.publish_story_created.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_story_empty_title():
    """Test create story with empty title fails."""
    storage_mock = AsyncMock()
    messaging_mock = AsyncMock()

    use_case = CreateStoryUseCase(
        storage=storage_mock,
        messaging=messaging_mock,
    )

    with pytest.raises(ValueError, match="title cannot be empty"):
        await use_case.execute(
            title="",
            brief="Brief",
            created_by="po",
        )


@pytest.mark.asyncio
async def test_create_story_empty_brief():
    """Test create story with empty brief fails."""
    storage_mock = AsyncMock()
    messaging_mock = AsyncMock()

    use_case = CreateStoryUseCase(
        storage=storage_mock,
        messaging=messaging_mock,
    )

    with pytest.raises(ValueError, match="brief cannot be empty"):
        await use_case.execute(
            title="Title",
            brief="",
            created_by="po",
        )


@pytest.mark.asyncio
async def test_create_story_empty_created_by():
    """Test create story with empty created_by fails."""
    storage_mock = AsyncMock()
    messaging_mock = AsyncMock()

    use_case = CreateStoryUseCase(
        storage=storage_mock,
        messaging=messaging_mock,
    )

    with pytest.raises(ValueError, match="created_by cannot be empty"):
        await use_case.execute(
            title="Title",
            brief="Brief",
            created_by="",
        )
