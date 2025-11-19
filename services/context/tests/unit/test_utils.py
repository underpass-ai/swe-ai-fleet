"""Unit tests for context service utilities."""

import pytest
from unittest.mock import MagicMock

from services.context.utils import (
    detect_scopes,
    detect_case_header_scope,
    detect_plan_header_scope,
    detect_subtasks_scope,
    detect_decisions_scope,
    detect_dependencies_scope,
    detect_milestones_scope,
)


class TestDetectCaseHeaderScope:
    """Test detect_case_header_scope function."""

    def test_detects_case_header_with_case_keyword(self):
        """Test detects CASE_HEADER when 'Case:' is present."""
        content = "Case: Some case description"
        result = detect_case_header_scope(content)

        assert result == ["CASE_HEADER"]

    def test_detects_case_header_with_status_keyword(self):
        """Test detects CASE_HEADER when 'Status:' is present."""
        content = "Status: In progress"
        result = detect_case_header_scope(content)

        assert result == ["CASE_HEADER"]

    def test_detects_case_header_with_both_keywords(self):
        """Test detects CASE_HEADER when both keywords are present."""
        content = "Case: Test case\nStatus: Active"
        result = detect_case_header_scope(content)

        assert result == ["CASE_HEADER"]

    def test_returns_empty_when_no_keywords(self):
        """Test returns empty list when no keywords are present."""
        content = "Some other content without keywords"
        result = detect_case_header_scope(content)

        assert result == []

    def test_returns_empty_for_empty_string(self):
        """Test returns empty list for empty string."""
        result = detect_case_header_scope("")

        assert result == []


class TestDetectPlanHeaderScope:
    """Test detect_plan_header_scope function."""

    def test_detects_plan_header_with_plan_keyword(self):
        """Test detects PLAN_HEADER when 'Plan:' is present."""
        content = "Plan: Some plan description"
        result = detect_plan_header_scope(content)

        assert result == ["PLAN_HEADER"]

    def test_detects_plan_header_with_total_subtasks_keyword(self):
        """Test detects PLAN_HEADER when 'Total Subtasks:' is present."""
        content = "Total Subtasks: 5"
        result = detect_plan_header_scope(content)

        assert result == ["PLAN_HEADER"]

    def test_detects_plan_header_with_both_keywords(self):
        """Test detects PLAN_HEADER when both keywords are present."""
        content = "Plan: Test plan\nTotal Subtasks: 3"
        result = detect_plan_header_scope(content)

        assert result == ["PLAN_HEADER"]

    def test_returns_empty_when_no_keywords(self):
        """Test returns empty list when no keywords are present."""
        content = "Some other content"
        result = detect_plan_header_scope(content)

        assert result == []


class TestDetectSubtasksScope:
    """Test detect_subtasks_scope function."""

    def test_detects_subtasks_with_subtasks_keyword(self):
        """Test detects SUBTASKS_ROLE when 'Subtasks:' is present."""
        content = "Subtasks:\n- Task 1\n- Task 2"
        result = detect_subtasks_scope(content)

        assert result == ["SUBTASKS_ROLE"]

    def test_detects_subtasks_with_your_subtasks_keyword(self):
        """Test detects SUBTASKS_ROLE when 'Your Subtasks:' is present."""
        content = "Your Subtasks:\n- Task 1"
        result = detect_subtasks_scope(content)

        assert result == ["SUBTASKS_ROLE"]

    def test_does_not_detect_when_no_subtasks_present(self):
        """Test does not detect when 'No subtasks' is present."""
        content = "Subtasks: No subtasks"
        result = detect_subtasks_scope(content)

        assert result == []

    def test_does_not_detect_when_your_subtasks_has_no_subtasks(self):
        """Test does not detect when 'Your Subtasks:' has 'No subtasks'."""
        content = "Your Subtasks: No subtasks"
        result = detect_subtasks_scope(content)

        assert result == []

    def test_does_not_detect_when_no_subtasks_anywhere_in_content(self):
        """Test does not detect when 'No subtasks' appears anywhere in content."""
        content = "Other section: No subtasks\nSubtasks:\n- Task 1"
        result = detect_subtasks_scope(content)

        # Note: Current implementation excludes if "No subtasks" appears anywhere
        assert result == []

    def test_returns_empty_when_no_keywords(self):
        """Test returns empty list when no keywords are present."""
        content = "Some other content"
        result = detect_subtasks_scope(content)

        assert result == []


