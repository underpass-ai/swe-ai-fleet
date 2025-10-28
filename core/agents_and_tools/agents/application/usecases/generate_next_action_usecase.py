"""Use case for deciding next action (ReAct pattern)."""

import json
import logging

from core.agents_and_tools.agents.application.dtos.next_action_dto import NextActionDTO
from core.agents_and_tools.agents.domain.entities.observation_histories import ObservationHistories
from core.agents_and_tools.agents.domain.ports.llm_client import LLMClientPort
from core.agents_and_tools.agents.infrastructure.mappers.execution_step_mapper import ExecutionStepMapper
from core.agents_and_tools.agents.infrastructure.services.json_response_parser import (
    JSONResponseParser,
)
from core.agents_and_tools.agents.infrastructure.services.prompt_loader import PromptLoader
from core.agents_and_tools.common.domain.entities import AgentCapabilities

logger = logging.getLogger(__name__)


class GenerateNextActionUseCase:
    """
    Use case for deciding next action using ReAct (Reasoning + Acting) pattern.

    This use case contains the business logic for:
    - Building prompts for iterative decision-making
    - Formatting observation history for LLM
    - Parsing LLM responses into action decisions
    - Handling task completion detection
    """

    def __init__(
        self,
        llm_client: LLMClientPort,
        prompt_loader: PromptLoader | None = None,
        json_parser: JSONResponseParser | None = None,
    ):
        """
        Initialize use case with LLM client port.

        Args:
            llm_client: Port for LLM communication (low-level API calls)
            prompt_loader: Optional PromptLoader (default: create new instance)
            json_parser: Optional JSONResponseParser (default: create new instance)
        """
        self.llm_client = llm_client
        self.step_mapper = ExecutionStepMapper()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.json_parser = json_parser or JSONResponseParser()

    async def execute(
        self,
        task: str,
        context: str,
        observation_history: ObservationHistories,
        available_tools: AgentCapabilities,
    ) -> NextActionDTO:
        """
        Decide next action based on task and observation history (ReAct-style).

        This method contains business logic moved from VLLMClient.decide_next_action():
        - Build system prompt for ReAct pattern
        - Build user prompt with task, context, and observation history
        - Call llm_client.generate() (low-level LLM call)
        - Parse JSON response
        - Return NextActionDTO

        Args:
            task: Original task
            context: Project context
            observation_history: Previous actions and their results (ObservationHistories entity)
            available_tools: Available tool operations (AgentCapabilities entity)

        Returns:
            NextActionDTO with done, step, and reasoning
        """
        # Load prompt templates from YAML
        system_template = self.prompt_loader.get_system_prompt_template("next_action_react")
        user_template = self.prompt_loader.get_user_prompt_template("next_action_react")

        # Build system prompt from template
        tools_json = json.dumps(available_tools.capabilities, indent=2)
        system_prompt = system_template.format(capabilities=tools_json)

        # Build observation history string
        recent_observations = observation_history.get_last_n(5)
        history_lines = []
        for obs in recent_observations:
            history_lines.append(f"\nIteration {obs.iteration}:")
            history_lines.append(f"  Action: {obs.action.tool}.{obs.action.operation}")
            history_lines.append(f"  Result: {obs.success}")
            if obs.error:
                history_lines.append(f"  Error: {obs.error}")
        observation_history_str = "\n".join(history_lines)

        # Build user prompt from template
        user_prompt = user_template.format(
            task=task,
            context=context,
            observation_history=observation_history_str
        )

        # Call LLM via port (low-level API call)
        response = await self.llm_client.generate(system_prompt, user_prompt)

        # Parse JSON from response using parser service
        decision = self.json_parser.parse_json_response(response)

        # Convert step dict to ExecutionStep if present
        step_dict = decision.get("step")
        step_entity = self.step_mapper.to_entity(step_dict) if step_dict else None

        return NextActionDTO(
            done=decision.get("done", False),
            step=step_entity,
            reasoning=decision.get("reasoning", "No reasoning provided"),
        )

