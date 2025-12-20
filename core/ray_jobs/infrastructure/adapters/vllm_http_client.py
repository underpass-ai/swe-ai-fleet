"""vLLM HTTP client adapter."""

import json
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
                # Build payload with structured outputs if applicable
                payload = request.to_dict()
                
                # Logging for debugging
                logger.debug(
                    f"[{self.agent_id}] vLLM request: "
                    f"model={request.model}, "
                    f"has_schema={request.json_schema is not None}, "
                    f"task_type={request.task_type}"
                )
                
                async with session.post(
                    f"{self.vllm_url}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Extract reasoning if exists (separated by reasoning parser)
                    message = data["choices"][0]["message"]
                    content = message["content"]
                    reasoning = message.get("reasoning")  # Optional, only if server has parser
                    
                    # Validate JSON if structured output
                    if request.json_schema:
                        try:
                            json.loads(content)  # Validate that it's valid JSON
                            logger.debug(f"[{self.agent_id}] ✅ Valid JSON from structured outputs")
                        except json.JSONDecodeError as e:
                            logger.error(
                                f"[{self.agent_id}] ❌ Invalid JSON from structured outputs: {e}\n"
                                f"Content preview: {content[:200]}"
                            )
                            raise RuntimeError(f"vLLM returned invalid JSON: {e}") from e
                    
                    # Log reasoning if exists (for observability)
                    if reasoning:
                        logger.debug(
                            f"[{self.agent_id}] Reasoning trace available "
                            f"({len(reasoning)} chars)"
                        )
                    
                    # Parse vLLM API response using domain model
                    vllm_response = VLLMResponse.from_vllm_api(
                        api_data=data,
                        agent_id=self.agent_id,
                        role=self.role,
                        model=self.model,
                        temperature=request.temperature,
                        reasoning=reasoning,
                    )

                    # Log the generated content
                    logger.info(
                        f"[{self.agent_id}] 💡 LLM generated response "
                        f"({len(vllm_response.content)} chars, {vllm_response.tokens} tokens):\n"
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

