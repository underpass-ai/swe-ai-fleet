"""Context port for Planning Service.

Port (interface) for Context Service integration via gRPC.
Planning Service uses Context Service to get rehydrated context by role
for task derivation.

Following Hexagonal Architecture:
- Application layer defines the port (this interface)
- Infrastructure layer provides the adapter (gRPC client)
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ContextResponse:
    """
    Response from Context Service with rehydrated context.

    Maps to GetContextResponse proto message.
    """

    context: str              # Formatted context string ready for LLM
    token_count: int          # Estimated token count
    scopes: tuple[str, ...]   # Applied scope policies
    version: str              # Context version/hash

    def __post_init__(self) -> None:
        """Validate response (fail-fast)."""
        if not self.context:
            raise ValueError("context cannot be empty")

        if self.token_count < 0:
            raise ValueError(f"token_count must be >= 0, got {self.token_count}")


class ContextPort(Protocol):
    """Port for Context Service gRPC integration.

    Responsibilities:
    - Get rehydrated context by role for a Story
    - Context includes: Story header, Plan header, Role tasks, Decisions, etc.
    - Used for task derivation and council reviews

    Following Hexagonal Architecture:
    - Port defines interface (application layer)
    - Adapter implements gRPC calls (infrastructure layer)
    - DDD: Uses ONLY Value Objects (NO primitives)
    """

    async def get_context(
        self,
        story_id: str,
        role: str,
        phase: str,
        token_budget: int = 2000,
    ) -> ContextResponse:
        """Get rehydrated context for a Story and role.

        Calls Context Service GetContext gRPC endpoint to retrieve
        role-specific context including:
        - Story header
        - Plan header
        - Role tasks
        - Relevant decisions
        - Decision dependencies
        - Impacted tasks
        - Recent milestones
        - Last summary

        Args:
            story_id: Story identifier (string)
            role: Role name (ARCHITECT, QA, DEVOPS, DEV, DATA)
            phase: Work phase (DESIGN, BUILD, TEST, DOCS)
            token_budget: Token budget hint (default: 2000)

        Returns:
            ContextResponse with formatted context and metadata

        Raises:
            ContextServiceError: If gRPC call fails or context not found
        """
        ...

