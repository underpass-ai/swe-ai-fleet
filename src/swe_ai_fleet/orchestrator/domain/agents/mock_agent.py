"""Mock Agent implementation for testing and development.

This module provides a configurable mock agent that can simulate various behaviors
for testing the Deliberate and Orchestrate use cases without requiring real LLM backends.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from enum import Enum

if TYPE_CHECKING:
    from ..tasks.task_constraints import TaskConstraints

from .agent import Agent


class AgentBehavior(Enum):
    """Enum defining different agent behaviors for testing."""
    
    NORMAL = "normal"              # Standard good quality responses
    EXCELLENT = "excellent"        # High quality responses (for testing winners)
    POOR = "poor"                  # Low quality responses (for testing losers)
    VERBOSE = "verbose"            # Very detailed responses
    CONCISE = "concise"            # Minimal responses
    ERROR_PRONE = "error_prone"    # Introduces intentional errors
    INCONSISTENT = "inconsistent"  # Changes behavior between calls
    STUBBORN = "stubborn"          # Doesn't revise based on feedback


class MockAgent(Agent):
    """Mock agent for testing deliberation workflows.
    
    This agent simulates proposal generation, critique, and revision
    with configurable behaviors for different testing scenarios.
    
    Example:
        >>> agent = MockAgent("agent-1", "DEV", behavior=AgentBehavior.EXCELLENT)
        >>> proposal = agent.generate("Implement login", constraints, diversity=True)
        >>> feedback = agent.critique(proposal["content"], rubric)
        >>> revised = agent.revise(proposal["content"], feedback)
    """
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        behavior: AgentBehavior = AgentBehavior.NORMAL,
        seed: int | None = None,
    ):
        """Initialize mock agent.
        
        Args:
            agent_id: Unique identifier for this agent (e.g., "agent-dev-001")
            role: Role of the agent (e.g., "DEV", "QA", "ARCHITECT")
            behavior: Behavior mode for this agent
            seed: Random seed for reproducible behavior (optional)
        """
        self.agent_id = agent_id
        self.role = role
        self.behavior = behavior
        self.seed = seed
        
        # Track state for INCONSISTENT behavior
        self._call_count = 0
        
    def generate(
        self,
        task: str,
        constraints: TaskConstraints,
        diversity: bool = False,
    ) -> dict[str, Any]:
        """Generate a mock proposal for a task.
        
        Args:
            task: Task description to generate proposal for
            constraints: Task constraints and rubric
            diversity: Whether to increase diversity in the response
            
        Returns:
            Dictionary with "content" key containing the proposal
        """
        self._call_count += 1
        
        # Build proposal based on behavior
        proposal = self._generate_proposal_content(task, constraints, diversity)
        
        return {
            "content": proposal,
            "metadata": {
                "agent_id": self.agent_id,
                "role": self.role,
                "behavior": self.behavior.value,
                "diversity": diversity,
                "call_count": self._call_count,
            }
        }
    
    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        """Generate mock feedback for a proposal.
        
        Args:
            proposal: Proposal content to critique
            rubric: Evaluation rubric/criteria
            
        Returns:
            Feedback as a string
        """
        if self.behavior == AgentBehavior.STUBBORN:
            # Stubborn agents don't provide useful feedback
            return "Looks fine to me."
        
        if self.behavior == AgentBehavior.EXCELLENT:
            return self._generate_excellent_critique(proposal, rubric)
        
        if self.behavior == AgentBehavior.POOR:
            return self._generate_poor_critique(proposal)
        
        # Normal critique
        rubric_keys = list(rubric.keys())[:3]  # First 3 criteria
        return (
            f"Feedback from {self.agent_id}:\n"
            f"1. Consider improving: {rubric_keys[0] if rubric_keys else 'structure'}\n"
            f"2. Good approach but could be more specific\n"
            f"3. Add more detail on implementation"
        )
    
    def revise(self, content: str, feedback: str) -> str:
        """Apply mock revision based on feedback.
        
        Args:
            content: Original proposal content
            feedback: Feedback to incorporate
            
        Returns:
            Revised proposal content
        """
        if self.behavior == AgentBehavior.STUBBORN:
            # Stubborn agents don't revise
            return content
        
        if self.behavior == AgentBehavior.INCONSISTENT:
            # Inconsistent agents sometimes revise, sometimes don't
            if self._call_count % 2 == 0:
                return content
        
        # Apply revision
        revision_note = (
            f"\n\n--- REVISION by {self.agent_id} ---\n"
            f"Applied feedback:\n{feedback[:100]}...\n"
            f"---\n"
        )
        
        if self.behavior == AgentBehavior.EXCELLENT:
            revision_note += "Significantly improved based on peer feedback.\n"
        
        return content + revision_note
    
    def _generate_proposal_content(
        self,
        task: str,
        constraints: TaskConstraints,
        diversity: bool,
    ) -> str:
        """Generate proposal content based on behavior."""
        
        # Extract rubric info
        rubric = constraints.get_rubric()
        rubric_items = list(rubric.keys())[:3]
        
        # Base proposal structure
        if self.behavior == AgentBehavior.EXCELLENT:
            return self._generate_excellent_proposal(task, rubric_items, diversity)
        
        if self.behavior == AgentBehavior.POOR:
            return self._generate_poor_proposal(task)
        
        if self.behavior == AgentBehavior.VERBOSE:
            return self._generate_verbose_proposal(task, rubric_items)
        
        if self.behavior == AgentBehavior.CONCISE:
            return self._generate_concise_proposal(task)
        
        if self.behavior == AgentBehavior.ERROR_PRONE:
            return self._generate_error_prone_proposal(task)
        
        # NORMAL behavior (default)
        return self._generate_normal_proposal(task, rubric_items, diversity)
    
    def _generate_excellent_proposal(
        self,
        task: str,
        rubric_items: list[str],
        diversity: bool,
    ) -> str:
        """Generate high-quality proposal."""
        diversity_note = " (with high diversity)" if diversity else ""
        
        return f"""# Proposal by {self.agent_id} ({self.role}){diversity_note}

