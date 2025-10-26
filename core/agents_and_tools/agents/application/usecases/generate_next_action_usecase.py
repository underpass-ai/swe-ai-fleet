"""Use case for deciding next action (ReAct pattern)."""

import json
import logging
from typing import Any

from core.agents.domain.ports.llm_client import LLMClientPort

logger = logging.getLogger(__name__)

# Constants
JSON_CODE_BLOCK_START = "```json"
JSON_CODE_BLOCK_END = "```"
JSON_MARKDOWN_DELIMITER_LEN = 7  # Length of "```json"


class GenerateNextActionUseCase:
    """
    Use case for deciding next action using ReAct (Reasoning + Acting) pattern.

    This use case contains the business logic for:
    - Building prompts for iterative decision-making
    - Formatting observation history for LLM
    - Parsing LLM responses into action decisions
    - Handling task completion detection
    """

    def __init__(self, llm_client: LLMClientPort):
        """
        Initialize use case with LLM client port.

        Args:
            llm_client: Port for LLM communication (low-level API calls)
        """
        self.llm_client = llm_client

    async def execute(
        self,
        task: str,
        context: str,
        observation_history: list[dict],
        available_tools: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Decide next action based on task and observation history (ReAct-style).

        This method contains business logic moved from VLLMClient.decide_next_action():
        - Build system prompt for ReAct pattern
        - Build user prompt with task, context, and observation history
        - Call llm_client.generate() (low-level LLM call)
        - Parse JSON response
        - Return decision dict

        Args:
            task: Original task
            context: Project context
            observation_history: Previous actions and their results
            available_tools: Available tool operations

        Returns:
            Dictionary with:
            - done: bool - Is task complete?
            - step: dict - Next action to take
            - reasoning: str - Why this action?
        """
        # Build system prompt
        system_prompt = f"""You are an autonomous agent using ReAct (Reasoning + Acting) pattern.

Available tools:
{json.dumps(available_tools['capabilities'], indent=2)}

Decide the next action based on task and previous observations.
Respond in JSON format:
{{
  "done": false,
  "reasoning": "Why this action...",
  "step": {{"tool": "files", "operation": "read_file", "params": {{"path": "..."}}}}
}}

Or if task is complete:
{{
  "done": true,
  "reasoning": "Task complete because..."
}}
"""

        # Build user prompt with history
        user_prompt = f"""Task: {task}

Context: {context}

Observation History:
"""
        for obs in observation_history[-5:]:  # Last 5 observations
            user_prompt += f"\nIteration {obs['iteration']}:\n"
            user_prompt += f"  Action: {obs['action']}\n"
            user_prompt += f"  Result: {obs['success']}\n"
            if obs.get('error'):
                user_prompt += f"  Error: {obs['error']}\n"

        user_prompt += "\nWhat should I do next?"

        # Call LLM via port (low-level API call)
        response = await self.llm_client.generate(system_prompt, user_prompt)

        # Parse response (business logic)
        try:
            if JSON_CODE_BLOCK_START in response:
                json_start = response.find(JSON_CODE_BLOCK_START) + JSON_MARKDOWN_DELIMITER_LEN
                json_end = response.find(JSON_CODE_BLOCK_END, json_start)
                response = response[json_start:json_end].strip()

            decision = json.loads(response)
            return decision

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse decision from LLM: {e}")
            # Fallback: mark as done
            return {"done": True, "reasoning": "Failed to parse LLM response"}

