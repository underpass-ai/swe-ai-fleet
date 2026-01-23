"""HumanGateStepHandler: Handles human approval gates.

Following Hexagonal Architecture:
- This is an infrastructure adapter
- Executes human gate steps (waiting for human approval)
- Returns domain value objects (StepResult)
"""

from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.context_key import ContextKey
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.step_result import StepResult
from core.ceremony_engine.domain.value_objects.step_status import StepStatus
from core.ceremony_engine.infrastructure.adapters.step_handlers.base_step_handler import (
    BaseStepHandler,
)


class HumanGateStepHandler(BaseStepHandler):
    """Handler for human_gate_step steps.

    Waits for human approval/decision before proceeding.

    Config requirements:
    - role: Role required for approval (e.g., "product_owner")
    - message: Message/prompt for human

    Following Hexagonal Architecture:
    - This is infrastructure (adapter)
    - Checks context for human approval
    - Returns WAITING_FOR_HUMAN if not approved, COMPLETED if approved
    """

    async def execute(
        self,
        step: Step,
        context: ExecutionContext,
    ) -> StepResult:
        """Execute human gate step.

        Args:
            step: Step to execute
            context: Execution context (should contain ContextKey.HUMAN_APPROVALS)

        Returns:
            StepResult with status:
            - WAITING_FOR_HUMAN if not approved
            - COMPLETED if approved
            - FAILED if rejected

        Raises:
            ValueError: If config is invalid
        """
        # Validate config
        self._validate_config(step, required_keys=["role", "message"])

        # Extract config
        role = step.config["role"]
        message = step.config["message"]

        # Check for human approval in context
        human_approvals = context.get_mapping(ContextKey.HUMAN_APPROVALS) or {}
        step_approval_key = f"{step.id.value}:{role}"

        if step_approval_key not in human_approvals:
            # No approval yet - return WAITING_FOR_HUMAN status
            return StepResult(
                status=StepStatus.WAITING_FOR_HUMAN,
                output={"role": role, "message": message, "waiting": True},
                metadata={"step_id": step.id.value, "role": role},
            )

        approval = human_approvals[step_approval_key]
        if approval:
            # Approved - return COMPLETED
            return self._create_success_result(
                output={
                    "role": role,
                    "message": message,
                    "approved": True,
                },
                metadata={"step_id": step.id.value, "role": role},
            )
        else:
            # Rejected - return FAILED
            return self._create_failure_result(
                error_message=f"Human gate rejected by {role}",
                metadata={"step_id": step.id.value, "role": role},
            )
