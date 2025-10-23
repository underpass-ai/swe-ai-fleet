"""Adapter to integrate Agent interface with Model protocol.

This module bridges the gap between the orchestrator's Agent interface
and the models/ bounded context's Model protocol.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.models.loaders import Model

    from ..tasks.task_constraints import TaskConstraints

from .agent import Agent

logger = logging.getLogger(__name__)


class ModelAgentAdapter(Agent):
    """Adapter that wraps a Model to implement the Agent interface.
    
    This adapter allows any Model from the models/ bounded context to be used
    as an Agent in the orchestrator workflow.
    
    Example:
        >>> from core.models.loaders import get_model_from_env
        >>> model = get_model_from_env()
        >>> agent = ModelAgentAdapter(
        ...     model=model,
        ...     agent_id="agent-dev-001",
        ...     role="DEV"
        ... )
        >>> proposal = agent.generate("Implement login", constraints)
    """
    
    def __init__(
        self,
        model: Model,
        agent_id: str,
        role: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 30,
    ):
        """Initialize ModelAgentAdapter.
        
        Args:
            model: Model instance from models/ bounded context
            agent_id: Unique identifier for this agent
            role: Role of the agent (e.g., "DEV", "QA", "ARCHITECT")
            temperature: Sampling temperature for generation
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
        """
        self.model = model
        self.agent_id = agent_id
        self.role = role
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        logger.info(
            f"Initialized ModelAgentAdapter {self.agent_id} with role {self.role} "
            f"using model {type(model).__name__}"
        )
    
    def generate(
        self,
        task: str,
        constraints: TaskConstraints,
        diversity: bool = False,
    ) -> dict[str, Any]:
        """Generate a proposal using the underlying Model.
        
        Args:
            task: Task description to generate proposal for
            constraints: Task constraints and rubric
            diversity: Whether to increase diversity in the response
            
        Returns:
            Dictionary with "content" key containing the proposal
        """
        try:
            # Build system prompt based on role and constraints
            system_prompt = self._build_system_prompt(constraints, diversity)
            user_prompt = self._build_task_prompt(task, constraints)
            
            # Create messages for chat completion
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Generate proposal using the Model
            proposal_content = self.model.infer(
                prompt=user_prompt,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout_sec=self.timeout,
            )
            
            return {
                "content": proposal_content.strip(),
                "metadata": {
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "model_type": type(self.model).__name__,
                    "diversity": diversity,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating proposal for agent {self.agent_id}: {e}")
            # Return fallback proposal
            return self._fallback_proposal(task, constraints, diversity)
    
    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        """Generate critique using the underlying Model.
        
        Args:
            proposal: Proposal content to critique
            rubric: Evaluation rubric/criteria
            
        Returns:
            Feedback as a string
        """
        try:
            system_prompt = self._build_critique_system_prompt(rubric)
            user_prompt = f"Please critique this proposal:\n\n{proposal}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            feedback = self.model.infer(
                prompt=user_prompt,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout_sec=self.timeout,
            )
            
            return feedback.strip()
            
        except Exception as e:
            logger.error(f"Error generating critique for agent {self.agent_id}: {e}")
            return f"Unable to provide critique due to error: {str(e)}"
    
    def revise(self, content: str, feedback: str) -> str:
        """Apply revision based on feedback using the underlying Model.
        
        Args:
            content: Original proposal content
            feedback: Feedback to incorporate
            
        Returns:
            Revised proposal content
        """
        try:
            system_prompt = self._build_revision_system_prompt()
            user_prompt = f"""Please revise the following proposal based on the feedback provided.

Original Proposal:
{content}

Feedback:
{feedback}

