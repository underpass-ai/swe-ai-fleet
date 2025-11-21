"""Context port for Planning Service.

Port (interface) for Context Service integration via gRPC.
Planning Service uses Context Service to get rehydrated context by role
for task derivation.

Following Hexagonal Architecture:
- Application layer defines the port (this interface)
- Infrastructure layer provides the adapter (gRPC client)
"""

from typing import Protocol

from planning.domain.value_objects.identifiers.story_id import StoryId


class ContextPort(Protocol):
    """Port for Context Service gRPC integration.

    Responsibilities:
    - Get rehydrated context by role for a Story
    - Context includes: Story header, Plan header, Role tasks, Decisions, etc.
    - Used for task derivation (LLM prompt construction)

    Following Hexagonal Architecture:
    - Port defines interface (application layer)
    - Adapter implements gRPC calls (infrastructure layer)
    - DDD: Uses ONLY Value Objects (NO primitives)
    """

    async def get_context(
        self,
        story_id: StoryId,
        role: str,
        phase: str = "plan",
    ) -> str:
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
            story_id: Story identifier (domain VO)
            role: Role name (e.g., "developer", "architect", "qa")
            phase: Work phase (default: "plan" for task derivation)

        Returns:
            Context string (formatted prompt blocks ready for LLM)

        Raises:
            ContextServiceError: If gRPC call fails or context not found
        """
        ...

