"""DTOs for council operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CouncilConfigDTO:
    """Configuration for creating a council."""

    role: str
    num_agents: int
    agent_type: str
    model_profile: str

    def __post_init__(self) -> None:
        """Validate DTO fields."""
        if not self.role:
            raise ValueError("role cannot be empty")
        if self.num_agents < 1:
            raise ValueError(f"num_agents must be >= 1, got {self.num_agents}")
        if self.agent_type not in ("MOCK", "VLLM", "RAY_VLLM"):
            raise ValueError(f"invalid agent_type: {self.agent_type}")


@dataclass(frozen=True)
class DeliberationRequestDTO:
    """Request for multi-agent deliberation."""

    task_description: str
    role: str
    rounds: int
    num_agents: int
    rubric: str

    def __post_init__(self) -> None:
        """Validate DTO fields."""
        if not self.task_description:
            raise ValueError("task_description cannot be empty")
        if not self.role:
            raise ValueError("role cannot be empty")
        if self.rounds < 1:
            raise ValueError(f"rounds must be >= 1, got {self.rounds}")
        if self.num_agents < 1:
            raise ValueError(f"num_agents must be >= 1, got {self.num_agents}")


@dataclass(frozen=True)
class DeliberationResultDTO:
    """Result from deliberation."""

    winner_id: str
    winner_role: str
    winner_content: str
    num_proposals: int
    duration_ms: int

    def __post_init__(self) -> None:
        """Validate DTO fields."""
        if not self.winner_id:
            raise ValueError("winner_id cannot be empty")
        if not self.winner_role:
            raise ValueError("winner_role cannot be empty")
        if not self.winner_content:
            raise ValueError("winner_content cannot be empty")
        if self.num_proposals < 1:
            raise ValueError(f"num_proposals must be >= 1, got {self.num_proposals}")
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms must be >= 0, got {self.duration_ms}")

