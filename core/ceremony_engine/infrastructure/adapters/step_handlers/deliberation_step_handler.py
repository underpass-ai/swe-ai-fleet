"""DeliberationStepHandler: Submits deliberation steps.

Following Hexagonal Architecture:
- This is an infrastructure adapter
- Submits deliberation steps via application use case
- Returns domain value objects (StepResult)
"""

from core.ceremony_engine.application.use_cases.submit_deliberation_usecase import (
    SubmitDeliberationUseCase,
)
from core.ceremony_engine.domain.value_objects.context_key import ContextKey
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.step_result import StepResult
from core.ceremony_engine.infrastructure.adapters.step_handlers.base_step_handler import (
    BaseStepHandler,
)


class DeliberationStepHandler(BaseStepHandler):
    """Handler for deliberation_step steps.

    Submits a deliberation job and returns submission metadata.

    Config requirements:
    - prompt: Deliberation prompt/question
    - role: Role string for deliberation
    - num_agents: Number of agents for deliberation

    Following Hexagonal Architecture:
    - This is infrastructure (adapter)
    - Submits via port-backed application use case
    """

    def __init__(self, deliberation_use_case: SubmitDeliberationUseCase) -> None:
        """Initialize handler with required deliberation use case."""
        if not deliberation_use_case:
            raise ValueError("deliberation_use_case is required (fail-fast)")
        self._deliberation_use_case = deliberation_use_case

    async def execute(
        self,
        step: Step,
        context: ExecutionContext,
    ) -> StepResult:
        """Execute deliberation step.

        Args:
            step: Step to execute
            context: Execution context (inputs, etc.)

        Returns:
            StepResult with deliberation output

        Raises:
            ValueError: If config is invalid
        """
        # Validate config
        self._validate_config(step, required_keys=["prompt"])

        # Extract config
        prompt = step.config["prompt"]
        role = step.config.get("role")
        if not role or not str(role).strip():
            raise ValueError("deliberation_step requires 'role' in config")
        num_agents = step.config.get("num_agents")
        if num_agents is None:
            agents = step.config.get("agents")
            if not isinstance(agents, list) or not agents:
                raise ValueError("deliberation_step requires 'num_agents' or non-empty 'agents'")
            num_agents = len(agents)

        inputs = context.get(ContextKey.INPUTS)
        if not isinstance(inputs, dict):
            raise ValueError("deliberation_step requires inputs in ExecutionContext")
        story_id = inputs.get("story_id")
        ceremony_id = inputs.get("ceremony_id")
        if not isinstance(story_id, str) or not story_id.strip():
            raise ValueError("deliberation_step requires non-empty story_id in inputs")
        if not isinstance(ceremony_id, str) or not ceremony_id.strip():
            raise ValueError("deliberation_step requires non-empty ceremony_id in inputs")

        constraints = step.config.get("constraints")
        if constraints is not None and not isinstance(constraints, dict):
            raise ValueError("deliberation_step constraints must be a dict if provided")

        task_id = f"ceremony-{ceremony_id}:story-{story_id}:role-{role}"
        submission = await self._deliberation_use_case.execute(
            task_id=task_id,
            task_description=prompt,
            role=str(role),
            story_id=story_id,
            num_agents=int(num_agents),
            constraints=constraints,
        )

        output = {
            "task_id": submission["task_id"],
            "deliberation_id": submission["deliberation_id"],
            "role": submission["role"],
            "num_agents": submission["num_agents"],
            "status": submission["status"],
        }

        return self._create_success_result(output)
