"""Get Orchestrator Info Use Case.

This use case encapsulates the business logic for retrieving complete
orchestrator information including councils, agents, and connection status.

Following Hexagonal Architecture:
- Orchestrates orchestrator information retrieval
- Uses OrchestratorQueryPort abstraction
- No knowledge of infrastructure details (gRPC, protobuf, etc.)
- Pure business logic
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.monitoring.domain.entities.orchestrator.orchestrator_info import OrchestratorInfo
    from services.monitoring.domain.ports.orchestrator.orchestrator_query_port import OrchestratorQueryPort


class GetOrchestratorInfoUseCase:
    """Use case for retrieving complete orchestrator information.
    
    This use case encapsulates the business logic for orchestrator
    information retrieval, delegating to the OrchestratorQueryPort
    abstraction for data access.
    
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
    
    async def execute(self) -> OrchestratorInfo:
        """Execute the orchestrator info retrieval use case.
        
        Returns:
            OrchestratorInfo aggregate root with complete orchestrator state
            
        Raises:
            ConnectionError: If orchestrator is not available
            RuntimeError: If orchestrator query fails
            
        Example:
            >>> use_case = GetOrchestratorInfoUseCase(orchestrator_query_port)
            >>> orchestrator_info = await use_case.execute()
            >>> print(f"Connected: {orchestrator_info.is_connected()}")
            >>> print(f"Councils: {len(orchestrator_info.councils)}")
            >>> print(f"Total Agents: {orchestrator_info.get_total_agents()}")
        """
        # Delegate to port (Tell, Don't Ask)
        return await self._orchestrator_query.get_orchestrator_info()
