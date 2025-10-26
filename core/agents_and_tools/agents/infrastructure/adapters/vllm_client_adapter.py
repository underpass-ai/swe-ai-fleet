"""vLLM client adapter for LLM communication."""

import json
import logging
from typing import Any

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

from core.agents_and_tools.agents.domain.ports.llm_client import LLMClientPort

logger = logging.getLogger(__name__)

# Constants
JSON_CODE_BLOCK_START = "```json"
JSON_CODE_BLOCK_END = "```"
JSON_MARKDOWN_DELIMITER_LEN = 7  # Length of "```json"


class VLLMClientAdapter(LLMClientPort):
    """
    Adapter for vLLM API - ONLY raw LLM communication.

    This adapter implements LLMClientPort and provides low-level
    access to vLLM API. It only handles:
    - HTTP communication with vLLM
    - Request/response serialization
    - Error handling for API calls

    Business logic (building prompts, parsing responses for specific tasks)
    belongs in Use Cases.
    """

    def __init__(
        self,
        vllm_url: str,
        model: str = "Qwen/Qwen3-0.6B",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60,
    ):
        """
        Initialize vLLM client adapter.

        Args:
            vllm_url: URL of vLLM server (e.g., "http://vllm-server-service:8000")
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            timeout: Request timeout in seconds
        """
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp required for vLLM client. Install with: pip install aiohttp")

        self.vllm_url = vllm_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        logger.info(f"VLLMClientAdapter initialized: {model} at {vllm_url}")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate text using vLLM API.

        This is the ONLY responsibility: call LLM API and return text.
        No business logic, no specific task handling, just raw LLM communication.

        Args:
            system_prompt: System instruction for the LLM
            user_prompt: User query/task
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            Generated text content

        Raises:
            RuntimeError: If vLLM API call fails
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temp,
            "max_tokens": max_tok,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.vllm_url}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    content = data["choices"][0]["message"]["content"]
                    logger.debug(f"vLLM generated {len(content)} characters")
                    return content.strip()

        except aiohttp.ClientError as e:
            logger.error(f"vLLM API error: {e}")
            raise RuntimeError(f"Failed to call vLLM API at {self.vllm_url}: {e}") from e
        except KeyError as e:
            logger.error(f"Invalid vLLM response format: {e}")
            raise RuntimeError(f"Invalid vLLM API response: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error calling vLLM: {e}")
            raise RuntimeError(f"vLLM client error: {e}") from e

