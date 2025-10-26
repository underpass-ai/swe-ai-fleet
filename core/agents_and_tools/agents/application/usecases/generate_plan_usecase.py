"""Use case for generating execution plans."""

import json
import logging
from typing import Any

from core.agents_and_tools.agents.domain.ports.llm_client import LLMClientPort

logger = logging.getLogger(__name__)

# Constants
JSON_CODE_BLOCK_START = "```json"
JSON_CODE_BLOCK_END = "```"
JSON_MARKDOWN_DELIMITER_LEN = 7  # Length of "```json"


class GeneratePlanUseCase:
    """
    Use case for generating execution plans using LLM.

    This use case contains the business logic for:
    - Building prompts for execution planning
    - Parsing LLM responses into plan structures
    - Handling fallback plans on errors
    - Role-specific prompt engineering
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
        role: str,
        available_tools: dict[str, Any],
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate execution plan for a task.

        This method contains business logic moved from VLLMClient.generate_plan():
        - Build system prompt with role context
        - Build user prompt with task and context
        - Call llm_client.generate() (low-level LLM call)
        - Parse JSON response
        - Return plan dict

        Args:
            task: Task description
            context: Smart context from Context Service
            role: Agent role (DEV, QA, ARCHITECT, etc)
            available_tools: Tool descriptions from agent.get_available_tools()
            constraints: Task constraints

        Returns:
            Dictionary with:
            - steps: list[dict] - Execution steps
            - reasoning: str - Why this plan
        """
        constraints = constraints or {}

        # Build system prompt with role context
        role_prompts = {
            "DEV": "You are an expert software developer focused on writing clean, maintainable code.",
            "QA": "You are an expert QA engineer focused on testing and quality validation.",
            "ARCHITECT": "You are a senior software architect focused on design and analysis.",
            "DEVOPS": "You are a DevOps engineer focused on deployment and infrastructure.",
            "DATA": "You are a data engineer focused on databases and data pipelines.",
        }

        system_prompt = role_prompts.get(role, f"You are an expert {role} engineer.")
        system_prompt += "\n\n"
        tools_json = json.dumps(available_tools['capabilities'], indent=2)
        system_prompt += f"You have access to the following tools:\n{tools_json}\n\n"
        system_prompt += f"Mode: {available_tools['mode']}\n\n"
        system_prompt += "Generate a step-by-step execution plan in JSON format."

        # Build user prompt
        user_prompt = f"""Task: {task}

Context:
{context}

Generate an execution plan as a JSON object with this structure:
{{
  "reasoning": "Why this approach...",
  "steps": [
    {{"tool": "files", "operation": "read_file", "params": {{"path": "src/file.py"}}}},
    {{"tool": "tests", "operation": "pytest", "params": {{"path": "tests/"}}}},
    ...
  ]
}}

Use ONLY the available tools listed above. Be specific with file paths based on the context.
"""

        # Call LLM via port (low-level API call)
        response = await self.llm_client.generate(system_prompt, user_prompt)

        # Parse JSON from response (business logic)
        try:
            # Try to extract JSON if wrapped in markdown
            if JSON_CODE_BLOCK_START in response:
                json_start = response.find(JSON_CODE_BLOCK_START) + JSON_MARKDOWN_DELIMITER_LEN
                json_end = response.find(JSON_CODE_BLOCK_END, json_start)
                response = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()

            plan = json.loads(response)

            if "steps" not in plan:
                raise ValueError("Plan missing 'steps' field")

            return plan

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse plan from LLM response: {e}")
            logger.debug(f"Response was: {response}")

            # Fallback to simple plan
            return {
                "reasoning": "Failed to parse LLM response, using fallback",
                "steps": [
                    {"tool": "files", "operation": "list_files", "params": {"path": ".", "recursive": False}}
                ]
            }

