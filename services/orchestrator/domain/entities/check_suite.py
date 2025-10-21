"""Check Suite entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PolicyResult:
    """Entity representing policy check result."""
    
    passed: bool
    violations: list[str]
    score: float
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicyResult:
        """Create from dictionary.
        
        Tell, Don't Ask: Object knows how to deserialize itself.
        """
        return cls(
            passed=data.get("ok", True),
            violations=list(data.get("violations", [])),
            score=1.0 if data.get("ok", True) else 0.0
        )


@dataclass
class LintResult:
    """Entity representing lint check result."""
    
    passed: bool
    errors: int
    warnings: int
    score: float
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LintResult:
        """Create from dictionary.
        
        Tell, Don't Ask: Object knows how to deserialize itself.
        """
        issues = data.get("issues", [])
        return cls(
            passed=data.get("ok", True),
            errors=len(issues),
            warnings=0,
            score=1.0 if data.get("ok", True) else 0.0
        )


@dataclass
class DryRunResult:
    """Entity representing dry-run check result."""
    
    passed: bool
    exit_code: int
    output: str
    score: float
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DryRunResult:
        """Create from dictionary.
        
        Tell, Don't Ask: Object knows how to deserialize itself.
        """
        errors = data.get("errors", [])
        return cls(
            passed=data.get("ok", True),
            exit_code=0 if data.get("ok", True) else 1,
            output=errors[0] if errors else "",
            score=1.0 if data.get("ok", True) else 0.0
        )


@dataclass
class CheckSuite:
    """Entity representing a suite of quality checks.
    
    Applies "Tell, Don't Ask" principle by encapsulating logic
    for creating and converting check results.
    
    Attributes:
        policy: Policy check result (optional)
        lint: Lint check result (optional)
        dryrun: Dry-run check result (optional)
    """
    
    policy: PolicyResult | None = None
    lint: LintResult | None = None
    dryrun: DryRunResult | None = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckSuite:
        """Create CheckSuite from dictionary.
        
        Tell, Don't Ask: CheckSuite knows how to deserialize itself.
        
        Args:
            data: Dictionary with check results
            
        Returns:
            CheckSuite entity
        """
        policy = None
        if "policy" in data and data["policy"]:
            policy = PolicyResult.from_dict(data["policy"])
        
        lint = None
        if "lint" in data and data["lint"]:
            lint = LintResult.from_dict(data["lint"])
        
        dryrun = None
        if "dryrun" in data and data["dryrun"]:
            dryrun = DryRunResult.from_dict(data["dryrun"])
        
        return cls(policy=policy, lint=lint, dryrun=dryrun)
    
    def all_passed(self) -> bool:
        """Check if all checks passed.
        
        Tell, Don't Ask: Don't ask for each check's status,
        tell the suite to check if all passed.
        
        Returns:
            True if all checks passed, False otherwise
        """
        if self.policy and not self.policy.passed:
            return False
        if self.lint and not self.lint.passed:
            return False
        if self.dryrun and not self.dryrun.passed:
            return False
        return True
    
    def overall_score(self) -> float:
        """Calculate overall quality score.
        
        Tell, Don't Ask: Don't ask for individual scores,
        tell the suite to calculate overall score.
        
        Returns:
            Average score across all checks
        """
        scores = []
        if self.policy:
            scores.append(self.policy.score)
        if self.lint:
            scores.append(self.lint.score)
        if self.dryrun:
            scores.append(self.dryrun.score)
        
        return sum(scores) / len(scores) if scores else 1.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {}
        if self.policy:
            result["policy"] = {
                "passed": self.policy.passed,
                "violations": self.policy.violations,
                "score": self.policy.score,
            }
        if self.lint:
            result["lint"] = {
                "passed": self.lint.passed,
                "errors": self.lint.errors,
                "warnings": self.lint.warnings,
                "score": self.lint.score,
            }
        if self.dryrun:
            result["dryrun"] = {
                "passed": self.dryrun.passed,
                "exit_code": self.dryrun.exit_code,
                "output": self.dryrun.output,
                "score": self.dryrun.score,
            }
        return result

