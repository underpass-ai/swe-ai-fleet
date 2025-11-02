"""DTOs for user story operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryCreationRequestDTO:
    """Request to create a new user story."""

    story_id: str
    title: str
    description: str
    initial_phase: str

    def __post_init__(self) -> None:
        """Validate DTO fields."""
        if not self.story_id:
            raise ValueError("story_id cannot be empty")
        if not self.title:
            raise ValueError("title cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")
        if self.initial_phase not in ("DESIGN", "BUILD", "TEST", "VALIDATE"):
            raise ValueError(f"invalid initial_phase: {self.initial_phase}")


@dataclass(frozen=True)
class StoryCreationResponseDTO:
    """Response from story creation."""

    context_id: str
    story_id: str
    current_phase: str

    def __post_init__(self) -> None:
        """Validate DTO fields."""
        if not self.context_id:
            raise ValueError("context_id cannot be empty")
        if not self.story_id:
            raise ValueError("story_id cannot be empty")
        if not self.current_phase:
            raise ValueError("current_phase cannot be empty")


@dataclass(frozen=True)
class DecisionDTO:
    """Project decision data."""

    decision_id: str
    decision_type: str
    title: str
    rationale: str
    made_by_role: str
    made_by_agent: str

    def __post_init__(self) -> None:
        """Validate DTO fields."""
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty")
        if not self.decision_type:
            raise ValueError("decision_type cannot be empty")
        if not self.title:
            raise ValueError("title cannot be empty")
        if not self.rationale:
            raise ValueError("rationale cannot be empty")


@dataclass(frozen=True)
class TaskDTO:
    """Task data."""

    task_id: str
    role: str
    description: str
    context: str
    rationale: str

    def __post_init__(self) -> None:
        """Validate DTO fields."""
        if not self.task_id:
            raise ValueError("task_id cannot be empty")
        if not self.role:
            raise ValueError("role cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")

