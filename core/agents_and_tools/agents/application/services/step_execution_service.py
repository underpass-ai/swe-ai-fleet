"""Application service for executing individual task steps."""

from __future__ import annotations

import logging

from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
from core.agents_and_tools.agents.domain.entities import ExecutionStep
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort

logger = logging.getLogger(__name__)


class StepExecutionApplicationService:
    """
    Application service for executing individual task steps.

    This service coordinates step execution by delegating to the tool execution
    port and handling errors gracefully.

    Following DDD principles:
    - Service coordinates infrastructure concerns (tool execution)
    - Stateless
    - Reusable across different planning strategies
    """

    def __init__(self, tool_execution_port: ToolExecutionPort):
        """
        Initialize step execution service.

        Args:
            tool_execution_port: Port for executing tool operations (required)
        """
        if not tool_execution_port:
            raise ValueError("tool_execution_port is required (fail-fast)")

        self.tool_execution_port = tool_execution_port

    async def execute(
        self,
        step: ExecutionStep,
        enable_write: bool = True,
    ) -> StepExecutionDTO:
        """
        Execute a single task step.

        Args:
            step: The execution step to execute
            enable_write: Whether write operations are allowed

        Returns:
            StepExecutionDTO with success status, result, and error (if any)
        """
        tool_name = step.tool
        operation = step.operation
        params = step.params or {}

        try:
            # Delegate to tool execution port
            result = self.tool_execution_port.execute_operation(
                tool_name=tool_name,
                operation=operation,
                params=params,
                enable_write=enable_write,
            )

            # Normalize error message
            error_msg = result.error if not result.success else None
            if not result.success and not error_msg:
                error_msg = "Unknown error"

            return StepExecutionDTO(
                success=result.success,
                result=result,
                error=error_msg,
            )
        except ValueError as e:
            # Handle validation errors
            return StepExecutionDTO(success=False, result=None, error=str(e))
        except Exception as e:
            # Handle unexpected errors
            logger.exception(f"Step execution failed: {e}")
            return StepExecutionDTO(success=False, result=None, error=str(e))

