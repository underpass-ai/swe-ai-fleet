"""Port for Context Service gRPC integration."""

from typing import Protocol


class ContextServicePort(Protocol):
    """Interface for Context Service gRPC operations."""

    async def initialize_project_context(
        self,
        story_id: str,
        title: str,
        description: str,
        initial_phase: str
    ) -> tuple[str, str]:
        """Initialize a new project context in Neo4j.
        
        Args:
            story_id: Unique story identifier
            title: Story title
            description: Story description
            initial_phase: Initial phase (DESIGN, BUILD, etc.)
            
        Returns:
            Tuple of (context_id, current_phase)
            
        Raises:
            RuntimeError: If service call fails
        """
        ...

    async def add_project_decision(
        self,
        story_id: str,
        decision_type: str,
        title: str,
        rationale: str,
        alternatives_considered: str,
        metadata: dict[str, str]
    ) -> str:
        """Add a project decision to Neo4j.
        
        Args:
            story_id: Story this decision belongs to
            decision_type: ARCHITECTURE, IMPLEMENTATION, TESTING, etc.
            title: Decision title
            rationale: Why this decision was made
            alternatives_considered: Alternatives that were evaluated
            metadata: Additional metadata (e.g., role, winner)
            
        Returns:
            Generated decision ID
            
        Raises:
            RuntimeError: If service call fails
        """
        ...

    async def transition_phase(
        self,
        story_id: str,
        from_phase: str,
        to_phase: str,
        rationale: str
    ) -> tuple[str, str]:
        """Record a phase transition in Neo4j.
        
        Args:
            story_id: Story transitioning
            from_phase: Previous phase
            to_phase: New phase
            rationale: Why transition occurred
            
        Returns:
            Tuple of (story_id, transitioned_at timestamp)
            
        Raises:
            RuntimeError: If service call fails
        """
        ...

