"""Value objects for check results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PolicyResultVO:
    """Value object representing policy check result.
    
    Attributes:
        passed: Whether the policy check passed
        violations: List of policy violations
        score: Policy compliance score (0.0 to 1.0)
    """
    
    passed: bool
    violations: tuple[str, ...]  # Immutable tuple instead of list
    score: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "violations": list(self.violations),
            "score": self.score,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicyResultVO:
        """Create from dictionary."""
        return cls(
            passed=data["passed"],
            violations=tuple(data.get("violations", [])),
            score=data["score"],
        )


@dataclass(frozen=True)
class LintResultVO:
    """Value object representing lint check result.
    
    Attributes:
        passed: Whether the lint check passed
        errors: Number of lint errors found
        warnings: Number of lint warnings found
        score: Lint quality score (0.0 to 1.0)
    """
    
    passed: bool
    errors: int
    warnings: int
    score: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "score": self.score,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LintResultVO:
        """Create from dictionary."""
        return cls(
            passed=data["passed"],
            errors=data["errors"],
            warnings=data["warnings"],
            score=data["score"],
        )


@dataclass(frozen=True)
class DryRunResultVO:
    """Value object representing dry-run check result.
    
    Attributes:
        passed: Whether the dry-run check passed
        exit_code: Exit code from dry-run execution
        output: Output from dry-run (truncated if too long)
        score: Dry-run quality score (0.0 to 1.0)
    """
    
    passed: bool
    exit_code: int
    output: str
    score: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "exit_code": self.exit_code,
            "output": self.output,
            "score": self.score,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DryRunResultVO:
        """Create from dictionary."""
        return cls(
            passed=data["passed"],
            exit_code=data["exit_code"],
            output=data["output"],
            score=data["score"],
        )


@dataclass(frozen=True)
class CheckSuiteVO:
    """Value object representing a suite of quality checks.
    
    Attributes:
        policy: Policy check result (optional)
        lint: Lint check result (optional)
        dryrun: Dry-run check result (optional)
    """
    
    policy: PolicyResultVO | None = None
    lint: LintResultVO | None = None
    dryrun: DryRunResultVO | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {}
        if self.policy:
            result["policy"] = self.policy.to_dict()
        if self.lint:
            result["lint"] = self.lint.to_dict()
        if self.dryrun:
            result["dryrun"] = self.dryrun.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckSuiteVO:
        """Create from dictionary."""
        policy = None
        if "policy" in data and data["policy"]:
            policy = PolicyResultVO.from_dict(data["policy"])
        
        lint = None
        if "lint" in data and data["lint"]:
            lint = LintResultVO.from_dict(data["lint"])
        
        dryrun = None
        if "dryrun" in data and data["dryrun"]:
            dryrun = DryRunResultVO.from_dict(data["dryrun"])
        
        return cls(policy=policy, lint=lint, dryrun=dryrun)

