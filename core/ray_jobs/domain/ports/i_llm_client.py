"""Port for LLM client."""

from abc import ABC, abstractmethod

from ..vllm_request import VLLMRequest
from ..vllm_response import VLLMResponse


class ILLMClient(ABC):
    """
    Puerto para cliente de LLM.
    
    Define el contrato que debe cumplir cualquier
    implementación de cliente LLM (vLLM, OpenAI, etc.).
    """
    
    @abstractmethod
    async def generate(self, request: VLLMRequest) -> VLLMResponse:
        """
        Generar texto usando el LLM.
        
        Args:
            request: Request con prompts y parámetros
            
        Returns:
            Response con contenido generado
            
        Raises:
            RuntimeError: Si la llamada al LLM falla
        """
        pass

