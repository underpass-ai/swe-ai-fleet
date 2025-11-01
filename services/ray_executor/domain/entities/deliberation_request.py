"""Deliberation request entity."""

from dataclasses import dataclass

from services.ray_executor.domain.value_objects.agent_config import AgentConfig
from services.ray_executor.domain.value_objects.task_constraints import (
    TaskConstraints,
)


@dataclass(frozen=True)
class DeliberationRequest:
    """Represents a request to execute a deliberation on Ray cluster.

    This is a domain entity that encapsulates all the information needed
    to execute a multi-agent deliberation task.

    Attributes:
        task_id: Unique identifier for the task
        task_description: Description of what needs to be done
        role: Role for the council (DEV, QA, ARCHITECT, etc.)
        constraints: Task execution constraints
        agents: List of agent configurations
        vllm_url: URL of the vLLM inference server
        vllm_model: Model name to use for inference
    """

    task_id: str
    task_description: str
    role: str
    constraints: TaskConstraints
    agents: tuple[AgentConfig, ...]
    vllm_url: str
    vllm_model: str

    def __post_init__(self) -> None:
        """Validate deliberation request invariants."""
        if not self.task_id:
            raise ValueError("task_id cannot be empty")

        if not self.task_description:
            raise ValueError("task_description cannot be empty")

        if not self.role:
            raise ValueError("role cannot be empty")

        if not self.agents:
            raise ValueError("At least one agent is required")

        if not self.vllm_url:
            raise ValueError("vllm_url cannot be empty")

        if not self.vllm_model:
            raise ValueError("vllm_model cannot be empty")

