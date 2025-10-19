"""Use case for deleting a council."""

from __future__ import annotations

from typing import NamedTuple

from services.orchestrator.domain.entities import CouncilRegistry


class CouncilDeletionResult(NamedTuple):
    """Result of council deletion.
    
    Attributes:
        role: Role of the deleted council
        agents_removed: Number of agents that were removed
        success: Whether deletion was successful
        message: Result message
    """
    role: str
    agents_removed: int
    success: bool
    message: str


class DeleteCouncilUseCase:
    """Use case for deleting a council and its agents.
    
    Encapsulates the business logic for council deletion,
    ensuring proper cleanup and validation.
    
    Follows Single Responsibility Principle: only handles council deletion.
    """
    
    def __init__(self, council_registry: CouncilRegistry):
        """Initialize the use case.
        
        Args:
            council_registry: Registry to delete the council from
        """
        self._council_registry = council_registry
    
    def execute(self, role: str) -> CouncilDeletionResult:
        """Delete a council for the given role.
        
        Args:
            role: Role name of the council to delete
            
        Returns:
            CouncilDeletionResult with deletion details
            
        Raises:
            ValueError: If role is empty or council not found
            
        Example:
            >>> registry = CouncilRegistry()
            >>> use_case = DeleteCouncilUseCase(registry)
            >>> result = use_case.execute("Coder")
            >>> print(f"Deleted {result.agents_removed} agents")
        """
        # Fail-fast: Role must be provided
        if not role or not role.strip():
            raise ValueError("Role cannot be empty for council deletion")
        
        # Tell, Don't Ask: Registry handles deletion
        # Raises ValueError if council not found
        _council, agents_count = self._council_registry.delete_council(role)
        
        # Return successful result
        return CouncilDeletionResult(
            role=role,
            agents_removed=agents_count,
            success=True,
            message=f"Council {role} deleted successfully"
        )

