"""Get Councils Info Use Case.

This use case encapsulates the business logic for retrieving
detailed information about active councils and their agents.

Following Hexagonal Architecture:
- Orchestrates councils information retrieval
- Uses OrchestratorQueryPort abstraction
- No knowledge of infrastructure details (gRPC, protobuf, etc.)
- Pure business logic
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.monitoring.domain.entities.orchestrator.council_info import CouncilInfo
    from services.monitoring.domain.ports.orchestrator.orchestrator_info_port import OrchestratorInfoPort


class GetCouncilsInfoUseCase:
    """Use case for retrieving detailed information about active councils.
    
    This use case encapsulates the business logic for councils
    information retrieval, delegating to the OrchestratorQueryPort
    abstraction for data access.
    
    Following Clean Architecture:
    - Use case coordinates domain entities and ports
    - No infrastructure dependencies (uses ports)
    - Pure business logic
    """
    
    def __init__(self, orchestrator_info: OrchestratorInfoPort):
        """Initialize use case with dependencies.
        
        Args:
            orchestrator_info: Port for querying orchestrator information (injected)
        """
        self._orchestrator_info = orchestrator_info
    
    async def execute(self) -> list[CouncilInfo]:
        """Execute the councils info retrieval use case.
        
        Returns:
            List of CouncilInfo objects with council and agent details
            
        Raises:
            ConnectionError: If orchestrator is not available
            RuntimeError: If orchestrator query fails
            
        Example:
            >>> use_case = GetCouncilsInfoUseCase(orchestrator_query_port)
            >>> councils = await use_case.execute()
            >>> print(f"Found {len(councils)} councils")
            >>> for council in councils:
            ...     print(f"Council {council.role}: {council.total_agents} agents")
        """
        # Get orchestrator info and extract councils
        orchestrator_info = await self._orchestrator_info.get_orchestrator_info()
        
        # Return councils list
        return orchestrator_info.councils
