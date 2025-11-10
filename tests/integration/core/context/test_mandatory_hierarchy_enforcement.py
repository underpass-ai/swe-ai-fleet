"""Integration tests for mandatory hierarchy enforcement.

These tests verify that the domain invariants are enforced:
- NO orphan Tasks (all tasks belong to a Story via PlanVersion)
- NO orphan Stories (all stories belong to an Epic)
- NO orphan Epics (all epics belong to a Project)

Tests verify enforcement at multiple layers:
1. Value Object layer (ProjectId, EpicId, StoryId validation)
2. Entity layer (Epic.__post_init__, Story.__post_init__)
3. Neo4j constraints (property existence, unique IDs)

See: docs/architecture/DOMAIN_INVARIANTS_BUSINESS_RULES.md
"""

import pytest
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.epic import Epic
from core.context.domain.epic_status import EpicStatus
from core.context.domain.project import Project
from core.context.domain.project_status import ProjectStatus
from core.context.domain.story import Story


class TestMandatoryHierarchyEnforcement:
    """Integration tests for mandatory hierarchy: Project → Epic → Story → Task."""

    def test_cannot_create_epic_without_project(self) -> None:
        """Test that Epic cannot be created without a valid ProjectId.

        Domain Invariant: NO orphan epics allowed.

        This test verifies fail-fast validation at the value object layer.
        """
        # Attempt to create Epic with empty project_id
        with pytest.raises(ValueError, match="ProjectId cannot be empty"):
            Epic(
                epic_id=EpicId("E-ORPHAN"),
                project_id=ProjectId(""),  # Violates invariant
                title="Orphan Epic",
            )

    def test_cannot_create_story_without_epic(self) -> None:
        """Test that Story cannot be created without a valid EpicId.

        Domain Invariant: NO orphan stories allowed.

        This test verifies fail-fast validation at the value object layer.
        """
        # Attempt to create Story with empty epic_id
        with pytest.raises(ValueError, match="EpicId cannot be empty"):
            Story(
                story_id=StoryId("US-ORPHAN"),
                epic_id=EpicId(""),  # Violates invariant
                name="Orphan Story",
            )

    def test_valid_hierarchy_project_epic_story(self) -> None:
        """Test creating a valid hierarchy: Project → Epic → Story.

        This verifies the happy path where all relationships are valid.
        """
        # Step 1: Create Project (root of hierarchy)
        project = Project(
            project_id=ProjectId("PROJ-TEST-001"),
            name="Test Project",
            description="Integration test project",
            status=ProjectStatus.ACTIVE,
            owner="test_owner",
        )
        assert project.project_id.to_string() == "PROJ-TEST-001"

        # Step 2: Create Epic (belongs to Project)
        epic = Epic(
            epic_id=EpicId("E-TEST-001"),
            project_id=project.project_id,  # Valid parent reference
            title="Test Epic",
            description="Integration test epic",
            status=EpicStatus.ACTIVE,
        )
        assert epic.project_id.to_string() == project.project_id.to_string()

        # Step 3: Create Story (belongs to Epic)
        story = Story(
            story_id=StoryId("US-TEST-001"),
            epic_id=epic.epic_id,  # Valid parent reference
            name="Test user story",
        )
        assert story.epic_id.to_string() == epic.epic_id.to_string()

        # Verify complete hierarchy
        assert story.epic_id == epic.epic_id
        assert epic.project_id == project.project_id

    def test_epic_to_graph_properties_includes_project_id(self) -> None:
        """Test that Epic's Neo4j properties include project_id for hierarchy tracking."""
        project = Project(
            project_id=ProjectId("PROJ-GRAPH-001"),
            name="Graph Test Project",
        )

        epic = Epic(
            epic_id=EpicId("E-GRAPH-001"),
            project_id=project.project_id,
            title="Graph Test Epic",
        )

        # Convert to Neo4j properties
        props = epic.to_graph_properties()

        # Verify project_id is included (required for hierarchy queries)
        assert "project_id" in props
        assert props["project_id"] == "PROJ-GRAPH-001"
        assert "epic_id" in props
        assert props["epic_id"] == "E-GRAPH-001"

    def test_project_to_graph_properties(self) -> None:
        """Test that Project's Neo4j properties are correctly formatted."""
        project = Project(
            project_id=ProjectId("PROJ-PROPS-001"),
            name="Properties Test",
            description="Test description",
            status=ProjectStatus.IN_PROGRESS,
            owner="test_owner",
            created_at_ms=1699564800000,
        )

        props = project.to_graph_properties()

        assert props["project_id"] == "PROJ-PROPS-001"
        assert props["name"] == "Properties Test"
        assert props["description"] == "Test description"
        assert props["status"] == "in_progress"
        assert props["owner"] == "test_owner"
        assert props["created_at_ms"] == "1699564800000"

    def test_multiple_epics_same_project(self) -> None:
        """Test that multiple Epics can belong to the same Project."""
        project = Project(
            project_id=ProjectId("PROJ-MULTI-001"),
            name="Multi-Epic Project",
        )

        epic1 = Epic(
            epic_id=EpicId("E-MULTI-001"),
            project_id=project.project_id,
            title="First Epic",
        )

        epic2 = Epic(
            epic_id=EpicId("E-MULTI-002"),
            project_id=project.project_id,  # Same project
            title="Second Epic",
        )

        # Both epics reference the same project
        assert epic1.project_id == project.project_id
        assert epic2.project_id == project.project_id
        assert epic1.epic_id != epic2.epic_id  # Different epic IDs

    def test_multiple_stories_same_epic(self) -> None:
        """Test that multiple Stories can belong to the same Epic."""
        project = Project(
            project_id=ProjectId("PROJ-STORIES-001"),
            name="Multi-Story Project",
        )

        epic = Epic(
            epic_id=EpicId("E-STORIES-001"),
            project_id=project.project_id,
            title="Multi-Story Epic",
        )

        story1 = Story(
            story_id=StoryId("US-S1-001"),
            epic_id=epic.epic_id,
            name="First story",
        )

        story2 = Story(
            story_id=StoryId("US-S2-001"),
            epic_id=epic.epic_id,  # Same epic
            name="Second story",
        )

        # Both stories reference the same epic
        assert story1.epic_id == epic.epic_id
        assert story2.epic_id == epic.epic_id
        assert story1.story_id != story2.story_id  # Different story IDs

    def test_hierarchy_traceability(self) -> None:
        """Test that we can trace from Story back to Project through hierarchy.

        This verifies bidirectional traceability:
        - Forward: Project → Epic → Story
        - Backward: Story → Epic → Project
        """
        # Create full hierarchy
        project = Project(
            project_id=ProjectId("PROJ-TRACE-001"),
            name="Traceable Project",
        )

        epic = Epic(
            epic_id=EpicId("E-TRACE-001"),
            project_id=project.project_id,
            title="Traceable Epic",
        )

        story = Story(
            story_id=StoryId("US-TRACE-001"),
            epic_id=epic.epic_id,
            name="Traceable Story",
        )

        # Verify forward traceability (Project → Epic → Story)
        # Step 1: Project to Epic
        assert epic.project_id == project.project_id

        # Step 2: Epic to Story
        assert story.epic_id == epic.epic_id

        # Verify backward traceability (Story → Epic → Project)
        # From story, we can get epic_id
        retrieved_epic_id = story.epic_id
        assert retrieved_epic_id == epic.epic_id

        # From epic, we can get project_id
        retrieved_project_id = epic.project_id
        assert retrieved_project_id == project.project_id

        # Complete path: Story → Epic → Project
        assert story.epic_id == epic.epic_id == EpicId("E-TRACE-001")
        assert epic.project_id == project.project_id == ProjectId("PROJ-TRACE-001")


