"""Test operation execution result domain entity."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TestExecutionResult:
    """Domain entity representing the result of a test operation."""

    success: bool
    content: str | None
    error: str | None = None
    exit_code: int | None = None
    metadata: dict[str, Any] | None = None

