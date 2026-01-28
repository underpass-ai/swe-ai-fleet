"""Unit tests for GenerateLlmTextUseCase."""

import pytest
from unittest.mock import AsyncMock

from core.ceremony_engine.application.ports.llm_client_port import LlmClientPort
from core.ceremony_engine.application.use_cases.llm_generation_usecase import (
    GenerateLlmTextUseCase,
)


@pytest.mark.asyncio
async def test_generate_llm_text_happy_path() -> None:
    """Test LLM use case returns generated text."""
    llm_client_port = AsyncMock(spec=LlmClientPort)
    llm_client_port.generate.return_value = "LLM output"
    use_case = GenerateLlmTextUseCase(llm_client_port)

    result = await use_case.execute("System prompt", "User prompt")

    assert result == "LLM output"
    llm_client_port.generate.assert_awaited_once_with(
        system_prompt="System prompt",
        user_prompt="User prompt",
    )


@pytest.mark.asyncio
async def test_generate_llm_text_rejects_empty_system_prompt() -> None:
    """Test empty system prompt is rejected."""
    use_case = GenerateLlmTextUseCase(AsyncMock(spec=LlmClientPort))

    with pytest.raises(ValueError, match="system_prompt cannot be empty"):
        await use_case.execute("", "User prompt")


@pytest.mark.asyncio
async def test_generate_llm_text_rejects_empty_user_prompt() -> None:
    """Test empty user prompt is rejected."""
    use_case = GenerateLlmTextUseCase(AsyncMock(spec=LlmClientPort))

    with pytest.raises(ValueError, match="user_prompt cannot be empty"):
        await use_case.execute("System prompt", "   ")


def test_generate_llm_text_use_case_requires_llm_client_port() -> None:
    """Test use case rejects missing LLM client port."""
    with pytest.raises(ValueError, match="llm_client_port is required"):
        GenerateLlmTextUseCase(None)  # type: ignore[arg-type]
