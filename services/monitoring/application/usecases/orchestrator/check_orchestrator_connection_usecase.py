"""Check Orchestrator Connection Use Case.

This use case encapsulates the business logic for checking
orchestrator service connectivity and health status.

Following Hexagonal Architecture:
- Orchestrates connection health checking
- Uses OrchestratorQueryPort abstraction
- No knowledge of infrastructure details (gRPC, protobuf, etc.)
- Pure business logic
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.monitoring.domain.ports.orchestrator.orchestrator_query_port import OrchestratorQueryPort


class CheckOrchestratorConnectionUseCase:
    """Use case for checking orchestrator service connectivity.
    
    This use case encapsulates the business logic for verifying
    orchestrator service health and connectivity status.
    
    Following Clean Architecture:
    - Use case coordinates domain entities and ports
    - No infrastructure dependencies (uses ports)
    - Pure business logic
    """
    
    def __init__(self, orchestrator_query: OrchestratorQueryPort):
        """Initialize use case with dependencies.
        
        Args:
            orchestrator_query: Port for querying orchestrator information (injected)
        """
        self._orchestrator_query = orchestrator_query
    
    async def execute(self) -> bool:
        """Execute the orchestrator connection check use case.
        
        Returns:
            True if orchestrator is available and healthy, False otherwise
            
        Example:
            >>> use_case = CheckOrchestratorConnectionUseCase(orchestrator_query_port)
            >>> is_connected = await use_case.execute()
            >>> print(f"Orchestrator connected: {is_connected}")
        """
        # Delegate to port (Tell, Don't Ask)
        return await self._orchestrator_query.is_orchestrator_available()
