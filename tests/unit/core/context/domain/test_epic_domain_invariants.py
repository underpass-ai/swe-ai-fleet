"""Unit tests for Epic domain invariants (mandatory hierarchy)."""

import pytest
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.epic import Epic
from core.context.domain.epic_status import EpicStatus


class TestEpicDomainInvariants:
    """Test suite for Epic domain invariants - mandatory hierarchy enforcement."""

    def test_epic_with_valid_project_id(self) -> None:
        """Test creating Epic with valid project_id (happy path)."""
        epic = Epic(
            epic_id=EpicId("E-001"),
            project_id=ProjectId("PROJ-001"),  # Valid project reference
            title="Authentication System",
            description="Complete auth infrastructure",
            status=EpicStatus.ACTIVE,
        )

        assert epic.project_id.to_string() == "PROJ-001"
        assert epic.title == "Authentication System"

    def test_epic_without_project_id_raises_error(self) -> None:
        """Test that Epic MUST have project_id (domain invariant).

        Domain Rule: NO orphan epics allowed.
        Every Epic MUST belong to a Project.

        Note: Validation happens in ProjectId value object (fail-fast).
        This is correct layered validation.
        """
        with pytest.raises(ValueError, match="ProjectId cannot be empty"):
            Epic(
                epic_id=EpicId("E-001"),
                project_id=ProjectId(""),  # Empty project_id violates invariant
                title="Orphan Epic",
            )

    def test_epic_with_whitespace_project_id_raises_error(self) -> None:
        """Test that project_id cannot be whitespace-only.

        Note: Validation happens in ProjectId value object (fail-fast).
        """
        with pytest.raises(ValueError, match="ProjectId cannot be empty"):
            Epic(
                epic_id=EpicId("E-001"),
                project_id=ProjectId("   "),  # Whitespace-only violates invariant
                title="Invalid Epic",
            )

    def test_epic_to_graph_properties_includes_project_id(self) -> None:
        """Test that Neo4j properties include project_id."""
        epic = Epic(
            epic_id=EpicId("E-001"),
            project_id=ProjectId("PROJ-001"),
            title="Test Epic",
            description="Test description",
            status=EpicStatus.PLANNING,
            created_at_ms=1699564800000,
        )

        props = epic.to_graph_properties()

        # Must include project_id for hierarchy tracking
        assert "project_id" in props
        assert props["project_id"] == "PROJ-001"
        assert props["epic_id"] == "E-001"
        assert props["title"] == "Test Epic"
        assert props["status"] == "planning"

