"""Base step handler with common functionality.

Following Hexagonal Architecture:
- Base class for all step handlers
- Provides common validation and error handling
- Handlers are infrastructure adapters
"""

from typing import Any

from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.step_result import StepResult
from core.ceremony_engine.domain.value_objects.step_status import StepStatus


class BaseStepHandler:
    """Base class for step handlers with common functionality.

    Provides:
    - Common validation methods
    - Error handling patterns
    - Helper methods for creating StepResult

    Following Hexagonal Architecture:
    - This is infrastructure (adapters)
    - Handles concrete execution logic
    - Returns domain value objects (StepResult)
    """

    async def execute(
        self,
        step: Step,
        context: ExecutionContext,
    ) -> StepResult:
        """Execute a step (to be implemented by subclasses).

        Args:
            step: Step to execute
            context: Execution context

        Returns:
            StepResult with execution status and output

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement execute()")

    def _validate_config(
        self,
        step: Step,
        required_keys: list[str],
    ) -> None:
        """Validate step config has required keys.

        Args:
            step: Step to validate
            required_keys: List of required config keys

        Raises:
            ValueError: If required keys are missing
        """
        missing_keys = [key for key in required_keys if key not in step.config]
        if missing_keys:
            raise ValueError(
                f"Step '{step.id.value}' config missing required keys: {missing_keys}"
            )

    def _create_success_result(
        self,
        output: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> StepResult:
        """Create a successful StepResult.

        Args:
            output: Step output data
            metadata: Optional metadata

        Returns:
            StepResult with COMPLETED status
        """
        return StepResult(
            status=StepStatus.COMPLETED,
            output=output,
            metadata=metadata,
        )

    def _create_failure_result(
        self,
        error_message: str,
        metadata: dict[str, Any] | None = None,
    ) -> StepResult:
        """Create a failed StepResult.

        Args:
            error_message: Error message
            metadata: Optional metadata

        Returns:
            StepResult with FAILED status
        """
        return StepResult(
            status=StepStatus.FAILED,
            output={},
            error_message=error_message,
            metadata=metadata,
        )
