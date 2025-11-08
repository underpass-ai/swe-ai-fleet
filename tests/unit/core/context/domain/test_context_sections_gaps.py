"""Unit tests for ContextSections - covering edge cases and gaps."""

import pytest

from core.context.domain.context_sections import ContextSections
from core.context.domain.value_objects.context_section import ContextSection
from core.context.domain.context_section_type import ContextSectionType
from core.reports.domain.decision_node import DecisionNode
from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.entity_ids.actor_id import ActorId
from core.context.domain.decision_status import DecisionStatus


class TestContextSectionGaps:
    """Tests to cover uncovered branches in ContextSections"""

    def test_add_decision_context_empty_list(self) -> None:
        """Test add_decision_context with empty decisions list (line 60)."""
        sections = ContextSections()
        sections.add_decision_context([])
        
        # Should return early without adding section
        assert sections.is_empty()

    def test_add_decision_context_without_rationale(self) -> None:
        """Test that add_decision_context handles decisions with empty rationale."""
        sections = ContextSections()

        # Decision with empty rationale
        decisions = [
            DecisionNode(
                id=DecisionId(value="dec-001"),
                title="Use microservices",
                rationale="",  # Empty rationale
                status=DecisionStatus.APPROVED,
                created_at_ms=1234567890,
                author_id=ActorId(value="architect-1"),
            ),
        ]

        sections.add_decision_context(decisions)

        # Check decision section exists (should be in section_type DECISION_CONTEXT)
        decision_sections = [s for s in sections.sections if s.section_type == ContextSectionType.DECISION_CONTEXT]
        
        assert len(decision_sections) > 0
        content = decision_sections[0].content
        assert "dec-001" in content
        assert "Use microservices" in content

    def test_add_decision_context_mixed_with_without_rationale(self) -> None:
        """Test mixed decisions (some with rationale, some without)."""
        sections = ContextSections()

        decisions = [
            DecisionNode(
                id=DecisionId(value="dec-001"),
                title="Use microservices",
                rationale="Better scalability",
                status=DecisionStatus.APPROVED,
                created_at_ms=1234567890,
                author_id=ActorId(value="architect-1"),
            ),
            DecisionNode(
                id=DecisionId(value="dec-002"),
                title="Use GraphQL",
                rationale="",  # Empty rationale
                status=DecisionStatus.PROPOSED,
                created_at_ms=1234567891,
                author_id=ActorId(value="architect-2"),
            ),
            DecisionNode(
                id=DecisionId(value="dec-003"),
                title="Deploy to K8s",
                rationale="",  # Empty rationale
                status=DecisionStatus.APPROVED,
                created_at_ms=1234567892,
                author_id=ActorId(value="architect-1"),
            ),
        ]

        sections.add_decision_context(decisions)

        # All decisions should be added
        decision_sections = [s for s in sections.sections if s.section_type == ContextSectionType.DECISION_CONTEXT]
        
        assert len(decision_sections) > 0
        content = decision_sections[0].content
        assert "dec-001" in content
        assert "dec-002" in content
        assert "dec-003" in content
        assert "Better scalability" in content

    def test_context_section_str(self) -> None:
        """Test ContextSection __str__ method."""
        section = ContextSection(
            content="Test content",
            section_type=ContextSectionType.STORY_IDENTIFICATION,
            priority=5,
        )
        
        assert str(section) == "Test content"

    def test_to_string_ordering(self) -> None:
        """Test to_string properly orders by priority (high → low)."""
        sections = ContextSections()
        
        sections.add_section("Low priority", ContextSectionType.DECISION_CONTEXT, priority=10)
        sections.add_section("High priority", ContextSectionType.STORY_IDENTIFICATION, priority=100)
        sections.add_section("Medium priority", ContextSectionType.ROLE_TASKS, priority=50)
        
        result = sections.to_string()
        lines = result.split("\n")
        
        # Should be ordered: high (100), medium (50), low (10)
        assert lines[0] == "High priority"
        assert lines[1] == "Medium priority"
        assert lines[2] == "Low priority"

    def test_is_empty_true(self) -> None:
        """Test is_empty returns True for empty sections."""
        sections = ContextSections()
        assert sections.is_empty()

    def test_is_empty_false(self) -> None:
        """Test is_empty returns False after adding section."""
        sections = ContextSections()
        sections.add_section("Content", ContextSectionType.STORY_IDENTIFICATION)
        assert not sections.is_empty()

    def test_get_sections_by_type(self) -> None:
        """Test get_sections_by_type filters correctly."""
        sections = ContextSections()
        
        sections.add_section("Decision 1", ContextSectionType.DECISION_CONTEXT, priority=100)
        sections.add_section("Decision 2", ContextSectionType.DECISION_CONTEXT, priority=90)
        sections.add_section("Story info", ContextSectionType.STORY_IDENTIFICATION, priority=80)
        
        decision_sections = sections.get_sections_by_type(ContextSectionType.DECISION_CONTEXT)
        assert len(decision_sections) == 2
        
        story_sections = sections.get_sections_by_type(ContextSectionType.STORY_IDENTIFICATION)
        assert len(story_sections) == 1

    def test_clear(self) -> None:
        """Test clear removes all sections."""
        sections = ContextSections()
        sections.add_section("Content 1", ContextSectionType.DECISION_CONTEXT)
        sections.add_section("Content 2", ContextSectionType.STORY_IDENTIFICATION)
        
        assert not sections.is_empty()
        
        sections.clear()
        assert sections.is_empty()
        assert len(sections.sections) == 0
