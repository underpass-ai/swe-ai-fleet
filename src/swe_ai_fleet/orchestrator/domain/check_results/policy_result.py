"""Policy check result domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .result import CheckResult


@dataclass(frozen=True)
class PolicyCheckResult(CheckResult):
    """Result of a policy check (e.g., OPA policy validation)."""
    
    violations: list[str]
    
    def get_issues(self) -> list[str]:
        """Get the list of policy violations."""
        return self.violations
    
    def get_score(self) -> float:
        """Calculate policy score: 1.0 if no violations, 0.0 otherwise."""
        return 1.0 if self.ok and not self.violations else 0.0
    
    def _get_specific_data(self) -> dict[str, Any]:
        """Get policy-specific data."""
        return {"violations": self.violations}
    
    @classmethod
    def success(cls) -> PolicyCheckResult:
        """Create a successful policy check result."""
        return cls(ok=True, violations=[])
    
    @classmethod
    def failure(cls, violations: list[str]) -> PolicyCheckResult:
        """Create a failed policy check result."""
        return cls(ok=False, violations=violations)
