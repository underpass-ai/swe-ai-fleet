"""vLLM client for agent planning and reasoning."""

import json
import logging
from typing import Any

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

logger = logging.getLogger(__name__)


class VLLMClient:
    """
    Client for calling vLLM API to generate agent plans and reasoning.
    
    Used by VLLMAgent for:
    - Generating execution plans from tasks
    - Deciding next actions in iterative mode
    - Analyzing tool results
    """
    
    def __init__(
        self,
        vllm_url: str,
        model: str = "Qwen/Qwen3-0.6B",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60,
    ):
        """
        Initialize vLLM client.
        
        Args:
            vllm_url: URL of vLLM server (e.g., "http://vllm-server-service:8000")
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            timeout: Request timeout in seconds
        """
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp required for vLLM client. Install with: pip install aiohttp")
        
        self.vllm_url = vllm_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        logger.info(f"VLLMClient initialized: {model} at {vllm_url}")
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate text using vLLM API.
        
        Args:
            system_prompt: System instruction
            user_prompt: User query/task
            temperature: Override default temperature
            max_tokens: Override default max tokens
        
        Returns:
            Generated text content
        
        Raises:
            RuntimeError: If vLLM API call fails
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temp,
            "max_tokens": max_tok,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.vllm_url}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    content = data["choices"][0]["message"]["content"]
                    logger.debug(f"vLLM generated {len(content)} characters")
                    return content.strip()
                    
        except aiohttp.ClientError as e:
            logger.error(f"vLLM API error: {e}")
            raise RuntimeError(f"Failed to call vLLM API at {self.vllm_url}: {e}") from e
        except KeyError as e:
            logger.error(f"Invalid vLLM response format: {e}")
            raise RuntimeError(f"Invalid vLLM API response: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error calling vLLM: {e}")
            raise RuntimeError(f"vLLM client error: {e}") from e
    
    async def generate_plan(
        self,
        task: str,
        context: str,
        role: str,
        available_tools: dict[str, Any],
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate execution plan for a task.
        
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
        system_prompt += f"You have access to the following tools:\n{json.dumps(available_tools['capabilities'], indent=2)}\n\n"
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
        
        # Call vLLM
        response = await self.generate(system_prompt, user_prompt)
        
        # Parse JSON from response
        try:
            # Try to extract JSON if wrapped in markdown
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
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
            logger.error(f"Failed to parse plan from vLLM response: {e}")
            logger.debug(f"Response was: {response}")
            
            # Fallback to simple plan
            return {
                "reasoning": "Failed to parse vLLM response, using fallback",
                "steps": [
                    {"tool": "files", "operation": "list_files", "params": {"path": ".", "recursive": False}}
                ]
            }
    
    async def decide_next_action(
        self,
        task: str,
        context: str,
        observation_history: list[dict],
        available_tools: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Decide next action based on task and observation history (ReAct-style).
        
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
        
        # Call vLLM
        response = await self.generate(system_prompt, user_prompt)
        
        # Parse response
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            
            decision = json.loads(response)
            return decision
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse decision from vLLM: {e}")
            # Fallback: mark as done
            return {"done": True, "reasoning": "Failed to parse vLLM response"}

