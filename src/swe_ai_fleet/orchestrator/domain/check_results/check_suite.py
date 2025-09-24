"""Check suite result domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .dryrun_result import DryrunCheckResult
from .lint_result import LintCheckResult
from .policy_result import PolicyCheckResult


@dataclass(frozen=True)
class CheckSuiteResult:
    """Aggregated result of multiple check types.
    
    Represents the combined outcome of lint, dry-run, and policy checks
    with overall scoring and status evaluation.
    """
    
    lint: LintCheckResult
    dryrun: DryrunCheckResult
    policy: PolicyCheckResult
    
    @property
    def overall_score(self) -> float:
        """Calculate the overall score across all checks.
        
        Returns:
            Average score of all checks (0.0 to 1.0)
        """
        scores = [
            self.lint.get_score(),
            self.dryrun.get_score(),
            self.policy.get_score(),
        ]
        return sum(scores) / len(scores)
    
    @property
    def is_perfect(self) -> bool:
        """Check if all checks passed perfectly."""
        return self.overall_score == 1.0
    
    @property
    def has_issues(self) -> bool:
        """Check if any check found issues."""
        return (
            bool(self.lint.get_issues()) or
            bool(self.dryrun.get_issues()) or
            bool(self.policy.get_issues())
        )
    
    def get_all_issues(self) -> dict[str, list[str]]:
        """Get all issues organized by check type.
        
        Returns:
            Dictionary mapping check types to their issues
        """
        return {
            "lint": self.lint.get_issues(),
            "dryrun": self.dryrun.get_issues(),
            "policy": self.policy.get_issues(),
        }
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the check suite to dictionary format."""
        return {
            "lint": self.lint.to_dict(),
            "dryrun": self.dryrun.to_dict(),
            "policy": self.policy.to_dict(),
            "score": self.overall_score,
        }
