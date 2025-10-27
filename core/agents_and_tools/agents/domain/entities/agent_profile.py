"""Domain entity for AgentProfile."""

from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None


@dataclass(frozen=True)
class AgentProfile:
    """Agent profile domain entity.

    Represents a role-specific LLM configuration in the domain layer.
    All fields are required and immutable.
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

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "AgentProfile":
        """Load profile from YAML file (fail fast)."""
        if not YAML_AVAILABLE:
            raise ImportError("pyyaml required. Install with: pip install pyyaml")

        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {yaml_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        # Fail fast if required fields are missing
        return cls(
            name=data["name"],
            model=data["model"],
            context_window=data["context_window"],
            temperature=data["temperature"],
            max_tokens=data["max_tokens"],
        )

