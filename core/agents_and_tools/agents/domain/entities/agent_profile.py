"""Domain entity for AgentProfile."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentProfile:
    """Agent profile domain entity.

    Represents a role-specific LLM configuration in the domain layer.
    All fields are required and immutable.

    Use yaml_profile_adapter.load_profile_from_yaml() to load from YAML.
    """

    name: str
    model: str
    context_window: int
    temperature: float
    max_tokens: int

    def __post_init__(self):
        """Validate profile values (fail fast)."""
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError(f"Temperature must be between 0 and 2, got {self.temperature}")
        if self.max_tokens <= 0:
            raise ValueError(f"Max tokens must be positive, got {self.max_tokens}")
        if self.context_window < self.max_tokens:
            raise ValueError(
                f"Context window ({self.context_window}) must be >= max_tokens ({self.max_tokens})"
            )
        if not self.model:
            raise ValueError("Model name cannot be empty")
        if not self.name:
            raise ValueError("Profile name cannot be empty")