## Task
{task}

## Solution Approach

### Phase 1: Analysis
- Thoroughly analyze requirements
- Identify edge cases and constraints
- Document assumptions

### Phase 2: Implementation
- Follow best practices for {self.role} role
- Implement comprehensive error handling
- Add detailed logging and monitoring

### Phase 3: Validation
- Write comprehensive test suite
- Perform code review
- Document all decisions

## Quality Considerations
{chr(10).join(f"- {item}: Fully addressed with industry best practices" for item in rubric_items)}

## Risk Mitigation
- Identified potential issues early
- Implemented rollback procedures
- Added monitoring and alerts

## Documentation
- Comprehensive inline comments
- API documentation updated
- Runbook created for operations

This proposal demonstrates excellent understanding and execution quality.
"""
    
    def _generate_normal_proposal(
        self,
        task: str,
        rubric_items: list[str],
        diversity: bool,
    ) -> str:
        """Generate standard quality proposal."""
        diversity_note = " with diversity" if diversity else ""
        
        return f"""Proposal from {self.agent_id} ({self.role}){diversity_note}:

Task: {task}

Approach:
1. Analyze the requirements
2. Implement the solution following {self.role} best practices
3. Test the implementation
4. Document the changes

Quality criteria addressed:
{chr(10).join(f"- {item}: Implemented" for item in rubric_items)}

The solution follows standard practices and meets requirements.
"""
    
    def _generate_poor_proposal(self, task: str) -> str:
        """Generate low-quality proposal."""
        return f"""Quick solution from {self.agent_id}:

{task}

