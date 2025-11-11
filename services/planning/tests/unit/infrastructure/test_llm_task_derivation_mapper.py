"""Unit tests for LLMTaskDerivationMapper."""

import pytest

from planning.domain.value_objects.actors.role_type import RoleType
from planning.infrastructure.mappers.llm_task_derivation_mapper import (
    LLMTaskDerivationMapper,
)


class TestLLMTaskDerivationMapper:
    """Test suite for LLMTaskDerivationMapper."""

    def test_from_llm_text_parses_single_task(self) -> None:
        """Test parsing single task from LLM text."""
        # Given: LLM text with single task
        llm_text = """
TASK_ID: TASK-001
TITLE: Setup database
DESCRIPTION: Create database schema and tables
ROLE: DEVELOPER
KEYWORDS: database, schema, setup
"""

        # When: parse
        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        # Then: one task parsed
        assert len(task_nodes) == 1
        assert task_nodes[0].task_id.value == "TASK-001"
        assert str(task_nodes[0].title) == "Setup database"
        assert task_nodes[0].role.value == RoleType.DEVELOPER
        assert len(task_nodes[0].keywords) == 3

    def test_from_llm_text_parses_multiple_tasks(self) -> None:
        """Test parsing multiple tasks separated by ---."""
        # Given: LLM text with multiple tasks
        llm_text = """
TASK_ID: TASK-001
TITLE: Setup database
DESCRIPTION: Create database schema
ROLE: DEVELOPER
KEYWORDS: database, schema
---
TASK_ID: TASK-002
TITLE: Create API
DESCRIPTION: Build REST API
ROLE: DEVELOPER
KEYWORDS: api, rest
"""

        # When: parse
        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        # Then: two tasks parsed
        assert len(task_nodes) == 2
        assert task_nodes[0].task_id.value == "TASK-001"
        assert task_nodes[1].task_id.value == "TASK-002"

    def test_from_llm_text_handles_missing_optional_fields(self) -> None:
        """Test parsing task with missing optional fields (description, keywords)."""
        # Given: LLM text without description and keywords
        llm_text = """
TASK_ID: TASK-001
TITLE: Setup database
ROLE: DEVELOPER
"""

        # When: parse
        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        # Then: task parsed with defaults
        assert len(task_nodes) == 1
        assert task_nodes[0].task_id.value == "TASK-001"
        assert len(task_nodes[0].keywords) == 0

    def test_from_llm_text_maps_role_variants(self) -> None:
        """Test that role variants are mapped correctly."""
        # Given: different role variants
        test_cases = [
            ("DEVELOPER", RoleType.DEVELOPER),
            ("DEV", RoleType.DEVELOPER),
            ("QA", RoleType.QA),
            ("TESTER", RoleType.QA),
            ("ARCHITECT", RoleType.ARCHITECT),
        ]

        for role_str, expected_type in test_cases:
            llm_text = f"""
TASK_ID: TASK-001
TITLE: Test task
ROLE: {role_str}
"""

            # When: parse
            task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

            # Then: role mapped correctly
            assert task_nodes[0].role.value == expected_type

    def test_from_llm_text_with_invalid_format_raises_error(self) -> None:
        """Test that completely invalid text raises ValueError."""
        # Given: invalid LLM text (no tasks)
        llm_text = "This is not a valid task format"

        # When/Then: raises ValueError
        with pytest.raises(ValueError, match="No valid tasks parsed"):
            LLMTaskDerivationMapper.from_llm_text(llm_text)

    def test_from_llm_text_with_missing_required_field_skips_task(self) -> None:
        """Test that task with missing required field is skipped."""
        # Given: LLM text with one valid and one invalid task
        llm_text = """
TASK_ID: TASK-001
TITLE: Valid task
ROLE: DEVELOPER
---
TITLE: Invalid task without ID
ROLE: DEVELOPER
"""

        # When: parse
        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        # Then: only valid task parsed
        assert len(task_nodes) == 1
        assert task_nodes[0].task_id.value == "TASK-001"