class TestDetectDecisionsScope:
    """Test detect_decisions_scope function."""

    def test_detects_decisions_with_decisions_keyword(self):
        """Test detects DECISIONS_RELEVANT_ROLE when 'Decisions:' is present."""
        content = "Decisions:\n- Decision 1\n- Decision 2"
        result = detect_decisions_scope(content)

        assert result == ["DECISIONS_RELEVANT_ROLE"]

    def test_detects_decisions_with_recent_decisions_keyword(self):
        """Test detects DECISIONS_RELEVANT_ROLE when 'Recent Decisions:' is present."""
        content = "Recent Decisions:\n- Decision 1"
        result = detect_decisions_scope(content)

        assert result == ["DECISIONS_RELEVANT_ROLE"]

    def test_does_not_detect_when_no_relevant_decisions(self):
        """Test does not detect when 'No relevant decisions' is present."""
        content = "Decisions: No relevant decisions"
        result = detect_decisions_scope(content)

        assert result == []

    def test_does_not_detect_when_recent_decisions_has_no_relevant(self):
        """Test does not detect when 'Recent Decisions:' has 'No relevant decisions'."""
        content = "Recent Decisions: No relevant decisions"
        result = detect_decisions_scope(content)

        assert result == []

    def test_does_not_detect_when_no_relevant_decisions_anywhere_in_content(self):
        """Test does not detect when 'No relevant decisions' appears anywhere in content."""
        content = "Other section: No relevant decisions\nDecisions:\n- Decision 1"
        result = detect_decisions_scope(content)

        # Note: Current implementation excludes if "No relevant decisions" appears anywhere
        assert result == []

    def test_returns_empty_when_no_keywords(self):
        """Test returns empty list when no keywords are present."""
        content = "Some other content"
        result = detect_decisions_scope(content)

        assert result == []


class TestDetectDependenciesScope:
    """Test detect_dependencies_scope function."""

    def test_detects_dependencies_with_dependencies_keyword(self):
        """Test detects DEPS_RELEVANT when 'Dependencies:' is present."""
        content = "Dependencies:\n- Dep 1\n- Dep 2"
        result = detect_dependencies_scope(content)

        assert result == ["DEPS_RELEVANT"]

    def test_detects_dependencies_with_decision_dependencies_keyword(self):
        """Test detects DEPS_RELEVANT when 'Decision Dependencies:' is present."""
        content = "Decision Dependencies:\n- Dep 1"
        result = detect_dependencies_scope(content)

        assert result == ["DEPS_RELEVANT"]

    def test_detects_dependencies_with_both_keywords(self):
        """Test detects DEPS_RELEVANT when both keywords are present."""
        content = "Dependencies: Dep 1\nDecision Dependencies: Dep 2"
        result = detect_dependencies_scope(content)

        assert result == ["DEPS_RELEVANT"]

    def test_returns_empty_when_no_keywords(self):
        """Test returns empty list when no keywords are present."""
        content = "Some other content"
        result = detect_dependencies_scope(content)

        assert result == []


class TestDetectMilestonesScope:
    """Test detect_milestones_scope function."""

    def test_detects_milestones_with_milestones_keyword(self):
        """Test detects MILESTONES when 'Milestones:' is present."""
        content = "Milestones:\n- Milestone 1\n- Milestone 2"
        result = detect_milestones_scope(content)

        assert result == ["MILESTONES"]

    def test_detects_milestones_with_recent_milestones_keyword(self):
        """Test detects MILESTONES when 'Recent Milestones:' is present."""
        content = "Recent Milestones:\n- Milestone 1"
        result = detect_milestones_scope(content)

        assert result == ["MILESTONES"]

    def test_does_not_detect_when_no_recent_milestones(self):
        """Test does not detect when 'No recent milestones' is present."""
        content = "Milestones: No recent milestones"
        result = detect_milestones_scope(content)

        assert result == []

    def test_does_not_detect_when_recent_milestones_has_none(self):
        """Test does not detect when 'Recent Milestones:' has 'No recent milestones'."""
        content = "Recent Milestones: No recent milestones"
        result = detect_milestones_scope(content)

        assert result == []

    def test_does_not_detect_when_no_recent_milestones_anywhere_in_content(self):
        """Test does not detect when 'No recent milestones' appears anywhere in content."""
        content = "Other section: No recent milestones\nMilestones:\n- Milestone 1"
        result = detect_milestones_scope(content)

        # Note: Current implementation excludes if "No recent milestones" appears anywhere
        assert result == []

    def test_returns_empty_when_no_keywords(self):
        """Test returns empty list when no keywords are present."""
        content = "Some other content"
        result = detect_milestones_scope(content)

        assert result == []


