"""Unit tests for CreateEpicUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from planning.application.usecases.create_epic_usecase import CreateEpicUseCase
from planning.domain.entities.epic import Epic
from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.statuses.epic_status import EpicStatus
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus


@pytest.mark.asyncio
async def test_create_epic_success():
    """Test successful epic creation with valid parent project."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateEpicUseCase(storage=storage, messaging=messaging)

    # Mock parent project (domain invariant validation)
    project_id = ProjectId("PROJ-TEST-001")
    mock_project = Project(
        project_id=project_id,
        name="Test Project",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_project.return_value = mock_project

    # Act
    epic = await use_case.execute(
        project_id=project_id,
        title="Backend API Development",
        description="Complete backend REST API",
    )

    # Assert
    assert epic.project_id == project_id
    assert epic.title == "Backend API Development"
    assert epic.description == "Complete backend REST API"
    assert epic.status == EpicStatus.ACTIVE
    assert isinstance(epic.epic_id, EpicId)

    # Verify epic was saved
    storage.save_epic.assert_awaited_once()
    saved_epic = storage.save_epic.call_args[0][0]
    assert saved_epic.title == "Backend API Development"

    # Verify event was published
    messaging.publish_event.assert_awaited_once()
    call_args = messaging.publish_event.call_args
    assert call_args[1]["topic"] == "planning.epic.created"


@pytest.mark.asyncio
async def test_create_epic_generates_unique_id():
    """Test that epic ID is auto-generated and unique."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateEpicUseCase(storage=storage, messaging=messaging)

    # Mock parent project
    project_id = ProjectId("PROJ-TEST-002")
    mock_project = Project(
        project_id=project_id,
        name="Test Project",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_project.return_value = mock_project

    # Create two epics
    epic1 = await use_case.execute(project_id=project_id, title="Epic 1")
    epic2 = await use_case.execute(project_id=project_id, title="Epic 2")

    # IDs should be different
    assert epic1.epic_id != epic2.epic_id
    assert epic1.epic_id.value.startswith("E-")
    assert epic2.epic_id.value.startswith("E-")


@pytest.mark.asyncio
async def test_create_epic_rejects_nonexistent_project():
    """Test that creating epic without valid parent project fails."""
    storage = AsyncMock()
    storage.get_project.return_value = None  # Project not found
    messaging = AsyncMock()
    use_case = CreateEpicUseCase(storage=storage, messaging=messaging)

    project_id = ProjectId("NONEXISTENT")

    with pytest.raises(ValueError, match="Project .* not found"):
        await use_case.execute(
            project_id=project_id,
            title="Orphan Epic",
        )

    # Epic should not be saved
    storage.save_epic.assert_not_awaited()
    # Event should not be published
    messaging.publish_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_epic_rejects_empty_title():
    """Test that empty title is rejected (domain validation)."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateEpicUseCase(storage=storage, messaging=messaging)

    # Mock parent project
    project_id = ProjectId("PROJ-TEST-003")
    mock_project = Project(
        project_id=project_id,
        name="Test Project",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_project.return_value = mock_project

    with pytest.raises(ValueError, match="title cannot be empty"):
        await use_case.execute(
            project_id=project_id,
            title="",
        )


@pytest.mark.asyncio
async def test_create_epic_sets_timestamps():
    """Test that created_at and updated_at are set."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateEpicUseCase(storage=storage, messaging=messaging)

    # Mock parent project
    project_id = ProjectId("PROJ-TEST-004")
    mock_project = Project(
        project_id=project_id,
        name="Test Project",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_project.return_value = mock_project

    before = datetime.now(UTC)
    epic = await use_case.execute(project_id=project_id, title="Test Epic")
    after = datetime.now(UTC)

    # Timestamps should be within test execution window
    assert before <= epic.created_at <= after
    assert before <= epic.updated_at <= after
    # Timestamps should be very close (within 1 second)
    delta = abs((epic.updated_at - epic.created_at).total_seconds())
    assert delta < 1.0, f"Timestamps differ by {delta}s"


@pytest.mark.asyncio
async def test_create_epic_storage_failure_propagates():
    """Test that storage failures are propagated."""
    storage = AsyncMock()
    storage.save_epic.side_effect = Exception("Storage error")
    messaging = AsyncMock()
    use_case = CreateEpicUseCase(storage=storage, messaging=messaging)

    # Mock parent project
    project_id = ProjectId("PROJ-TEST-005")
    mock_project = Project(
        project_id=project_id,
        name="Test Project",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_project.return_value = mock_project

    with pytest.raises(Exception, match="Storage error"):
        await use_case.execute(project_id=project_id, title="Test Epic")

    # Event should not be published on storage failure
    messaging.publish_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_epic_with_minimal_data():
    """Test creating epic with only required fields."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateEpicUseCase(storage=storage, messaging=messaging)

    # Mock parent project
    project_id = ProjectId("PROJ-TEST-006")
    mock_project = Project(
        project_id=project_id,
        name="Test Project",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    storage.get_project.return_value = mock_project

    epic = await use_case.execute(
        project_id=project_id,
        title="Minimal Epic",
    )

    assert epic.title == "Minimal Epic"
    assert epic.description == ""  # Default
    assert epic.status == EpicStatus.ACTIVE

