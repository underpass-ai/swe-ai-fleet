"""Application service for executing individual task steps."""

from __future__ import annotations

import logging

from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
from core.agents_and_tools.agents.domain.entities import ExecutionStep
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort

logger = logging.getLogger(__name__)


class StepExecutionApplicationService:
    """
    Application service for executing individual task steps with RBAC enforcement.

    This service coordinates step execution by delegating to the tool execution
    port and handling errors gracefully. It enforces RBAC by validating tool
    access before execution.

    Following DDD principles:
    - Service coordinates infrastructure concerns (tool execution)
    - Enforces RBAC at application layer
    - Stateless
    - Reusable across different planning strategies
    """

    def __init__(self, tool_execution_port: ToolExecutionPort, allowed_tools: frozenset[str]):
        """
        Initialize step execution service with RBAC enforcement.

        Args:
            tool_execution_port: Port for executing tool operations (required)
            allowed_tools: Set of tool names allowed for this agent's role (required for RBAC)
        """
        if not tool_execution_port:
            raise ValueError("tool_execution_port is required (fail-fast)")
        if not allowed_tools:
            raise ValueError("allowed_tools is required for RBAC enforcement (fail-fast)")

        self.tool_execution_port = tool_execution_port
        self.allowed_tools = allowed_tools

    async def execute(
        self,
        step: ExecutionStep,
        enable_write: bool = True,
    ) -> StepExecutionDTO:
        """
        Execute a single task step with RBAC enforcement.

        Args:
            step: The execution step to execute
            enable_write: Whether write operations are allowed

        Returns:
            StepExecutionDTO with success status, result, and error (if any)
        """
        tool_name = step.tool
        operation = step.operation
        params = step.params or {}

        # 🔒 RBAC ENFORCEMENT: Validate tool access BEFORE execution (fail-fast)
        if tool_name not in self.allowed_tools:
            error_msg = (
                f"RBAC Violation: Tool '{tool_name}' not allowed for this role. "
                f"Allowed tools: {sorted(self.allowed_tools)}"
            )
            logger.error(error_msg)
            return StepExecutionDTO(success=False, result=None, error=error_msg)

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

