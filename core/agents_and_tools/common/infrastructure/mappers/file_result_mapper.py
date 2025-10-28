"""Mapper for FileResult to FileExecutionResult."""

from core.agents_and_tools.agents.domain.entities.file_execution_result import FileExecutionResult
from core.agents_and_tools.tools import FileResult


class FileResultMapper:
    """Mapper for FileResult to domain entity."""

    def to_entity(self, result: FileResult) -> FileExecutionResult:
        """Convert FileResult to FileExecutionResult domain entity."""
        return FileExecutionResult(
            success=result.success,
            content=result.content,
            error=result.error,
        )

