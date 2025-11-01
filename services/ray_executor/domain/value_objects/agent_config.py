"""Agent configuration value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for an agent in the deliberation.

    Value object representing an agent's configuration for task execution.

    Attributes:
        agent_id: Unique identifier for the agent
        role: Role of the agent (DEV, QA, ARCHITECT, etc.)
        model: Model name to use (e.g. "Qwen/Qwen2.5-Coder-7B-Instruct")
        prompt_template: Optional prompt template for the agent
    """

    agent_id: str
    role: str
    model: str
    prompt_template: str = ""

    def __post_init__(self) -> None:
        """Validate agent config invariants."""
        if not self.agent_id:
            raise ValueError("agent_id cannot be empty")

        if not self.role:
            raise ValueError("role cannot be empty")

        if not self.model:
            raise ValueError("model cannot be empty")

