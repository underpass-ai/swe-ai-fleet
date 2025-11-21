"""Unit tests for ProjectId value object."""

import pytest
from core.context.domain.entity_ids.project_id import ProjectId


class TestProjectId:
    """Test suite for ProjectId value object."""

    def test_create_valid_project_id(self) -> None:
        """Test creating a valid project ID."""
        project_id = ProjectId("PROJ-001")

        assert project_id.value == "PROJ-001"
        assert project_id.to_string() == "PROJ-001"
        assert str(project_id) == "PROJ-001"

    def test_project_id_cannot_be_empty(self) -> None:
        """Test that ProjectId cannot be empty string."""
        with pytest.raises(ValueError, match="ProjectId cannot be empty"):
            ProjectId("")

    def test_project_id_cannot_be_whitespace(self) -> None:
        """Test that ProjectId cannot be whitespace-only."""
        with pytest.raises(ValueError, match="ProjectId cannot be empty"):
            ProjectId("   ")

    def test_project_id_immutability(self) -> None:
        """Test that ProjectId is immutable (frozen dataclass)."""
        project_id = ProjectId("PROJ-001")

        with pytest.raises(AttributeError):
            project_id.value = "PROJ-002"  # type: ignore[misc]

    def test_project_id_equality(self) -> None:
        """Test ProjectId equality comparison."""
        id1 = ProjectId("PROJ-001")
        id2 = ProjectId("PROJ-001")
        id3 = ProjectId("PROJ-002")

        assert id1 == id2
        assert id1 != id3