Please provide the revised proposal that incorporates the feedback."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            revised_content = self.model.infer(
                prompt=user_prompt,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout_sec=self.timeout,
            )
            
            return revised_content.strip()
            
        except Exception as e:
            logger.error(f"Error revising proposal for agent {self.agent_id}: {e}")
            # Return original content with error note
            return f"{content}\n\n[Revision failed due to error: {str(e)}]"
    
    def _build_system_prompt(self, constraints: TaskConstraints, diversity: bool) -> str:
        """Build system prompt for proposal generation."""
        rubric = constraints.get_rubric()
        # rubric is a string, parse it to get items
        rubric_lines = rubric.strip().split('\n') if rubric else []
        rubric_items = [line.split(':')[0].strip() for line in rubric_lines if ':' in line]
        
        diversity_note = " Be creative and explore diverse approaches." if diversity else ""
        
        return f"""You are {self.agent_id}, a {self.role} agent in a software engineering team.

Your role is to generate high-quality proposals for software development tasks.
Focus on your expertise as a {self.role} professional.

Quality criteria to address:
{chr(10).join(f"- {item}" for item in rubric_items)}

Guidelines:
- Be specific and actionable
- Follow best practices for {self.role} role
- Consider edge cases and error handling
- Include implementation details
- Address all quality criteria{diversity_note}

Provide a comprehensive proposal that demonstrates your expertise."""
    
    def _build_task_prompt(self, task: str, constraints: TaskConstraints) -> str:
        """Build user prompt for task execution."""
        # Get additional constraints if available
        cluster_spec = constraints.get_cluster_spec() or ""
        
        prompt = f"Task: {task}\n\n"
        
        # Add cluster spec if available
        if cluster_spec:
            prompt += f"Additional constraints:\n{cluster_spec}\n\n"
        
        prompt += "Please provide a detailed proposal for implementing this task."
        
        return prompt
    
    def _build_critique_system_prompt(self, rubric: dict[str, Any]) -> str:
        """Build system prompt for critique generation."""
        rubric_items = list(rubric.keys())
        
        return f"""You are {self.agent_id}, a {self.role} agent providing peer review.

Your role is to critique proposals constructively and provide actionable feedback.

Evaluation criteria:
{chr(10).join(f"- {item}" for item in rubric_items)}

Guidelines:
- Be constructive and specific
- Highlight both strengths and areas for improvement
- Provide actionable suggestions
- Focus on quality and best practices
- Consider the {self.role} perspective

Provide a detailed critique that helps improve the proposal."""
    
    def _build_revision_system_prompt(self) -> str:
        """Build system prompt for revision generation."""
        return f"""You are {self.agent_id}, a {self.role} agent revising a proposal.

Your role is to incorporate feedback and improve the original proposal.

Guidelines:
- Address all feedback points constructively
- Maintain the original structure where appropriate
- Improve clarity and specificity
- Ensure all requirements are met
- Apply {self.role} best practices

Provide the revised proposal that incorporates the feedback while maintaining quality."""
    
    def _fallback_proposal(self, task: str, constraints: TaskConstraints, diversity: bool) -> dict[str, Any]:
        """Generate fallback proposal when Model is unavailable."""
        logger.warning(f"Using fallback proposal for agent {self.agent_id}")
        
        rubric = constraints.get_rubric()
        # rubric is a string, parse it to get items
        rubric_lines = rubric.strip().split('\n') if rubric else []
        rubric_items = [line.split(':')[0].strip() for line in rubric_lines if ':' in line][:3]
        
        fallback_content = f"""# Fallback Proposal by {self.agent_id} ({self.role})

## Task
{task}

## Approach
1. Analyze requirements as a {self.role} professional
2. Design solution following {self.role} best practices
3. Implement with proper error handling
4. Test thoroughly
5. Document changes

## Quality Considerations
{chr(10).join(f"- {item}: To be addressed" for item in rubric_items)}

## Note
This is a fallback proposal generated when the underlying model was unavailable.
Please ensure proper implementation when the model is restored.
"""
        
        return {
            "content": fallback_content,
            "metadata": {
                "agent_id": self.agent_id,
                "role": self.role,
                "model_type": "fallback",
                "diversity": diversity,
                "error": "Model unavailable",
            }
        }
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"ModelAgentAdapter(id={self.agent_id}, role={self.role}, "
            f"model={type(self.model).__name__})"
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.agent_id} ({self.role}) - {type(self.model).__name__}"


def create_model_agent_from_profile(
    profile_path: str,
    agent_id: str,
    role: str,
    **kwargs: Any,
) -> ModelAgentAdapter:
    """Create a ModelAgentAdapter from a model profile YAML file.
    
    Args:
        profile_path: Path to the model profile YAML file
        agent_id: Unique identifier for the agent
        role: Role of the agent
        **kwargs: Additional parameters for ModelAgentAdapter
        
    Returns:
        ModelAgentAdapter instance
        
    Example:
        >>> agent = create_model_agent_from_profile(
        ...     "profiles/developer.yaml",
        ...     "agent-dev-001",
        ...     "DEV"
        ... )
    """
    import yaml

    from core.models.loaders import get_model_from_env
    
    # Load profile
    with open(profile_path) as f:
        profile = yaml.safe_load(f)
    
    # Get model from environment (profile provides hints)
    model = get_model_from_env()
    
    # Extract model-specific parameters from profile
    adapter_kwargs = {
        "temperature": kwargs.get("temperature", 0.7),
        "max_tokens": kwargs.get("max_tokens", profile.get("context_window", 2048) // 4),
        "timeout": kwargs.get("timeout", 30),
    }
    adapter_kwargs.update(kwargs)
    
    return ModelAgentAdapter(
        model=model,
        agent_id=agent_id,
        role=role,
        **adapter_kwargs
    )
