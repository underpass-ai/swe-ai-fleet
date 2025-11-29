"""Unit tests for Plan entity."""

import pytest
from planning.domain.entities.plan import Plan
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId


class TestPlan:
    """Test suite for Plan entity."""

    def test_plan_initialization_success(self) -> None:
        """Test successful initialization of Plan."""
        # Given
        plan_id = PlanId("plan-123")
        story_ids = (StoryId("story-123"), StoryId("story-456"))
        title = Title("Implementation Plan")
        description = Brief("Detailed technical plan")
        acceptance_criteria = ("Criterion 1", "Criterion 2")
        technical_notes = "Use Python"
        roles = ("developer",)

        # When
        plan = Plan(
            plan_id=plan_id,
            story_ids=story_ids,
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            technical_notes=technical_notes,
            roles=roles,
        )

        # Then
        assert plan.plan_id == plan_id
        assert plan.story_ids == story_ids
        assert plan.title == title
        assert plan.description == description
        assert plan.acceptance_criteria == acceptance_criteria
        assert plan.technical_notes == technical_notes
        assert plan.roles == roles

    def test_plan_initialization_fails_empty_story_ids(self) -> None:
        """Test validation fails when story_ids is empty."""
        # Given
        plan_id = PlanId("plan-123")
        story_ids = ()  # Empty tuple
        title = Title("Implementation Plan")
        description = Brief("Detailed technical plan")
        acceptance_criteria = ("Criterion 1",)

        # When/Then
        with pytest.raises(ValueError, match="Plan must cover at least one Story"):
            Plan(
                plan_id=plan_id,
                story_ids=story_ids,
                title=title,
                description=description,
                acceptance_criteria=acceptance_criteria,
            )

    def test_plan_initialization_fails_empty_acceptance_criteria(self) -> None:
        """Test validation fails when acceptance_criteria is empty."""
        # Given
        plan_id = PlanId("plan-123")
        story_ids = (StoryId("story-123"),)
        title = Title("Implementation Plan")
        description = Brief("Detailed technical plan")
        acceptance_criteria = ()  # Empty tuple

        # When/Then
        with pytest.raises(ValueError, match="Plan must have at least one acceptance criterion"):
            Plan(
                plan_id=plan_id,
                story_ids=story_ids,
                title=title,
                description=description,
                acceptance_criteria=acceptance_criteria,
            )

    def test_get_description_for_decomposition(self) -> None:
        """Test get_description_for_decomposition method."""
        # Given
        plan = Plan(
            plan_id=PlanId("plan-1"),
            story_ids=(StoryId("story-1"),),
            title=Title("Title"),
            description=Brief("Description text"),
            acceptance_criteria=("AC1",),
        )

        # When
        result = plan.get_description_for_decomposition()

        # Then
        assert result == "Description text"

    def test_get_acceptance_criteria_text(self) -> None:
        """Test get_acceptance_criteria_text method."""
        # Given
        plan = Plan(
            plan_id=PlanId("plan-1"),
            story_ids=(StoryId("story-1"),),
            title=Title("Title"),
            description=Brief("Description"),
            acceptance_criteria=("Verify A", "Check B"),
        )

        # When
        result = plan.get_acceptance_criteria_text()

        # Then
        assert result == "- Verify A\n- Check B"

    def test_get_technical_notes_text(self) -> None:
        """Test get_technical_notes_text method."""
        # Case 1: With notes
        plan_with_notes = Plan(
            plan_id=PlanId("plan-1"),
            story_ids=(StoryId("story-1"),),
            title=Title("Title"),
            description=Brief("Description"),
            acceptance_criteria=("AC1",),
            technical_notes="Use Redis",
        )
        assert plan_with_notes.get_technical_notes_text() == "Use Redis"

        # Case 2: Without notes (empty string)
        plan_without_notes = Plan(
            plan_id=PlanId("plan-2"),
            story_ids=(StoryId("story-2"),),
            title=Title("Title"),
            description=Brief("Description"),
            acceptance_criteria=("AC1",),
            technical_notes="",
        )
        assert plan_without_notes.get_technical_notes_text() == "Not specified"

