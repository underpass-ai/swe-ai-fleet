"""Application service for tool result summarization."""

from __future__ import annotations

from typing import Any

from core.agents_and_tools.agents.domain.entities import ExecutionStep
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort


class ResultSummarizationApplicationService:
    """
    Application service for summarizing tool operation results.

    This service coordinates result summarization by delegating to
    tool-specific summarization methods.

    Following DDD principles:
    - Service operates on domain entities (ExecutionStep)
    - Coordinates infrastructure concerns (tool access)
    - Stateless
    """

    def __init__(self, tool_execution_port: ToolExecutionPort):
        """
        Initialize summarization service.

        Args:
            tool_execution_port: Port for accessing tools (required)
        """
        if not tool_execution_port:
            raise ValueError("tool_execution_port is required (fail-fast)")

        self.tool_execution_port = tool_execution_port

    def summarize(
        self,
        step: ExecutionStep,
        tool_result: Any,
        params: dict[str, Any] | None = None,
    ) -> str:
        """
        Summarize tool operation result.

        Args:
            step: The execution step that was executed
            tool_result: The result entity from the tool
            params: Operation parameters (optional, uses step.params if None)

        Returns:
            Human-readable summary string
        """
        # Get the tool instance
        tool = self.tool_execution_port.get_tool_by_name(step.tool)
        if not tool:
            return "Operation completed"

        # Use provided params or get from step
        operation_params = params if params is not None else (step.params or {})

        # Delegate to tool's summarize_result method
        return tool.summarize_result(step.operation, tool_result, operation_params)

