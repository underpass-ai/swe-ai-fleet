"""List councils use case."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.orchestrator.domain.entities import CouncilRegistry
    from services.orchestrator.domain.ports import CouncilQueryPort


class ListCouncilsUseCase:
    """Use case for listing all active councils.
    
    This use case orchestrates the retrieval of council information
    using the CouncilQueryPort abstraction.
    
    Following Clean Architecture:
    - Use case coordinates domain entities and ports
    - No infrastructure dependencies (uses ports)
    - Pure business logic
    """
    
    def __init__(self, council_query: CouncilQueryPort):
        """Initialize use case with dependencies.
        
        Args:
            council_query: Port for querying council information (injected)
        """
        self.council_query = council_query
    
    def execute(
        self,
        council_registry: CouncilRegistry,
        include_agents: bool = False
    ) -> list:
        """Execute the list councils use case.
        
        Args:
            council_registry: Council registry to query
            include_agents: Whether to include detailed agent information
            
        Returns:
            List of CouncilInfo objects with council and agent details
        """
        # Delegate to port (Tell, Don't Ask)
        return self.council_query.list_councils(
            council_registry=council_registry,
            include_agents=include_agents
        )

