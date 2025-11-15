"""Tests for TaskDerivationConfig and LLMPrompt."""

from __future__ import annotations

import pytest

from task_derivation.domain.value_objects.task_derivation.config.task_derivation_config import (
    TaskDerivationConfig,
)
from task_derivation.domain.value_objects.task_derivation.prompt.llm_prompt import (
    LLMPrompt,
)


def test_task_derivation_config_builds_prompt_with_context() -> None:
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


def test_task_derivation_config_validates_min_max_relationship() -> None:
    with pytest.raises(ValueError, match="must be >= min_tasks"):
        TaskDerivationConfig(
            prompt_template="x",
            min_tasks=3,
            max_tasks=2,
            max_retries=1,
        )


def test_task_derivation_config_requires_min_tasks_at_least_one() -> None:
    with pytest.raises(ValueError, match="min_tasks must be >= 1"):
        TaskDerivationConfig(
            prompt_template="x",
            min_tasks=0,
            max_tasks=1,
            max_retries=0,
        )


def test_task_derivation_config_requires_non_negative_retries() -> None:
    with pytest.raises(ValueError, match="max_retries must be >= 0"):
        TaskDerivationConfig(
            prompt_template="x",
            min_tasks=1,
            max_tasks=1,
            max_retries=-1,
        )


def test_task_derivation_config_requires_prompt_template() -> None:
    with pytest.raises(ValueError, match="prompt_template cannot be empty"):
        TaskDerivationConfig(
            prompt_template=" ",
            min_tasks=1,
            max_tasks=1,
            max_retries=0,
        )


def test_llm_prompt_rejects_blank_value() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        LLMPrompt("")


def test_llm_prompt_token_estimate() -> None:
    prompt = LLMPrompt("alpha beta gamma delta")
    assert prompt.token_count_estimate() > 0

