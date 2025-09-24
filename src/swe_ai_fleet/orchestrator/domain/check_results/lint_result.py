"""Lint check result domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .result import CheckResult


@dataclass(frozen=True)
class LintCheckResult(CheckResult):
    """Result of a linting check (e.g., kubectl lint)."""
    
    issues: list[str]
    
    def get_issues(self) -> list[str]:
        """Get the list of linting issues."""
        return self.issues
    
    def get_score(self) -> float:
        """Calculate linting score: 1.0 if no issues, 0.0 otherwise."""
        return 1.0 if self.ok and not self.issues else 0.0
    
    def _get_specific_data(self) -> dict[str, Any]:
        """Get lint-specific data."""
        return {"issues": self.issues}
    
    @classmethod
    def success(cls) -> LintCheckResult:
        """Create a successful lint check result."""
        return cls(ok=True, issues=[])
    
    @classmethod
    def failure(cls, issues: list[str]) -> LintCheckResult:
        """Create a failed lint check result."""
        return cls(ok=False, issues=issues)
