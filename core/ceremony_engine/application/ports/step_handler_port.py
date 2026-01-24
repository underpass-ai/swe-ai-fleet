"""StepHandlerPort: Port for executing step handlers.

Following Hexagonal Architecture:
- This is a PORT (interface) in the application layer
- Infrastructure adapters implement this port
- Application services depend on this port, not concrete adapters
"""

from typing import Protocol

from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.step_result import StepResult


class StepHandlerPort(Protocol):
    """Port for executing step handlers.

    Provides step execution capabilities:
    - Execute steps via appropriate handler (deliberation, task_extraction, etc.)
    - Handlers are plug-and-play (infrastructure adapters)
    - Returns StepResult with status and output

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (StepHandlerRegistry, etc.)
    - Application depends on PORT, not concrete implementation
    """

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
        ...
