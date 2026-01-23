"""StepHandlerRegistry: Infrastructure adapter implementing StepHandlerPort.

Following Hexagonal Architecture:
- This adapter implements StepHandlerPort (application layer interface)
- It routes step execution to appropriate concrete handlers
- Handlers are plug-and-play (can be extended without changing application layer)
"""

from typing import Any

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.application.ports.step_handler_port import StepHandlerPort
from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.ceremony_engine.application.use_cases.submit_deliberation_usecase import (
    SubmitDeliberationUseCase,
)
from core.ceremony_engine.application.use_cases.submit_task_extraction_usecase import (
    SubmitTaskExtractionUseCase,
)
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.step_handler_type import StepHandlerType
from core.ceremony_engine.domain.value_objects.step_result import StepResult
from core.ceremony_engine.infrastructure.adapters.step_handlers.aggregation_step_handler import (
    AggregationStepHandler,
)
from core.ceremony_engine.infrastructure.adapters.step_handlers.deliberation_step_handler import (
    DeliberationStepHandler,
)
from core.ceremony_engine.infrastructure.adapters.step_handlers.human_gate_step_handler import (
    HumanGateStepHandler,
)
from core.ceremony_engine.infrastructure.adapters.step_handlers.publish_step_handler import (
    PublishStepHandler,
)
from core.ceremony_engine.infrastructure.adapters.step_handlers.task_extraction_step_handler import (
    TaskExtractionStepHandler,
)


class StepHandlerRegistry(StepHandlerPort):
    """Registry that routes step execution to appropriate handlers.

    Implements StepHandlerPort by:
    - Routing steps to handlers based on step.handler type
    - Providing plug-and-play handler registration
    - Handling unknown handler types (fail-fast)

    Following Hexagonal Architecture:
    - This is an ADAPTER (infrastructure layer)
    - Implements PORT (StepHandlerPort from application layer)
    - Application depends on PORT, not this adapter
    """

    def __init__(
        self,
        deliberation_use_case: SubmitDeliberationUseCase,
        task_extraction_use_case: SubmitTaskExtractionUseCase,
        messaging_port: MessagingPort,
        idempotency_port: IdempotencyPort,
    ) -> None:
        """Initialize registry with default handlers."""
        if not deliberation_use_case:
            raise ValueError("deliberation_use_case is required (fail-fast)")
        if not task_extraction_use_case:
            raise ValueError("task_extraction_use_case is required (fail-fast)")
        if not messaging_port:
            raise ValueError("messaging_port is required (fail-fast)")
        if not idempotency_port:
            raise ValueError("idempotency_port is required (fail-fast)")
        self._handlers: dict[StepHandlerType, Any] = {
            StepHandlerType.DELIBERATION_STEP: DeliberationStepHandler(
                deliberation_use_case
            ),
            StepHandlerType.TASK_EXTRACTION_STEP: TaskExtractionStepHandler(
                task_extraction_use_case
            ),
            StepHandlerType.AGGREGATION_STEP: AggregationStepHandler(),
            StepHandlerType.HUMAN_GATE_STEP: HumanGateStepHandler(),
            StepHandlerType.PUBLISH_STEP: PublishStepHandler(
                messaging_port, idempotency_port
            ),
        }

    async def execute_step(
        self,
        step: Step,
        context: ExecutionContext,
    ) -> StepResult:
        """Execute a step using the appropriate handler.

        Args:
            step: Step to execute (contains handler type and config)
            context: Execution context (inputs, instance state, etc.)

        Returns:
            StepResult with execution status and output

        Raises:
            ValueError: If step handler type is not supported
            Exception: If step execution fails
        """
        handler = self._handlers.get(step.handler)
        if not handler:
            raise ValueError(
                f"Step handler type '{step.handler.value}' is not supported. "
                f"Available handlers: {[h.value for h in self._handlers.keys()]}"
            )

        return await handler.execute(step, context)
