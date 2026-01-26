"""Use case for LLM text generation in ceremony engine."""

from core.ceremony_engine.application.ports.llm_client_port import LlmClientPort


class GenerateLlmTextUseCase:
    """Use case for generating text via LLM client port."""

    def __init__(self, llm_client_port: LlmClientPort) -> None:
        if not llm_client_port:
            raise ValueError("llm_client_port is required (fail-fast)")
        self._llm_client_port = llm_client_port

    async def execute(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text using the injected LLM client.

        Args:
            system_prompt: System instruction for the LLM
            user_prompt: User input prompt

        Returns:
            Generated text

        Raises:
            ValueError: If prompts are empty
            RuntimeError: If LLM call fails
        """
        if not system_prompt or not system_prompt.strip():
            raise ValueError("system_prompt cannot be empty")
        if not user_prompt or not user_prompt.strip():
            raise ValueError("user_prompt cannot be empty")

        return await self._llm_client_port.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
