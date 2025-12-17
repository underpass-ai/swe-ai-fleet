"""Use case: Generate proposal using LLM."""

from typing import Any

from ..domain import (
    AgentConfig,
    SystemPrompt,
    TaskPrompt,
    VLLMRequest,
)
from ..domain.ports import IVLLMClient


class GenerateProposal:
    """
    Caso de uso: Generar propuesta usando LLM.

    Coordina la construcción de prompts y la llamada al LLM
    para generar una propuesta de solución.
    """

    def __init__(self, config: AgentConfig, llm_client: IVLLMClient):
        """
        Initialize use case.

        Args:
            config: Configuración del agente
            llm_client: Cliente LLM (puerto)
        """
        self.config = config
        self.llm_client = llm_client

    async def execute(
        self,
        task: str,
        constraints: dict[str, Any],
        diversity: bool = False,
    ) -> dict[str, Any]:
        """
        Ejecutar generación de propuesta.

        Args:
            task: Task description
            constraints: Task constraints (rubric, requirements, metadata)
            diversity: Whether to increase diversity

        Returns:
            Proposal dictionary with content and metadata
        """
        # 1. Build system prompt using domain model
        system_prompt = SystemPrompt.for_role(
            role=str(self.config.role),
            rubric=constraints.get("rubric", ""),
            requirements=constraints.get("requirements", []),
            diversity=diversity,
        ).render()

        # 2. Build task prompt using domain model
        task_prompt = TaskPrompt(
            task=task,
            metadata=constraints.get("metadata", {}),
        ).render()

        # 3. Adjust temperature for diversity
        temperature = self.config.temperature * 1.3 if diversity else self.config.temperature

        # 4. Create vLLM request using domain model
        vllm_request = VLLMRequest.create(
            model=self.config.model,
            system_prompt=system_prompt,
            user_prompt=task_prompt,
            temperature=temperature,
            max_tokens=self.config.max_tokens,
        )

        # Log the input prompts for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"[{self.config.agent_id}] 📝 Generating proposal with:\n"
            f"   Task: {task[:200]}...\n"
            f"   Constraints keys: {list(constraints.keys()) if isinstance(constraints, dict) else 'N/A'}\n"
            f"   System prompt length: {len(system_prompt)} chars\n"
            f"   Task prompt length: {len(task_prompt)} chars"
        )

        # 5. Call LLM using port (dependency injection)
        vllm_response = await self.llm_client.generate(vllm_request)

        # Log the proposal
        logger.info(
            f"[{self.config.agent_id}] ✅ Proposal generated: {len(vllm_response.content)} chars, {vllm_response.tokens} tokens"
        )

        # 6. Return as dict (for backward compatibility)
        return vllm_response.to_dict()

