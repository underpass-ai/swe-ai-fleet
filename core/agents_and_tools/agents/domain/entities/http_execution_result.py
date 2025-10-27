"""HTTP operation execution result domain entity."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HttpExecutionResult:
    """Domain entity representing the result of an HTTP operation."""

    success: bool
    content: str | None
    error: str | None = None
    status_code: int | None = None
    metadata: dict[str, Any] | None = None

