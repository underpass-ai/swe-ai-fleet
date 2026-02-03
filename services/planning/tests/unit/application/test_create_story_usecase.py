"""Unit tests for CreateStoryUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases import CreateStoryUseCase
from planning.domain import (
    Brief,
    StoryStateEnum,
    Title,
    UserName,
)
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId


@pytest.mark.asyncio
async def test_create_story_success():
    """Test successful story creation."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)

    # Mock parent epic (domain invariant validation)
    epic_id = EpicId("E-TEST-001")
    mock_epic = Epic(
        epic_id=epic_id,
        project_id=ProjectId("PROJ-TEST-001"),
        title="Test Epic",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_epic.return_value = mock_epic

    title = Title("As a user I want to login")
    brief = Brief("User should be able to authenticate with email and password")
    created_by = UserName("po-tirso")

    story = await use_case.execute(
        epic_id=epic_id,  # REQUIRED - domain invariant
        title=title,
        brief=brief,
        created_by=created_by,
    )

    # Verify story created with correct attributes
    assert story.title.value == "As a user I want to login"
    assert story.brief.value == "User should be able to authenticate with email and password"
    assert story.created_by.value == "po-tirso"
    assert story.state.is_state(StoryStateEnum.DRAFT)
    assert story.dor_score.value == 0

    # Verify story was saved
    storage.save_story.assert_awaited_once()
    saved_story = storage.save_story.call_args[0][0]
    assert saved_story.title.value == "As a user I want to login"

    # Verify event was published
    messaging.publish_story_created.assert_awaited_once()
    call_args = messaging.publish_story_created.call_args[1]
    assert call_args["epic_id"] == epic_id
    assert call_args["title"] == title
    assert call_args["created_by"] == created_by


@pytest.mark.asyncio
async def test_create_story_generates_unique_id():
    """Test that story ID is auto-generated."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)

    # Mock parent epic
    epic_id = EpicId("E-TEST-002")
    mock_epic = Epic(
        epic_id=epic_id,
        project_id=ProjectId("PROJ-TEST-002"),
        title="Test Epic",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_epic.return_value = mock_epic

    story1 = await use_case.execute(
        epic_id=epic_id,
        title=Title("Story 1"),
        brief=Brief("Brief 1"),
        created_by=UserName("po"),
    )

    story2 = await use_case.execute(
        epic_id=epic_id,
        title=Title("Story 2"),
        brief=Brief("Brief 2"),
        created_by=UserName("po"),
    )

    # IDs should be different
    assert story1.story_id != story2.story_id


@pytest.mark.asyncio
async def test_create_story_sets_timestamps():
    """Test that created_at and updated_at are set."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)

    # Mock parent epic
    epic_id = EpicId("E-TEST-003")
    mock_epic = Epic(
        epic_id=epic_id,
        project_id=ProjectId("PROJ-TEST-003"),
        title="Test Epic",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_epic.return_value = mock_epic

    before = datetime.now(UTC)

    story = await use_case.execute(
        epic_id=epic_id,
        title=Title("Test"),
        brief=Brief("Test brief"),
        created_by=UserName("po"),
    )

    after = datetime.now(UTC)

    # Timestamps should be within test execution window
    assert before <= story.created_at <= after
    assert before <= story.updated_at <= after
    assert story.created_at == story.updated_at  # Same at creation


@pytest.mark.asyncio
async def test_create_story_storage_failure_propagates():
    """Test that storage failures are propagated."""
    storage = AsyncMock()
    storage.save_story.side_effect = Exception("Storage error")
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)

    # Mock parent epic
    epic_id = EpicId("E-TEST-004")
    mock_epic = Epic(
        epic_id=epic_id,
        project_id=ProjectId("PROJ-TEST-004"),
        title="Test Epic",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_epic.return_value = mock_epic

    with pytest.raises(Exception, match="Storage error"):
        await use_case.execute(
            epic_id=epic_id,
            title=Title("Test"),
            brief=Brief("Test brief"),
            created_by=UserName("po"),
        )

    # Event should not be published on storage failure
    messaging.publish_story_created.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_story_raises_error_when_epic_not_found():
    """Test that creating story with non-existent epic raises ValueError."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)

    # Mock epic not found
    epic_id = EpicId("E-NONEXISTENT")
    storage.get_epic.return_value = None

    # Act & Assert: Should raise ValueError
    with pytest.raises(ValueError, match="Epic.*not found"):
        await use_case.execute(
            epic_id=epic_id,
            title=Title("Test"),
            brief=Brief("Test brief"),
            created_by=UserName("po"),
        )

    # Assert: Story not saved
    storage.save_story.assert_not_awaited()

    # Assert: Event not published
    messaging.publish_story_created.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_story_messaging_failure_propagates():
    """Test that messaging failures are propagated."""
    storage = AsyncMock()
    messaging = AsyncMock()
    messaging.publish_story_created.side_effect = Exception("Messaging error")
    use_case = CreateStoryUseCase(storage=storage, messaging=messaging)

    # Mock parent epic
    epic_id = EpicId("E-TEST-005")
    mock_epic = Epic(
        epic_id=epic_id,
        project_id=ProjectId("PROJ-TEST-005"),
        title="Test Epic",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_epic.return_value = mock_epic

    # Act & Assert: Should raise exception
    with pytest.raises(Exception, match="Messaging error"):
        await use_case.execute(
            epic_id=epic_id,
            title=Title("Test"),
            brief=Brief("Test brief"),
            created_by=UserName("po"),
        )

    # Assert: Story was saved (before messaging failure)
    storage.save_story.assert_awaited_once()
