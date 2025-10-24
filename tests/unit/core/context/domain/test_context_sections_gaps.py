"""Unit tests for context_sections gaps - quick coverage completion

Tests for uncovered branches in ContextSections module.
"""

import pytest

from core.context.domain.context_sections import ContextSection, ContextSections


class TestContextSectionGaps:
    """Tests to cover uncovered branches in ContextSections"""

    def test_add_decision_context_empty_list(self):
        """Test add_decision_context with empty decisions list (line 60)."""
        sections = ContextSections()
        sections.add_decision_context([])
        
        # Should return early without adding section
        assert sections.is_empty()

    def test_add_decision_context_without_rationale(self):
        """Test add_decision_context where decisions lack rationale (line 74 else branch)."""
        sections = ContextSections()
        decisions = [
            {
                "id": "dec-001",
                "title": "Use Docker",
                "status": "APPROVED",
                # No rationale provided
            }
        ]
        sections.add_decision_context(decisions)
        
        # Should add section with simple format (no rationale line)
        assert len(sections.sections) == 1
        section_content = sections.sections[0].content
        assert "Use Docker" in section_content
        assert "APPROVED" in section_content
        # Should NOT have the extra rationale line
        lines = section_content.split("\n")
        assert len(lines) == 2  # Header + 1 decision line

    def test_add_decision_context_mixed_with_without_rationale(self):
        """Test add_decision_context with mixed decisions."""
        sections = ContextSections()
        decisions = [
            {
                "id": "dec-001",
                "title": "Decision 1",
                "status": "APPROVED",
                "rationale": "Good idea",
            },
            {
                "id": "dec-002",
                "title": "Decision 2",
                "status": "PROPOSED",
                # No rationale
            }
        ]
        sections.add_decision_context(decisions)
        
        assert len(sections.sections) == 1
        content = sections.sections[0].content
        assert "Good idea" in content
        assert "Decision 2" in content

    def test_context_section_str(self):
        """Test ContextSection __str__ method."""
        section = ContextSection(
            content="Test content",
            section_type="test",
            priority=5,
        )
        
        assert str(section) == "Test content"

    def test_to_string_ordering(self):
        """Test to_string properly orders by priority (high → low)."""
        sections = ContextSections()
        
        sections.add_section("Low priority", "low", priority=10)
        sections.add_section("High priority", "high", priority=100)
        sections.add_section("Medium priority", "medium", priority=50)
        
        result = sections.to_string()
        lines = result.split("\n")
        
        # Should be ordered: high (100), medium (50), low (10)
        assert lines[0] == "High priority"
        assert lines[1] == "Medium priority"
        assert lines[2] == "Low priority"

    def test_is_empty_true(self):
        """Test is_empty returns True for empty sections."""
        sections = ContextSections()
        assert sections.is_empty()

    def test_is_empty_false(self):
        """Test is_empty returns False after adding section."""
        sections = ContextSections()
        sections.add_section("Content", "type")
        assert not sections.is_empty()

    def test_get_sections_by_type(self):
        """Test get_sections_by_type filters correctly."""
        sections = ContextSections()
        
        sections.add_section("Decision 1", "decision", priority=100)
        sections.add_section("Decision 2", "decision", priority=90)
        sections.add_section("Case info", "case", priority=80)
        
        decision_sections = sections.get_sections_by_type("decision")
        assert len(decision_sections) == 2
        
        case_sections = sections.get_sections_by_type("case")
        assert len(case_sections) == 1

    def test_clear(self):
        """Test clear removes all sections."""
        sections = ContextSections()
        sections.add_section("Content 1", "type1")
        sections.add_section("Content 2", "type2")
        
        assert not sections.is_empty()
        
        sections.clear()
        assert sections.is_empty()
        assert len(sections.sections) == 0
