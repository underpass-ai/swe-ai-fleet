"""Tests for LLMPrompt (TaskDerivationConfig tests moved to core/shared)."""

from __future__ import annotations

import pytest

from task_derivation.domain.value_objects.task_derivation.prompt.llm_prompt import (
    LLMPrompt,
)


def test_llm_prompt_rejects_blank_value() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        LLMPrompt("")


def test_llm_prompt_token_estimate() -> None:
    prompt = LLMPrompt("alpha beta gamma delta")
    assert prompt.token_count_estimate() > 0

