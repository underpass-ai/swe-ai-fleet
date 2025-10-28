"""Database operation execution result domain entity."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DbExecutionResult:
    """Domain entity representing the result of a database operation."""

    success: bool
    content: str | None
    error: str | None = None
    metadata: dict[str, Any] | None = None

