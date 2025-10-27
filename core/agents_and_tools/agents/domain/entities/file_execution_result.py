"""File operation execution result domain entity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FileExecutionResult:
    """Domain entity representing the result of a file operation."""

    success: bool
    content: str | None
    error: str | None = None

