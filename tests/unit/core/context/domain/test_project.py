"""Unit tests for Project domain entity."""

import pytest
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.project import Project
from core.context.domain.project_status import ProjectStatus


class TestProject:
    """Test suite for Project entity."""

    def test_create_project_happy_path(self) -> None:
        """Test creating a valid project."""
        project = Project(
            project_id=ProjectId("PROJ-001"),
            name="SWE Platform v1",
            description="Complete SWE AI platform",
            status=ProjectStatus.ACTIVE,
            owner="tirso",
            created_at_ms=1699564800000,
        )

        assert project.project_id.to_string() == "PROJ-001"
        assert project.name == "SWE Platform v1"
        assert project.status == ProjectStatus.ACTIVE
        assert project.owner == "tirso"

    def test_project_name_cannot_be_empty(self) -> None:
        """Test that project name cannot be empty (domain invariant)."""
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            Project(
                project_id=ProjectId("PROJ-001"),
                name="",  # Empty name violates invariant
                description="Test",
            )

    def test_project_name_cannot_be_whitespace(self) -> None:
        """Test that project name cannot be only whitespace."""
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            Project(
                project_id=ProjectId("PROJ-001"),
                name="   ",  # Whitespace-only violates invariant
                description="Test",
            )

    def test_created_at_ms_cannot_be_negative(self) -> None:
        """Test that created_at_ms cannot be negative."""
        with pytest.raises(ValueError, match="created_at_ms cannot be negative"):
            Project(
                project_id=ProjectId("PROJ-001"),
                name="Valid Name",
                created_at_ms=-1,  # Negative timestamp invalid
            )

    def test_project_is_active(self) -> None:
        """Test is_active() method."""
        active_project = Project(
            project_id=ProjectId("PROJ-001"),
            name="Active Project",
            status=ProjectStatus.ACTIVE,
        )
        assert active_project.is_active() is True

        in_progress_project = Project(
            project_id=ProjectId("PROJ-002"),
            name="In Progress",
            status=ProjectStatus.IN_PROGRESS,
        )
        assert in_progress_project.is_active() is True

        completed_project = Project(
            project_id=ProjectId("PROJ-003"),
            name="Completed",
            status=ProjectStatus.COMPLETED,
        )
        assert completed_project.is_active() is False

    def test_project_is_completed(self) -> None:
        """Test is_completed() method."""
        completed = Project(
            project_id=ProjectId("PROJ-001"),
            name="Done",
            status=ProjectStatus.COMPLETED,
        )
        assert completed.is_completed() is True

        active = Project(
            project_id=ProjectId("PROJ-002"),
            name="Active",
            status=ProjectStatus.ACTIVE,
        )
        assert active.is_completed() is False

    def test_project_is_terminal(self) -> None:
        """Test is_terminal() method."""
        completed = Project(
            project_id=ProjectId("PROJ-001"),
            name="Done",
            status=ProjectStatus.COMPLETED,
        )
        assert completed.is_terminal() is True

        archived = Project(
            project_id=ProjectId("PROJ-002"),
            name="Archived",
            status=ProjectStatus.ARCHIVED,
        )
        assert archived.is_terminal() is True

        cancelled = Project(
            project_id=ProjectId("PROJ-003"),
            name="Cancelled",
            status=ProjectStatus.CANCELLED,
        )
        assert cancelled.is_terminal() is True

        active = Project(
            project_id=ProjectId("PROJ-004"),
            name="Active",
            status=ProjectStatus.ACTIVE,
        )
        assert active.is_terminal() is False

    def test_to_graph_properties(self) -> None:
        """Test conversion to Neo4j properties."""
        project = Project(
            project_id=ProjectId("PROJ-001"),
            name="Test Project",
            description="Test description",
            status=ProjectStatus.IN_PROGRESS,
            owner="test_owner",
            created_at_ms=1699564800000,
        )

        props = project.to_graph_properties()

        assert props["project_id"] == "PROJ-001"
        assert props["name"] == "Test Project"
        assert props["description"] == "Test description"
        assert props["status"] == "in_progress"
        assert props["owner"] == "test_owner"
        assert props["created_at_ms"] == "1699564800000"

