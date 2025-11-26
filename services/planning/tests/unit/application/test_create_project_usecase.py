"""Unit tests for CreateProjectUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.usecases.create_project_usecase import CreateProjectUseCase
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus


@pytest.mark.asyncio
async def test_create_project_success():
    """Test successful project creation."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateProjectUseCase(storage=storage, messaging=messaging)

    # Act
    project = await use_case.execute(
        name="SWE AI Fleet",
        description="Autonomous software engineering system",
        owner="tirso",
    )

    # Assert
    assert project.name == "SWE AI Fleet"
    assert project.description == "Autonomous software engineering system"
    assert project.owner == "tirso"
    assert project.status == ProjectStatus.ACTIVE
    assert isinstance(project.project_id, ProjectId)

    # Verify project was saved
    storage.save_project.assert_awaited_once()
    saved_project = storage.save_project.call_args[0][0]
    assert saved_project.name == "SWE AI Fleet"

    # Verify event was published
    messaging.publish_event.assert_awaited_once()
    call_args = messaging.publish_event.call_args
    assert call_args.kwargs["subject"] == "planning.project.created"
    assert "payload" in call_args.kwargs
    assert "project_id" in call_args.kwargs["payload"]


@pytest.mark.asyncio
async def test_create_project_generates_unique_id():
    """Test that project ID is auto-generated and unique."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateProjectUseCase(storage=storage, messaging=messaging)

    # Create two projects
    project1 = await use_case.execute(name="Project 1")
    project2 = await use_case.execute(name="Project 2")

    # IDs should be different
    assert project1.project_id != project2.project_id
    assert project1.project_id.value.startswith("PROJ-")
    assert project2.project_id.value.startswith("PROJ-")


@pytest.mark.asyncio
async def test_create_project_sets_timestamps():
    """Test that created_at and updated_at are set."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateProjectUseCase(storage=storage, messaging=messaging)

    before = datetime.now(UTC)
    project = await use_case.execute(name="Test Project")
    after = datetime.now(UTC)

    # Timestamps should be within test execution window
    assert before <= project.created_at <= after
    assert before <= project.updated_at <= after
    # Timestamps should be very close (within 1 second)
    delta = abs((project.updated_at - project.created_at).total_seconds())
    assert delta < 1.0, f"Timestamps differ by {delta}s"


@pytest.mark.asyncio
async def test_create_project_rejects_empty_name():
    """Test that empty name is rejected (domain validation)."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateProjectUseCase(storage=storage, messaging=messaging)

    with pytest.raises(ValueError, match="name cannot be empty"):
        await use_case.execute(name="")


@pytest.mark.asyncio
async def test_create_project_rejects_whitespace_name():
    """Test that whitespace-only name is rejected."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateProjectUseCase(storage=storage, messaging=messaging)

    with pytest.raises(ValueError, match="name cannot be empty"):
        await use_case.execute(name="   ")


@pytest.mark.asyncio
async def test_create_project_with_minimal_data():
    """Test creating project with only required fields."""
    storage = AsyncMock()
    messaging = AsyncMock()
    use_case = CreateProjectUseCase(storage=storage, messaging=messaging)

    project = await use_case.execute(name="Minimal Project")

    assert project.name == "Minimal Project"
    assert project.description == ""  # Default
    assert project.owner == ""  # Default
    assert project.status == ProjectStatus.ACTIVE


@pytest.mark.asyncio
async def test_create_project_storage_failure_propagates():
    """Test that storage failures are propagated."""
    storage = AsyncMock()
    storage.save_project.side_effect = Exception("Storage error")
    messaging = AsyncMock()
    use_case = CreateProjectUseCase(storage=storage, messaging=messaging)

    with pytest.raises(Exception, match="Storage error"):
        await use_case.execute(name="Test Project")

    # Event should not be published on storage failure
    messaging.publish_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_project_messaging_failure_propagates():
    """Test that messaging failures are propagated."""
    storage = AsyncMock()
    messaging = AsyncMock()
    messaging.publish_event.side_effect = Exception("NATS error")
    use_case = CreateProjectUseCase(storage=storage, messaging=messaging)

    with pytest.raises(Exception, match="NATS error"):
        await use_case.execute(name="Test Project")

    # Project should have been saved before messaging failure
    storage.save_project.assert_awaited_once()

