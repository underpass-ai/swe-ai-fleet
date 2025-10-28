"""Use case for summarizing tool operation results."""

from typing import Any

from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort


class SummarizeResultUseCase:
    """
    Use case for summarizing tool operation results.

    Delegates to tool's own summarize_result method.
    """

    def __init__(self, tool_execution_port: ToolExecutionPort):
        """
        Initialize the use case.

        Args:
            tool_execution_port: Port for tool execution
        """
        self.tool_execution_port = tool_execution_port

    def execute(self, tool_name: str, operation: str, tool_result: Any, params: dict[str, Any]) -> str:
        """
        Summarize tool operation result.

        Args:
            tool_name: Name of the tool
            operation: The operation that was executed
            tool_result: The result from the tool
            params: The operation parameters

        Returns:
            Human-readable summary
        """
        # Get tool instance from port
        tool = self.tool_execution_port.get_tool_by_name(tool_name)
        if not tool:
            return "Operation completed"

        # Delegate to tool's summarize_result method
        return tool.summarize_result(operation, tool_result, params)

