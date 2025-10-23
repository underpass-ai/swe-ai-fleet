"""Dry-run check result domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .result import CheckResult


@dataclass(frozen=True)
class DryrunCheckResult(CheckResult):
    """Result of a dry-run check (e.g., kubectl apply --dry-run)."""
    
    errors: list[str]
    
    def get_issues(self) -> list[str]:
        """Get the list of dry-run errors."""
        return self.errors
    
    def get_score(self) -> float:
        """Calculate dry-run score: 1.0 if no errors, 0.0 otherwise."""
        return 1.0 if self.ok and not self.errors else 0.0
    
    def _get_specific_data(self) -> dict[str, Any]:
        """Get dry-run specific data."""
        return {"errors": self.errors}
    
    @classmethod
    def success(cls) -> DryrunCheckResult:
        """Create a successful dry-run check result."""
        return cls(ok=True, errors=[])
    
    @classmethod
    def failure(cls, errors: list[str]) -> DryrunCheckResult:
        """Create a failed dry-run check result."""
        return cls(ok=False, errors=errors)