Just do it the simple way. Should work fine probably.
"""
    
    def _generate_verbose_proposal(
        self,
        task: str,
        rubric_items: list[str],
    ) -> str:
        """Generate overly detailed proposal."""
        return f"""# Extremely Detailed Proposal by {self.agent_id}

## Executive Summary
This proposal addresses the task: {task}

## Background and Context
Before we begin, it's important to understand the historical context...
[... many paragraphs of background ...]

## Detailed Analysis
{chr(10).join(f"### Analysis of {item}{chr(10)}This is a critical aspect that requires careful consideration...{chr(10)}" for item in rubric_items)}

## Implementation Plan (Very Detailed)
Step 1: Initial preparation
  Sub-step 1.1: Environment setup
    Sub-step 1.1.1: Check prerequisites
    Sub-step 1.1.2: Install dependencies
  Sub-step 1.2: Configuration
    [... continues in excessive detail ...]

## Conclusion
After this exhaustive analysis, we can proceed with confidence.

Total pages: 47 (simulated)
"""
    
    def _generate_concise_proposal(self, task: str) -> str:
        """Generate minimal proposal."""
        return f"{self.agent_id}: {task} - implement using standard approach. Done."
    
    def _generate_error_prone_proposal(self, task: str) -> str:
        """Generate proposal with intentional issues."""
        return f"""Proposal from {self.agent_id}:

Task: {task}

Solution:
- Missing error handling
- No input validation
- Hardcoded values: API_KEY = "12345"
- TODO: implement this part
- Code duplication in 3 places
- No tests

Should work most of the time.
"""
    
    def _generate_excellent_critique(
        self,
        proposal: str,
        rubric: dict[str, Any],
    ) -> str:
        """Generate high-quality critique."""
        return f"""Excellent peer review by {self.agent_id}:

Strengths:
- Clear structure and well-organized
- Addresses all key requirements
- Demonstrates deep understanding

Suggestions for improvement:
1. Consider adding specific metrics for success
2. Add rollback procedure for safety
3. Include performance benchmarks

The proposal shows excellent quality. Minor refinements would make it exceptional.
"""
    
    def _generate_poor_critique(self, proposal: str) -> str:
        """Generate low-quality critique."""
        return f"{self.agent_id}: Looks OK I guess."
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"MockAgent(id={self.agent_id}, role={self.role}, "
            f"behavior={self.behavior.value})"
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.agent_id} ({self.role}) - {self.behavior.value} mode"


def create_mock_council(
    role: str,
    num_agents: int = 3,
    behaviors: list[AgentBehavior] | None = None,
) -> list[MockAgent]:
    """Factory function to create a council of mock agents.
    
    Args:
        role: Role for all agents in the council
        num_agents: Number of agents to create
        behaviors: Optional list of behaviors (one per agent)
                  If not provided, uses mixed behaviors for realistic testing
    
    Returns:
        List of MockAgent instances
    
    Example:
        >>> council = create_mock_council("DEV", num_agents=3)
        >>> # Returns: [EXCELLENT, NORMAL, NORMAL] agents
        
        >>> custom_council = create_mock_council(
        ...     "QA",
        ...     num_agents=3,
        ...     behaviors=[AgentBehavior.EXCELLENT, AgentBehavior.POOR, AgentBehavior.NORMAL]
        ... )
    """
    if behaviors is None:
        # Default: 1 excellent, rest normal (realistic scenario)
        behaviors = [AgentBehavior.EXCELLENT] + [AgentBehavior.NORMAL] * (num_agents - 1)
    
    if len(behaviors) != num_agents:
        raise ValueError(
            f"Number of behaviors ({len(behaviors)}) must match num_agents ({num_agents})"
        )
    
    agents = []
    for i, behavior in enumerate(behaviors):
        agent = MockAgent(
            agent_id=f"agent-{role.lower()}-{i:03d}",
            role=role,
            behavior=behavior,
        )
        agents.append(agent)
    
    return agents

