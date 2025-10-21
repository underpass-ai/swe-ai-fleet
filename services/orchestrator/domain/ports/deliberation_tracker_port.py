"""Deliberation tracker port for managing deliberation state.

This port abstracts the tracking and storage of deliberation results,
allowing the domain to query deliberation status without knowing
about the underlying storage mechanism (in-memory, Redis, DB, etc.).

Following Hexagonal Architecture:
- Domain defines the contract (port)
- Infrastructure provides the implementation (adapter)
- Business logic remains independent of storage technology
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from services.orchestrator.domain.entities import DeliberationResultData


class DeliberationTrackerPort(ABC):
    """Port defining the interface for deliberation tracking operations.
    
    This port allows tracking ongoing deliberations and querying their results.
    It abstracts the storage mechanism (in-memory, Redis, DB) from the domain.
    
    Following Hexagonal Architecture:
    - Port (this interface) is in domain/ports/
    - Adapter (in-memory, Redis) is in infrastructure/adapters/
    - Domain uses this port without knowing storage details
    """
    
    @abstractmethod
    async def start_tracking(
        self,
        task_id: str,
        num_agents: int,
        role: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Start tracking a new deliberation.
        
        This initializes tracking for a deliberation, expecting responses
        from the specified number of agents.
        
        Args:
            task_id: Unique task identifier
            num_agents: Expected number of agent responses
            role: Role of the deliberating council
            metadata: Optional metadata (story_id, plan_id, etc.)
            
        Raises:
            ValueError: If task_id already exists
        """
        pass
    
    @abstractmethod
    def get_result(self, task_id: str) -> DeliberationResultData | None:
        """Get the current result of a deliberation.
        
        Returns the deliberation result including status, received responses,
        and any failures. Returns None if task_id not found.
        
        Args:
            task_id: Task identifier
            
        Returns:
            DeliberationResultData entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_status(self, task_id: str) -> str | None:
        """Get the status of a deliberation.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Status string ("pending", "in_progress", "completed", "failed")
            or None if not found
        """
        pass
    
    @abstractmethod
    async def record_agent_response(
        self,
        task_id: str,
        agent_id: str,
        proposal: dict[str, Any],
        duration_ms: int,
    ) -> bool:
        """Record a successful agent response.
        
        Returns True if this completes the deliberation (all agents responded).
        
        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            proposal: Agent's proposal/response
            duration_ms: Time taken by agent
            
        Returns:
            True if deliberation is now complete, False otherwise
            
        Raises:
            ValueError: If task_id not found
        """
        pass
    
    @abstractmethod
    async def record_agent_failure(
        self,
        task_id: str,
        agent_id: str,
        error: str,
    ) -> bool:
        """Record a failed agent response.
        
        Returns True if all expected responses are received (success + failures).
        
        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            error: Error message
            
        Returns:
            True if deliberation should be finalized, False otherwise
            
        Raises:
            ValueError: If task_id not found
        """
        pass
    
    @abstractmethod
    async def timeout_deliberation(self, task_id: str) -> None:
        """Mark a deliberation as timed out.
        
        This should be called when a deliberation exceeds its timeout period
        without receiving all expected responses.
        
        Args:
            task_id: Task identifier
            
        Raises:
            ValueError: If task_id not found
        """
        pass
    
    @abstractmethod
    def list_active_deliberations(self) -> list[str]:
        """List task IDs of all active (in-progress) deliberations.
        
        Returns:
            List of task IDs for deliberations that are in progress
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> dict[str, int]:
        """Get tracking statistics.
        
        Returns:
            Dictionary with counts:
            - total: Total deliberations tracked
            - in_progress: Currently active
            - completed: Successfully completed
            - failed: Failed deliberations
        """
        pass
    
    @abstractmethod
    async def cleanup_old_deliberations(self, max_age_seconds: int) -> int:
        """Clean up completed/failed deliberations older than max_age.
        
        Args:
            max_age_seconds: Maximum age in seconds
            
        Returns:
            Number of deliberations cleaned up
        """
        pass


class DeliberationNotFoundError(Exception):
    """Exception raised when a deliberation is not found.
    
    This provides a domain-level abstraction for "not found" errors,
    independent of the underlying storage mechanism.
    """
    
    def __init__(self, task_id: str):
        """Initialize error.
        
        Args:
            task_id: Task identifier that was not found
        """
        super().__init__(f"Deliberation not found: {task_id}")
        self.task_id = task_id

