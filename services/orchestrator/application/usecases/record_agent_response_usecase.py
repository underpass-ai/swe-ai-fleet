"""Use case for recording agent responses in deliberations."""

from __future__ import annotations

from typing import NamedTuple

from services.orchestrator.domain.entities import (
    AgentFailure,
    AgentResponse,
    DeliberationStateRegistry,
)


class AgentResponseRecorded(NamedTuple):
    """Result of recording an agent response.
    
    Attributes:
        task_id: Task identifier
        is_complete: Whether deliberation is now complete
        all_failed: Whether all agents have failed
        received_count: Number of successful responses
        expected_count: Expected number of responses
    """
    
    task_id: str
    is_complete: bool
    all_failed: bool
    received_count: int
    expected_count: int


class RecordAgentResponseUseCase:
    """Use case for recording successful agent responses.
    
    This use case encapsulates the business logic for adding agent
    responses to deliberation state and checking for completion.
    
    Following Clean Architecture:
    - Coordinates domain entities (DeliberationState, AgentResponse)
    - No infrastructure dependencies
    - Pure business logic
    """
    
    def __init__(self, registry: DeliberationStateRegistry):
        """Initialize the use case.
        
        Args:
            registry: Deliberation state registry
        """
        self._registry = registry
    
    def execute(
        self,
        task_id: str,
        agent_id: str,
        role: str,
        proposal: dict,
        duration_ms: int,
        timestamp: str,
        expected_agents: int | None = None,
    ) -> AgentResponseRecorded:
        """Record a successful agent response.
        
        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            role: Agent role
            proposal: Agent's proposal/response
            duration_ms: Time taken by agent
            timestamp: When response was received
            expected_agents: Expected number of agents (from first message)
            
        Returns:
            AgentResponseRecorded with completion status
            
        Example:
            >>> use_case = RecordAgentResponseUseCase(registry)
            >>> result = use_case.execute(
            ...     task_id="task-001",
            ...     agent_id="agent-001",
            ...     role="Coder",
            ...     proposal={"code": "..."},
            ...     duration_ms=1000,
            ...     timestamp="2025-10-19T12:00:00Z",
            ...     expected_agents=3
            ... )
            >>> print(f"Complete: {result.is_complete}")
        """
        # Get or create deliberation state (Tell, Don't Ask)
        state = self._registry.get_or_create(task_id)
        
        # Set expected count if provided
        if expected_agents is not None:
            state.set_expected_agents(expected_agents)
        
        # Create and add response (domain entity)
        response = AgentResponse(
            agent_id=agent_id,
            role=role,
            proposal=proposal,
            duration_ms=duration_ms,
            timestamp=timestamp,
        )
        state.add_response(response)
        
        # Check completion status (Tell, Don't Ask)
        received_count, expected_count = state.get_progress_count()
        
        return AgentResponseRecorded(
            task_id=task_id,
            is_complete=state.is_complete(),
            all_failed=False,  # Can't be all failed if we just added success
            received_count=received_count,
            expected_count=expected_count,
        )


class RecordAgentFailureUseCase:
    """Use case for recording failed agent responses.
    
    This use case encapsulates the business logic for adding agent
    failures to deliberation state and checking for completion.
    
    Following Clean Architecture:
    - Coordinates domain entities (DeliberationState, AgentFailure)
    - No infrastructure dependencies
    - Pure business logic
    """
    
    def __init__(self, registry: DeliberationStateRegistry):
        """Initialize the use case.
        
        Args:
            registry: Deliberation state registry
        """
        self._registry = registry
    
    def execute(
        self,
        task_id: str,
        agent_id: str,
        error: str,
        timestamp: str,
    ) -> AgentResponseRecorded:
        """Record a failed agent response.
        
        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            error: Error message
            timestamp: When failure occurred
            
        Returns:
            AgentResponseRecorded with completion status
            
        Example:
            >>> use_case = RecordAgentFailureUseCase(registry)
            >>> result = use_case.execute(
            ...     task_id="task-001",
            ...     agent_id="agent-002",
            ...     error="Timeout",
            ...     timestamp="2025-10-19T12:05:00Z"
            ... )
            >>> print(f"All failed: {result.all_failed}")
        """
        # Get or create deliberation state (Tell, Don't Ask)
        state = self._registry.get_or_create(task_id)
        
        # Create and add failure (domain entity)
        failure = AgentFailure(
            agent_id=agent_id,
            error=error,
            timestamp=timestamp,
        )
        state.add_failure(failure)
        
        # Check completion status (Tell, Don't Ask)
        received_count, expected_count = state.get_progress_count()
        
        return AgentResponseRecorded(
            task_id=task_id,
            is_complete=state.is_complete(),
            all_failed=state.all_failed(),
            received_count=received_count,
            expected_count=expected_count,
        )

