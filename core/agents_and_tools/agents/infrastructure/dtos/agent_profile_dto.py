"""Data Transfer Object for AgentProfile in infrastructure layer."""

from dataclasses import dataclass


@dataclass
class AgentProfileDTO:
    """DTO for agent profile configuration.
    
    Used for serialization/deserialization between layers.
    All fields are required.
    """
    
    name: str
    model: str
    context_window: int
    temperature: float
    max_tokens: int
    
    def to_dict(self) -> dict[str, any]:
        """Convert DTO to dictionary."""
        return {
            "name": self.name,
            "model": self.model,
            "context_window": self.context_window,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, any]) -> "AgentProfileDTO":
        """Create DTO from dictionary (fail fast - no defaults)."""
        return cls(
            name=data["name"],
            model=data["model"],
            context_window=data["context_window"],
            temperature=data["temperature"],
            max_tokens=data["max_tokens"],
        )