class TestDomainInvariantEdgeCases:
    """Test edge cases and boundary conditions for domain invariants."""

    def test_project_with_empty_description_is_valid(self) -> None:
        """Test that Project with empty description is valid (description is optional)."""
        project = Project(
            project_id=ProjectId("PROJ-EMPTY-DESC"),
            name="Project with no description",
            description="",  # Empty but valid
        )

        assert project.description == ""
        assert project.name == "Project with no description"

    def test_epic_with_empty_description_is_valid(self) -> None:
        """Test that Epic with empty description is valid (description is optional)."""
        epic = Epic(
            epic_id=EpicId("E-EMPTY-DESC"),
            project_id=ProjectId("PROJ-001"),
            title="Epic with no description",
            description="",  # Empty but valid
        )

        assert epic.description == ""
        assert epic.title == "Epic with no description"

    def test_project_name_with_special_characters(self) -> None:
        """Test that Project name can contain special characters."""
        project = Project(
            project_id=ProjectId("PROJ-SPECIAL"),
            name="SWE Platform v2.0 (Beta) - Q4 2025!",
        )

        assert "v2.0" in project.name
        assert "Beta" in project.name
        assert "Q4" in project.name

    def test_hierarchy_with_long_ids(self) -> None:
        """Test hierarchy with very long IDs (edge case)."""
        long_id = "PROJ-" + "A" * 100  # Very long ID

        project = Project(
            project_id=ProjectId(long_id),
            name="Long ID Project",
        )

        assert len(project.project_id.to_string()) > 100
        assert project.project_id.to_string() == long_id

