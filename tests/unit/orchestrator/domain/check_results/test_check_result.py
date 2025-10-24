"""Tests for CheckResult abstract base class."""

import pytest
from abc import ABC
from core.orchestrator.domain.check_results.check_result import CheckResult


class ConcreteCheckResult(CheckResult):
    """Concrete implementation of CheckResult for testing."""
    
    def __init__(self, ok: bool, issues: list[str], score: float):
        self._ok = ok
        self._issues = issues
        self._score = score
    
    @property
    def ok(self) -> bool:
        return self._ok
    
    def get_issues(self) -> list[str]:
        return self._issues
    
    def get_score(self) -> float:
        return self._score
    
    def _get_specific_data(self) -> dict[str, any]:
        return {
            "issues": self._issues,
            "score": self._score
        }


class TestCheckResult:
    """Test cases for CheckResult abstract base class."""

    def test_check_result_creation_success(self):
        """Test creating a successful check result."""
        result = ConcreteCheckResult(
            ok=True,
            issues=["Minor formatting issue"],
            score=0.9
        )
        
        assert result.ok is True
        assert result.get_issues() == ["Minor formatting issue"]
        assert result.get_score() == 0.9

    def test_check_result_creation_failure(self):
        """Test creating a failed check result."""
        result = ConcreteCheckResult(
            ok=False,
            issues=["Critical error", "Missing dependency"],
            score=0.2
        )
        
        assert result.ok is False
        assert result.get_issues() == ["Critical error", "Missing dependency"]
        assert result.get_score() == 0.2

    def test_check_result_to_dict(self):
        """Test converting check result to dictionary."""
        result = ConcreteCheckResult(
            ok=True,
            issues=["Warning: deprecated API"],
            score=0.8
        )
        
        result_dict = result.to_dict()
        
        expected = {
            "ok": True,
            "issues": ["Warning: deprecated API"],
            "score": 0.8
        }
        
        assert result_dict == expected

    def test_check_result_empty_issues(self):
        """Test check result with no issues."""
        result = ConcreteCheckResult(
            ok=True,
            issues=[],
            score=1.0
        )
        
        assert result.ok is True
        assert result.get_issues() == []
        assert result.get_score() == 1.0

    def test_check_result_score_boundaries(self):
        """Test check result with boundary score values."""
        # Perfect score
        perfect_result = ConcreteCheckResult(
            ok=True,
            issues=[],
            score=1.0
        )
        assert perfect_result.get_score() == 1.0
        
        # Worst score
        worst_result = ConcreteCheckResult(
            ok=False,
            issues=["Multiple critical errors"],
            score=0.0
        )
        assert worst_result.get_score() == 0.0

    def test_check_result_cannot_instantiate_abstract_class(self):
        """Test that CheckResult abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CheckResult(ok=True)  # type: ignore