class TestDetectScopes:
    """Test detect_scopes function."""

    def test_detects_all_scopes(self):
        """Test detects all scopes when all keywords are present."""
        prompt_blocks = MagicMock()
        prompt_blocks.context = (
            "Case: Test case\n"
            "Status: Active\n"
            "Plan: Test plan\n"
            "Total Subtasks: 5\n"
            "Subtasks:\n- Task 1\n"
            "Decisions:\n- Decision 1\n"
            "Dependencies:\n- Dep 1\n"
            "Milestones:\n- Milestone 1"
        )

        result = detect_scopes(prompt_blocks)

        assert "CASE_HEADER" in result
        assert "PLAN_HEADER" in result
        assert "SUBTASKS_ROLE" in result
        assert "DECISIONS_RELEVANT_ROLE" in result
        assert "DEPS_RELEVANT" in result
        assert "MILESTONES" in result

    def test_returns_empty_when_no_content(self):
        """Test returns empty list when context is empty."""
        prompt_blocks = MagicMock()
        prompt_blocks.context = ""

        result = detect_scopes(prompt_blocks)

        assert result == []

    def test_returns_empty_when_none_content(self):
        """Test returns empty list when context is None."""
        prompt_blocks = MagicMock()
        prompt_blocks.context = None

        result = detect_scopes(prompt_blocks)

        assert result == []

    def test_detects_single_scope(self):
        """Test detects single scope when only one is present."""
        prompt_blocks = MagicMock()
        prompt_blocks.context = "Case: Test case"

        result = detect_scopes(prompt_blocks)

        assert result == ["CASE_HEADER"]

    def test_detects_multiple_scopes(self):
        """Test detects multiple scopes when several are present."""
        prompt_blocks = MagicMock()
        prompt_blocks.context = (
            "Case: Test case\n"
            "Plan: Test plan\n"
            "Dependencies:\n- Dep 1"
        )

        result = detect_scopes(prompt_blocks)

        assert "CASE_HEADER" in result
        assert "PLAN_HEADER" in result
        assert "DEPS_RELEVANT" in result
        assert len(result) == 3

    def test_excludes_subtasks_when_no_subtasks(self):
        """Test excludes SUBTASKS_ROLE when 'No subtasks' is present."""
        prompt_blocks = MagicMock()
        prompt_blocks.context = "Subtasks: No subtasks"

        result = detect_scopes(prompt_blocks)

        assert "SUBTASKS_ROLE" not in result

    def test_excludes_decisions_when_no_relevant_decisions(self):
        """Test excludes DECISIONS_RELEVANT_ROLE when 'No relevant decisions' is present."""
        prompt_blocks = MagicMock()
        prompt_blocks.context = "Decisions: No relevant decisions"

        result = detect_scopes(prompt_blocks)

        assert "DECISIONS_RELEVANT_ROLE" not in result

    def test_excludes_milestones_when_no_recent_milestones(self):
        """Test excludes MILESTONES when 'No recent milestones' is present."""
        prompt_blocks = MagicMock()
        prompt_blocks.context = "Milestones: No recent milestones"

        result = detect_scopes(prompt_blocks)

        assert "MILESTONES" not in result

    def test_detects_scopes_with_mixed_exclusions(self):
        """Test detects scopes correctly with some exclusions."""
        prompt_blocks = MagicMock()
        prompt_blocks.context = (
            "Case: Test case\n"
            "Subtasks: No subtasks\n"
            "Decisions:\n- Decision 1\n"
            "Milestones: No recent milestones"
        )

        result = detect_scopes(prompt_blocks)

        assert "CASE_HEADER" in result
        assert "SUBTASKS_ROLE" not in result  # Excluded because "No subtasks" present
        assert "DECISIONS_RELEVANT_ROLE" in result
        assert "MILESTONES" not in result  # Excluded because "No recent milestones" present

