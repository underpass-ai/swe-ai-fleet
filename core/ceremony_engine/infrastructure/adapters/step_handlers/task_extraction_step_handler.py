"""TaskExtractionStepHandler: Extracts tasks from artifacts.

Following Hexagonal Architecture:
- This is an infrastructure adapter
- Executes task extraction steps
- Returns domain value objects (StepResult)
"""

from core.ceremony_engine.application.use_cases.submit_task_extraction_usecase import (
    SubmitTaskExtractionUseCase,
)
from core.ceremony_engine.domain.value_objects.context_key import ContextKey
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.step_result import StepResult
from core.ceremony_engine.infrastructure.adapters.step_handlers.base_step_handler import (
    BaseStepHandler,
)


class TaskExtractionStepHandler(BaseStepHandler):
    """Handler for task_extraction_step steps.

    Extracts tasks from artifacts (deliberations, documents, etc.).

    Config requirements:
    - source: Source artifact ID or path
    - extraction_prompt: Prompt for task extraction (optional)

    Following Hexagonal Architecture:
    - This is infrastructure (adapter)
    - Submits task extraction via application use case
    """

    def __init__(self, task_extraction_use_case: SubmitTaskExtractionUseCase) -> None:
        """Initialize handler with required task extraction use case."""
        if not task_extraction_use_case:
            raise ValueError("task_extraction_use_case is required (fail-fast)")
        self._task_extraction_use_case = task_extraction_use_case

    async def execute(
        self,
        step: Step,
        context: ExecutionContext,
    ) -> StepResult:
        """Execute task extraction step.

        Args:
            step: Step to execute
            context: Execution context (inputs, artifacts, etc.)

        Returns:
            StepResult with extracted tasks

        Raises:
            ValueError: If config is invalid
        """
        # Validate config
        self._validate_config(step, required_keys=["source"])

        # Extract config
        source = step.config["source"]
        inputs = context.get(ContextKey.INPUTS)
        if not isinstance(inputs, dict):
            raise ValueError("task_extraction_step requires inputs in ExecutionContext")
        story_id = inputs.get("story_id")
        ceremony_id = inputs.get("ceremony_id")
        agent_deliberations = inputs.get("agent_deliberations")
        if not isinstance(story_id, str) or not story_id.strip():
            raise ValueError("task_extraction_step requires non-empty story_id in inputs")
        if not isinstance(ceremony_id, str) or not ceremony_id.strip():
            raise ValueError("task_extraction_step requires non-empty ceremony_id in inputs")
        if not isinstance(agent_deliberations, list) or not agent_deliberations:
            raise ValueError("task_extraction_step requires agent_deliberations list in inputs")

        submission = await self._task_extraction_use_case.execute(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_deliberations=agent_deliberations,
        )

        output = {
            "source": source,
            "task_id": submission["task_id"],
            "deliberation_id": submission["deliberation_id"],
            "status": submission["status"],
        }

        return self._create_success_result(output)
