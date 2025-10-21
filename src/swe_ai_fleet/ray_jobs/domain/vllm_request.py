"""Domain model for vLLM API requests."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Message:
    """Mensaje individual en una conversación (Value Object)."""
    role: str  # "system" | "user" | "assistant"
    content: str
    
    def to_dict(self) -> dict[str, str]:
        """Convertir a formato dict para vLLM API."""
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass(frozen=True)
class VLLMRequest:
    """
    Request para vLLM API (Value Object).
    
    Representa una solicitud inmutable para generar texto usando vLLM.
    Encapsula todos los parámetros necesarios para la llamada API.
    """
    model: str
    messages: tuple[Message, ...]  # Tuple for immutability
    temperature: float
    max_tokens: int
    
    @classmethod
    def create(
        cls,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> "VLLMRequest":
        """Factory method para crear request con prompts."""
        return cls(
            model=model,
            messages=(
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ),
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convertir a formato dict para vLLM API."""
        return {
            "model": self.model,
            "messages": [msg.to_dict() for msg in self.messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
    
    def with_temperature(self, temperature: float) -> "VLLMRequest":
        """Crear nueva request con temperatura diferente (immutable)."""
        return VLLMRequest(
            model=self.model,
            messages=self.messages,
            temperature=temperature,
            max_tokens=self.max_tokens,
        )
    
    def with_diversity(self, diversity_factor: float = 1.3) -> "VLLMRequest":
        """Crear nueva request con temperatura ajustada para diversidad."""
        return self.with_temperature(self.temperature * diversity_factor)

