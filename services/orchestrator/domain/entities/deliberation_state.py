"""Deliberation state entity for tracking active deliberations.

This entity encapsulates the state of an ongoing deliberation, replacing
the raw dictionary used in DeliberationResultCollector.

Following Domain-Driven Design:
- Entity with identity (task_id)
- Encapsulates state and behavior
- Replaces dict[str, Any] with strong typing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AgentResponse:
    """Individual agent response within a deliberation.
    
    Attributes:
        agent_id: Agent identifier
        role: Agent role
        proposal: Agent's proposal/response
        duration_ms: Time taken by agent
        timestamp: When response was received
    """
    
    agent_id: str
    role: str
    proposal: dict[str, Any]
    duration_ms: int
    timestamp: str


@dataclass
class AgentFailure:
    """Individual agent failure within a deliberation.
    
    Attributes:
        agent_id: Agent identifier
        error: Error message
        timestamp: When failure occurred
    """
    
    agent_id: str
    error: str
    timestamp: str


@dataclass
class DeliberationState:
    """Entity representing the state of an ongoing deliberation.
    
    This entity tracks the progress of a deliberation as agent responses
    arrive, applying "Tell, Don't Ask" principle by encapsulating
    state management logic.
    
    Attributes:
        task_id: Unique task identifier (entity identity)
        expected_agents: Expected number of agent responses
        received: List of successful agent responses
        failed: List of failed agent responses
        started_at: When deliberation started
        completed_at: When deliberation completed (None if in progress)
        status: Current status ("in_progress", "completed", "failed")
        final_result: Final result dict (None if not completed)
    """
    
    task_id: str
    expected_agents: int | None = None
    received: list[AgentResponse] = field(default_factory=list)
    failed: list[AgentFailure] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    status: str = "in_progress"
    final_result: dict[str, Any] | None = None
    
    def set_expected_agents(self, count: int) -> None:
        """Set the expected number of agents.
        
        Tell, Don't Ask: Tell the state to set expected count.
        
        Args:
            count: Expected number of agents
        """
        if self.expected_agents is None:
            self.expected_agents = count
    
    def add_response(self, response: AgentResponse) -> None:
        """Add a successful agent response.
        
        Tell, Don't Ask: Tell the state to add a response.
        
        Args:
            response: Agent response to add
        """
        self.received.append(response)
    
    def add_failure(self, failure: AgentFailure) -> None:
        """Add a failed agent response.
        
        Tell, Don't Ask: Tell the state to add a failure.
        
        Args:
            failure: Agent failure to add
        """
        self.failed.append(failure)
    
    def is_complete(self) -> bool:
        """Check if deliberation is complete.
        
        Tell, Don't Ask: Ask the state if it's complete,
        don't access fields directly.
        
        Returns:
            True if all expected responses received
        """
        if self.expected_agents is None:
            return False
        
        total_responses = len(self.received) + len(self.failed)
        return total_responses >= self.expected_agents
    
    def all_failed(self) -> bool:
        """Check if all agents failed.
        
        Tell, Don't Ask: Ask the state if all failed.
        
        Returns:
            True if expected agents is set and all failed
        """
        if self.expected_agents is None:
            return False
        
        total_responses = len(self.received) + len(self.failed)
        return (
            total_responses >= self.expected_agents
            and len(self.received) == 0
        )
    
    def mark_completed(self, result: dict[str, Any]) -> None:
        """Mark deliberation as completed.
        
        Tell, Don't Ask: Tell the state to mark as completed.
        
        Args:
            result: Final deliberation result
        """
        self.status = "completed"
        self.final_result = result
        self.completed_at = datetime.now(UTC)
    
    def mark_failed(self, error_message: str) -> None:
        """Mark deliberation as failed.
        
        Tell, Don't Ask: Tell the state to mark as failed.
        
        Args:
            error_message: Error description
        """
        self.status = "failed"
        self.final_result = {"error": error_message}
        self.completed_at = datetime.now(UTC)
    
    def get_progress_count(self) -> tuple[int, int]:
        """Get progress as (received, expected) count.
        
        Tell, Don't Ask: Ask the state for progress.
        
        Returns:
            Tuple of (received_count, expected_count)
        """
        received_count = len(self.received)
        expected_count = self.expected_agents or 0
        return (received_count, expected_count)
    
    def get_duration_ms(self) -> int:
        """Calculate duration in milliseconds.
        
        Tell, Don't Ask: Ask the state to calculate duration.
        
        Returns:
            Duration in milliseconds
        """
        if self.completed_at:
            delta = self.completed_at - self.started_at
        else:
            delta = datetime.now(UTC) - self.started_at
        
        return int(delta.total_seconds() * 1000)
    
    def is_in_progress(self) -> bool:
        """Check if deliberation is still in progress.
        
        Returns:
            True if status is "in_progress"
        """
        return self.status == "in_progress"
    
    def is_timed_out(self, timeout_seconds: int) -> bool:
        """Check if deliberation has timed out.
        
        Tell, Don't Ask: Ask the state if it timed out.
        
        Args:
            timeout_seconds: Timeout threshold in seconds
            
        Returns:
            True if in progress and older than timeout
        """
        if not self.is_in_progress():
            return False
        
        age = (datetime.now(UTC) - self.started_at).total_seconds()
        return age > timeout_seconds
    
    def should_cleanup(self, cleanup_after_seconds: int) -> bool:
        """Check if deliberation should be cleaned up.
        
        Tell, Don't Ask: Ask the state if it should be cleaned up.
        
        Args:
            cleanup_after_seconds: Cleanup threshold in seconds
            
        Returns:
            True if completed/failed and older than threshold
        """
        if self.status not in ["completed", "failed"] or not self.completed_at:
            return False
        
        age = (datetime.now(UTC) - self.completed_at).total_seconds()
        return age > cleanup_after_seconds

