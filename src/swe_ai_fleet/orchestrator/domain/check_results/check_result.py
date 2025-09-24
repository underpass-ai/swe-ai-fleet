"""Base check result abstract class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CheckResult(ABC):
    """Abstract base class for all check results.
    
    Represents the outcome of a validation check with a common interface
    for scoring and status evaluation.
    """
    
    ok: bool
    
    @abstractmethod
    def get_issues(self) -> list[str]:
        """Get a list of issues found during the check."""
        pass
    
    @abstractmethod
    def get_score(self) -> float:
        """Calculate the score for this check result.
        
        Returns:
            Score between 0.0 and 1.0, where 1.0 is perfect
        """
        pass
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the check result to a dictionary format."""
        return {
            "ok": self.ok,
            **self._get_specific_data(),
        }
    
    @abstractmethod
    def _get_specific_data(self) -> dict[str, Any]:
        """Get check-specific data for serialization."""
        pass
