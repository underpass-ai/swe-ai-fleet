"""Unit tests for LLMTaskDerivationMapper."""

import pytest

# Role removed - Planning Service assigns roles based on RBAC and event context, NOT from LLM
from planning.infrastructure.mappers.llm_task_derivation_mapper import (
    LLMTaskDerivationMapper,
)


class TestLLMTaskDerivationMapper:
    """Test suite for LLMTaskDerivationMapper."""

    def test_from_llm_text_parses_single_task(self) -> None:
        """Test parsing single task from LLM text."""
        # Given: LLM text with single task (no ROLE - Planning Service assigns roles)
        llm_text = """
TITLE: Setup database
DESCRIPTION: Create database schema and tables
ESTIMATED_HOURS: 8
PRIORITY: 1
KEYWORDS: database, schema, setup
"""

        # When: parse
        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        # Then: one task parsed
        assert len(task_nodes) == 1
        assert str(task_nodes[0].title) == "Setup database"
        # Role removed from TaskNode - Planning Service assigns roles based on RBAC
        assert len(task_nodes[0].keywords) == 3

    def test_from_llm_text_parses_multiple_tasks(self) -> None:
        """Test parsing multiple tasks separated by ---."""
        # Given: LLM text with multiple tasks (no ROLE - Planning Service assigns roles)
        llm_text = """
TITLE: Setup database
DESCRIPTION: Create database schema
ESTIMATED_HOURS: 8
PRIORITY: 1
KEYWORDS: database, schema
---
TITLE: Create API
DESCRIPTION: Build REST API
ESTIMATED_HOURS: 16
PRIORITY: 2
KEYWORDS: api, rest
"""

        # When: parse
        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        # Then: two tasks parsed
        assert len(task_nodes) == 2
        assert str(task_nodes[0].title) == "Setup database"
        assert str(task_nodes[1].title) == "Create API"

    def test_from_llm_text_handles_missing_optional_fields(self) -> None:
        """Test parsing task with missing optional fields (description, keywords)."""
        # Given: LLM text without description and keywords (no ROLE - Planning Service assigns roles)
        llm_text = """
TITLE: Setup database
ESTIMATED_HOURS: 8
PRIORITY: 1
"""

        # When: parse
        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        # Then: task parsed with defaults
        assert len(task_nodes) == 1
        assert str(task_nodes[0].title) == "Setup database"
        assert len(task_nodes[0].keywords) == 0
        # Role removed from TaskNode - Planning Service assigns roles based on RBAC

    def test_from_llm_text_does_not_parse_role(self) -> None:
        """Test that ROLE is NOT parsed from LLM (Planning Service assigns roles)."""
        # Given: LLM text with ROLE field (should be ignored)
        llm_text = """
TITLE: Test task
DESCRIPTION: Test description
ESTIMATED_HOURS: 8
PRIORITY: 1
KEYWORDS: test
ROLE: DEVELOPER
"""

        # When: parse
        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        # Then: role is not part of TaskNode (Planning Service assigns roles)

    def test_from_llm_text_with_invalid_format_raises_error(self) -> None:
        """Test that completely invalid text raises ValueError."""
        # Given: invalid LLM text (no tasks)
        llm_text = "This is not a valid task format"

        # When/Then: raises ValueError
        with pytest.raises(ValueError, match="No valid tasks parsed"):
            LLMTaskDerivationMapper.from_llm_text(llm_text)

    def test_from_llm_text_with_missing_required_field_skips_task(self) -> None:
        """Test that task with missing required field is skipped."""
        # Given: LLM text with one valid and one invalid task (no ROLE - Planning Service assigns roles)
        llm_text = """
TITLE: Valid task
DESCRIPTION: Valid description
ESTIMATED_HOURS: 8
PRIORITY: 1
KEYWORDS: valid
---
TITLE: Invalid task without description
ESTIMATED_HOURS: 8
PRIORITY: 1
"""

        # When: parse
        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        # Then: both tasks parsed (description falls back to title)
        assert len(task_nodes) == 2
        assert str(task_nodes[0].title) == "Valid task"
        assert str(task_nodes[1].title) == "Invalid task without description"

