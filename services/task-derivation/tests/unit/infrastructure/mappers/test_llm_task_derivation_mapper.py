"""Unit tests for LLMTaskDerivationMapper."""

from __future__ import annotations

import pytest

from task_derivation.infrastructure.mappers.llm_task_derivation_mapper import (
    LLMTaskDerivationMapper,
)


class TestLLMTaskDerivationMapper:
    """Test suite for parsing LLM output."""

    def test_parses_multiple_tasks(self) -> None:
        llm_text = (
            "TITLE: Setup project\n"
            "DESCRIPTION: Create structure\n"
            "ESTIMATED_HOURS: 8\n"
            "PRIORITY: 1\n"
            "KEYWORDS: setup, project\n"
            "---\n"
            "TITLE: Build API\n"
            "DESCRIPTION: Implement endpoints\n"
            "ESTIMATED_HOURS: 12\n"
            "PRIORITY: 2\n"
            "KEYWORDS: api, rest\n"
        )

        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        assert len(task_nodes) == 2
        assert task_nodes[0].title.value == "Setup project"

    def test_defaults_missing_optional_fields(self) -> None:
        llm_text = (
            "TITLE: Setup project\n"
            "DESCRIPTION: Create structure\n"
            "KEYWORDS: setup\n"
        )

        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_text)

        assert task_nodes[0].estimated_hours.to_hours() == 0
        assert task_nodes[0].priority.value == 1

    def test_raises_when_no_tasks(self) -> None:
        with pytest.raises(ValueError):
            LLMTaskDerivationMapper.from_llm_text("   ")

