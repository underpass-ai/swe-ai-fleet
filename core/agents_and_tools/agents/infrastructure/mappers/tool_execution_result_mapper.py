"""
Mapper for converting infrastructure tool results to domain entities.

This mapper converts infrastructure-specific Result types (FileResult, GitResult, etc.)
to the domain entity ToolExecutionResult, maintaining separation between infrastructure
and domain layers.
"""

from typing import Any

from core.agents_and_tools.agents.domain.entities.tool_execution_result import ToolExecutionResult
from core.agents_and_tools.tools import (
    DbResult,
    DockerResult,
    FileResult,
    GitResult,
    HttpResult,
    TestResult,
)


class ToolExecutionResultMapper:
    """Mapper for converting tool results to domain entities."""

    def infrastructure_to_entity(
        self, result: Any, tool_name: str, operation: str
    ) -> ToolExecutionResult:
        """
        Convert infrastructure Result to domain entity (NO REFLECTION).

        Args:
            result: Infrastructure result object (FileResult, GitResult, etc.)
            tool_name: Name of the tool
            operation: Name of the operation

        Returns:
            ToolExecutionResult domain entity
        """
        # Extract common attributes from result types
        content = self._extract_content(result)
        error = self._extract_error(result)
        metadata = self._extract_metadata(result)

        return ToolExecutionResult(
            success=result.success,
            tool_name=tool_name,
            operation=operation,
            content=content,
            error=error,
            metadata=metadata,
        )

    def _extract_content(self, result: Any) -> str | None:
        """Extract content from result (NO REFLECTION)."""
        if isinstance(result, FileResult):
            return result.content
        elif isinstance(result, GitResult):
            return result.stdout
        elif isinstance(result, TestResult):
            return result.stdout
        elif isinstance(result, HttpResult):
            return str(result.body) if result.body else None
        elif isinstance(result, DbResult):
            return str(result.data) if result.data else None
        elif isinstance(result, DockerResult):
            return result.stdout

        return None

    def _extract_error(self, result: Any) -> str | None:
        """Extract error from result (NO REFLECTION)."""
        if isinstance(result, FileResult):
            return result.error
        elif isinstance(result, GitResult):
            return result.stderr
        elif isinstance(result, TestResult):
            return result.stderr
        elif isinstance(result, HttpResult):
            return result.error
        elif isinstance(result, DbResult):
            return result.error
        elif isinstance(result, DockerResult):
            return result.stderr

        return None

    def _extract_metadata(self, result: Any) -> dict[str, Any]:
        """Extract metadata from result (NO REFLECTION)."""
        metadata = {}

        # Helper to safely update metadata dict
        def _update_metadata_key(key: str):
            if hasattr(result, key):
                metadata[key] = getattr(result, key)

        # Helper to update dict metadata
        def _update_metadata_dict():
            if hasattr(result, "metadata") and result.metadata:
                metadata.update(result.metadata)

        # Extract metadata based on type
        if isinstance(result, FileResult):
            _update_metadata_dict()
        elif isinstance(result, GitResult):
            _update_metadata_key("operation")
            _update_metadata_key("exit_code")
            _update_metadata_dict()
        elif isinstance(result, TestResult):
            _update_metadata_key("exit_code")
            _update_metadata_dict()
        elif isinstance(result, HttpResult):
            _update_metadata_key("status_code")
            _update_metadata_dict()
        elif isinstance(result, DbResult):
            _update_metadata_dict()
        elif isinstance(result, DockerResult):
            _update_metadata_key("exit_code")
            _update_metadata_dict()

        return metadata if metadata else None

