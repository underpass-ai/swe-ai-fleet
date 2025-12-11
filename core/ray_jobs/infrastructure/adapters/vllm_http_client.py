"""vLLM HTTP client adapter."""

import logging

import aiohttp

from ...domain import VLLMRequest, VLLMResponse
from ...domain.ports import IVLLMClient

logger = logging.getLogger(__name__)


class VLLMHTTPClient(IVLLMClient):
    """
    Implementación de ILLMClient usando vLLM HTTP API.

    Conecta con un servidor vLLM via HTTP para generar texto.
    """

    def __init__(
        self,
        vllm_url: str,
        agent_id: str,
        role: str,
        model: str,
        timeout: int = 60,
    ):
        """
        Initialize vLLM HTTP client.

        Args:
            vllm_url: URL del servidor vLLM
            agent_id: ID del agente (para metadata)
            role: Rol del agente (para metadata)
            model: Modelo a usar
            timeout: Timeout en segundos
        """
        self.vllm_url = vllm_url
        self.agent_id = agent_id
        self.role = role
        self.model = model
        self.timeout = timeout

    async def generate(self, request: VLLMRequest) -> VLLMResponse:
        """
        Generar texto usando vLLM HTTP API.

        Args:
            request: Request con prompts y parámetros

        Returns:
            Response con contenido generado

        Raises:
            RuntimeError: Si la llamada a vLLM falla
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.vllm_url}/v1/chat/completions",
                    json=request.to_dict(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    # Parse vLLM API response using domain model
                    vllm_response = VLLMResponse.from_vllm_api(
                        api_data=data,
                        agent_id=self.agent_id,
                        role=self.role,
                        model=self.model,
                        temperature=request.temperature,
                    )

                    # Log the generated content
                    logger.info(
                        f"[{self.agent_id}] 💡 LLM generated response ({len(vllm_response.content)} chars, {vllm_response.tokens} tokens):\n"
                        f"{'='*70}\n{vllm_response.content}\n{'='*70}"
                    )

                    return vllm_response

            except aiohttp.ClientError as e:
                logger.error(
                    f"[{self.agent_id}] vLLM API error: {e}",
                    exc_info=True
                )
                raise RuntimeError(f"Failed to call vLLM API: {e}") from e
            except KeyError as e:
                logger.error(
                    f"[{self.agent_id}] Invalid vLLM response format: {e}",
                    exc_info=True
                )
                raise RuntimeError(f"Invalid vLLM response: {e}") from e

