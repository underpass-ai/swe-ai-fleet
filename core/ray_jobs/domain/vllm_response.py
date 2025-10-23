"""Domain model for vLLM API responses."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class VLLMResponse:
    """
    Response de vLLM API (Value Object).
    
    Representa la respuesta inmutable del LLM,
    encapsulando contenido generado y metadata.
    """
    content: str
    author_id: str
    author_role: str
    model: str
    temperature: float
    tokens: int
    
    @classmethod
    def from_vllm_api(
        cls,
        api_data: dict,
        agent_id: str,
        role: str,
        model: str,
        temperature: float,
    ) -> "VLLMResponse":
        """
        Factory method desde respuesta cruda de vLLM API.
        
        Parsea la estructura de vLLM API:
        {
            "choices": [{"message": {"content": "..."}}],
            "usage": {"total_tokens": 123}
        }
        
        Args:
            api_data: Respuesta JSON de vLLM API
            agent_id: ID del agente
            role: Rol del agente
            model: Modelo usado
            temperature: Temperatura usada
            
        Returns:
            VLLMResponse instance
            
        Raises:
            KeyError: Si la estructura de la respuesta es inválida
        """
        try:
            # Extract content from vLLM API structure
            content = api_data["choices"][0]["message"]["content"]
            usage_data = api_data.get("usage", {})
            tokens = usage_data.get("total_tokens", 0)
            
            return cls(
                content=content.strip(),
                author_id=agent_id,
                author_role=role,
                model=model,
                temperature=temperature,
                tokens=tokens,
            )
        except (KeyError, IndexError, TypeError) as e:
            raise KeyError(f"Invalid vLLM API response structure: {e}") from e
    
    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario para serialización."""
        return {
            "content": self.content,
            "author_id": self.author_id,
            "author_role": self.author_role,
            "model": self.model,
            "temperature": self.temperature,
            "tokens": self.tokens,
        }

