"""Port for LLM client operations (low-level API calls).

Defined in ceremony_engine to avoid depending on core.agents_and_tools.
Adapters (e.g. vLLM client) implement this port."""

from abc import ABC, abstractmethod


class LlmClientPort(ABC):
    """Port defining low-level LLM API interface.

    This port should ONLY contain the primitive LLM operation:
    generating text from prompts.

    Business logic (planning, decisions, etc.) belongs in Use Cases.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate text from prompts.

        This is the ONLY responsibility: call LLM API and return text.
        No business logic, no specific task handling, just raw LLM communication.

        Args:
            system_prompt: System instruction for the LLM
            user_prompt: User query/task
            temperature: Override default temperature for this call
            max_tokens: Override default max tokens for this call

        Returns:
            Generated text content from LLM

        Raises:
            RuntimeError: If LLM API call fails
        """
        pass
