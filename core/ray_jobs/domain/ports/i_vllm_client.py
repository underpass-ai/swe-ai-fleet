"""Port for vLLM client."""

from abc import ABC, abstractmethod

from ..vllm_request import VLLMRequest
from ..vllm_response import VLLMResponse


class IVLLMClient(ABC):
    """
    Puerto para cliente vLLM.
    
    Define el contrato específico para interactuar con vLLM.
    Es más específico que ILLMClient porque conoce los tipos
    VLLMRequest y VLLMResponse del dominio.
    """
    
    @abstractmethod
    async def generate(self, request: VLLMRequest) -> VLLMResponse:
        """
        Generar texto usando vLLM.
        
        Args:
            request: Request con prompts y parámetros de vLLM
            
        Returns:
            Response con contenido generado por vLLM
            
        Raises:
            RuntimeError: Si la llamada a vLLM falla
        """
        pass

