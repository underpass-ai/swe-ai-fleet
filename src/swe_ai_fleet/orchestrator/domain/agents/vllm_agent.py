"""vLLM Agent implementation for production use.

This module provides a real LLM agent that uses vLLM server with OpenAI-compatible API
for generating proposals, critiques, and revisions in the orchestration workflow.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

import aiohttp

if TYPE_CHECKING:
    from ..tasks.task_constraints import TaskConstraints

from .agent import Agent

logger = logging.getLogger(__name__)


class VLLMAgent(Agent):
    """vLLM agent for real LLM-based task execution.
    
    This agent connects to a vLLM server using OpenAI-compatible API endpoints
    to generate proposals, critiques, and revisions using real language models.
    
    Example:
        >>> agent = VLLMAgent(
        ...     agent_id="agent-dev-001",
        ...     role="DEV", 
        ...     vllm_url="http://localhost:8000",
        ...     model="meta-llama/Llama-2-7b-chat-hf"
        ... )
        >>> proposal = await agent.generate("Implement login", constraints, diversity=True)
        >>> feedback = await agent.critique(proposal["content"], rubric)
        >>> revised = await agent.revise(proposal["content"], feedback)
    """
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        vllm_url: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 30,
    ):
        """Initialize vLLM agent.
        
        Args:
            agent_id: Unique identifier for this agent (e.g., "agent-dev-001")
            role: Role of the agent (e.g., "DEV", "QA", "ARCHITECT")
            vllm_url: Base URL of the vLLM server (e.g., "http://localhost:8000")
            model: Model name to use (e.g., "meta-llama/Llama-2-7b-chat-hf")
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
        """
        self.agent_id = agent_id
        self.role = role
        self.vllm_url = vllm_url.rstrip('/')
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # OpenAI-compatible endpoints
        self.chat_endpoint = urljoin(self.vllm_url, "/v1/chat/completions")
        self.completions_endpoint = urljoin(self.vllm_url, "/v1/completions")
        
        logger.info(
            f"Initialized VLLMAgent {self.agent_id} with role {self.role} "
            f"using model {self.model} at {self.vllm_url}"
        )
    
    async def generate(
        self,
        task: str,
        constraints: TaskConstraints,
        diversity: bool = False,
    ) -> dict[str, Any]:
        """Generate a proposal for a task using vLLM.
        
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
            
            # Generate proposal
            response = await self._call_vllm_chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            proposal_content = response.strip()
            
            return {
                "content": proposal_content,
                "metadata": {
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "model": self.model,
                    "diversity": diversity,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating proposal for agent {self.agent_id}: {e}")
            # Fallback to basic proposal
            return self._fallback_proposal(task, constraints, diversity)
    
    async def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        """Generate critique for a proposal using vLLM.
        
        Args:
            proposal: Proposal content to critique
            rubric: Evaluation rubric/criteria
            
        Returns:
            Feedback as a string
        """
        try:
            system_prompt = self._build_critique_system_prompt(rubric)
            user_prompt = f"Please critique this proposal:\n\n{proposal}"
            
            response = await self._call_vllm_chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating critique for agent {self.agent_id}: {e}")
            return f"Unable to provide critique due to error: {str(e)}"
    
    async def revise(self, content: str, feedback: str) -> str:
        """Apply revision based on feedback using vLLM.
        
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
            
            response = await self._call_vllm_chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error revising proposal for agent {self.agent_id}: {e}")
            # Return original content with error note
            return f"{content}\n\n[Revision failed due to error: {str(e)}]"
    
    async def _call_vllm_chat(self, messages: list[dict[str, str]]) -> str:
        """Call vLLM chat completions endpoint."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.post(self.chat_endpoint, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"vLLM API error {response.status}: {error_text}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]
    
    def _build_system_prompt(self, constraints: TaskConstraints, diversity: bool) -> str:
        """Build system prompt for proposal generation."""
        rubric = constraints.get_rubric()
        rubric_items = list(rubric.keys())
        
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
        additional_constraints = constraints.get_cluster_spec() or {}
        
        prompt = f"Task: {task}\n\n"
        
        # Add any additional requirements from constraints
        if additional_constraints:
            prompt += "Additional constraints:\n"
            for key, value in additional_constraints.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"
        
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
        """Generate fallback proposal when vLLM is unavailable."""
        logger.warning(f"Using fallback proposal for agent {self.agent_id}")
        
        rubric = constraints.get_rubric()
        rubric_items = list(rubric.keys())[:3]
        
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
This is a fallback proposal generated when vLLM service was unavailable.
Please ensure proper implementation when service is restored.
"""
        
        return {
            "content": fallback_content,
            "metadata": {
                "agent_id": self.agent_id,
                "role": self.role,
                "model": "fallback",
                "diversity": diversity,
                "error": "vLLM unavailable",
            }
        }
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"VLLMAgent(id={self.agent_id}, role={self.role}, "
            f"model={self.model}, url={self.vllm_url})"
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.agent_id} ({self.role}) - {self.model} via {self.vllm_url}"


# Async wrapper for sync interface compatibility
# AsyncVLLMAgent REMOVED - Was causing asyncio.run() in async context bug
# All code is now async, no need for sync wrappers
# See BUG_ASYNCIO_RUN_IN_VLLM_AGENT.md for details
