"""Unit tests for TaskDerivationConfig value object."""

from __future__ import annotations

import pytest

from core.shared.domain.value_objects.task_derivation.config.task_derivation_config import (
    TaskDerivationConfig,
)


class TestTaskDerivationConfig:
    """Tests for TaskDerivationConfig value object."""

    def test_valid_config_creates_instance(self) -> None:
        """Test that valid config creates instance."""
        config = TaskDerivationConfig(
            prompt_template="Template: {description}",
            min_tasks=2,
            max_tasks=5,
            max_retries=1,
        )
        assert config.prompt_template == "Template: {description}"
        assert config.min_tasks == 2
        assert config.max_tasks == 5
        assert config.max_retries == 1

    def test_requires_prompt_template(self) -> None:
        """Test that empty prompt template is rejected."""
        with pytest.raises(ValueError, match="prompt_template cannot be empty"):
            TaskDerivationConfig(
                prompt_template=" ",
                min_tasks=1,
                max_tasks=1,
                max_retries=0,
            )

    def test_requires_min_tasks_at_least_one(self) -> None:
        """Test that min_tasks < 1 is rejected."""
        with pytest.raises(ValueError, match="min_tasks must be >= 1"):
            TaskDerivationConfig(
                prompt_template="x",
                min_tasks=0,
                max_tasks=1,
                max_retries=0,
            )

    def test_validates_min_max_relationship(self) -> None:
        """Test that max_tasks < min_tasks is rejected."""
        with pytest.raises(ValueError, match="must be >= min_tasks"):
            TaskDerivationConfig(
                prompt_template="x",
                min_tasks=3,
                max_tasks=2,
                max_retries=1,
            )

    def test_requires_non_negative_retries(self) -> None:
        """Test that max_retries < 0 is rejected."""
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            TaskDerivationConfig(
                prompt_template="x",
                min_tasks=1,
                max_tasks=1,
                max_retries=-1,
            )

    def test_build_prompt_without_context(self) -> None:
        """Test building prompt without rehydrated context."""
        config = TaskDerivationConfig(
            prompt_template="Desc: {description}\nAC: {acceptance_criteria}\nNotes: {technical_notes}",
            min_tasks=2,
            max_tasks=5,
            max_retries=1,
        )

        prompt = config.build_prompt(
            description="Build API",
            acceptance_criteria="Must pass tests",
            technical_notes="Use FastAPI",
        )

        assert "Build API" in prompt
        assert "Must pass tests" in prompt
        assert "Use FastAPI" in prompt
        assert "{rehydrated_context}" not in prompt

    def test_build_prompt_with_context(self) -> None:
        """Test building prompt with rehydrated context."""
        config = TaskDerivationConfig(
            prompt_template="Desc: {description}\nCtx: {rehydrated_context}",
            min_tasks=2,
            max_tasks=5,
            max_retries=1,
        )

        prompt = config.build_prompt(
            description="Build API",
            acceptance_criteria="Must pass tests",
            technical_notes="Use FastAPI",
            rehydrated_context="Story header",
        )

        assert "Build API" in prompt
        assert "Story header" in prompt

    def test_build_prompt_with_empty_optional_fields(self) -> None:
        """Test building prompt with empty optional fields uses defaults."""
        config = TaskDerivationConfig(
            prompt_template="Desc: {description}\nAC: {acceptance_criteria}\nNotes: {technical_notes}",
            min_tasks=2,
            max_tasks=5,
            max_retries=1,
        )

        prompt = config.build_prompt(
            description="Build API",
            acceptance_criteria="",
            technical_notes="",
        )

        assert "Build API" in prompt
        assert "Not specified" in prompt
        assert "None" in prompt

