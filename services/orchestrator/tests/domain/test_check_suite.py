"""Tests for CheckSuite entity."""

import pytest

from services.orchestrator.domain.entities import CheckSuite, DryRunResult, LintResult, PolicyResult


class TestCheckSuite:
    """Test suite for CheckSuite entity."""
    
    def test_all_passed_true(self):
        """Test all_passed returns True when all checks pass."""
        suite = CheckSuite(
            policy=PolicyResult(passed=True, violations=[], score=1.0),
            lint=LintResult(passed=True, errors=0, warnings=0, score=1.0),
            dryrun=DryRunResult(passed=True, exit_code=0, output="", score=1.0)
        )
        
        assert suite.all_passed() is True
    
    def test_all_passed_false_policy(self):
        """Test all_passed returns False when policy fails."""
        suite = CheckSuite(
            policy=PolicyResult(passed=False, violations=["violation"], score=0.0),
            lint=LintResult(passed=True, errors=0, warnings=0, score=1.0),
            dryrun=DryRunResult(passed=True, exit_code=0, output="", score=1.0)
        )
        
        assert suite.all_passed() is False
    
    def test_all_passed_false_linting(self):
        """Test all_passed returns False when linting fails."""
        suite = CheckSuite(
            policy=PolicyResult(passed=True, violations=[], score=1.0),
            lint=LintResult(passed=False, errors=5, warnings=0, score=0.0),
            dryrun=DryRunResult(passed=True, exit_code=0, output="", score=1.0)
        )
        
        assert suite.all_passed() is False
    
    def test_all_passed_false_dry_run(self):
        """Test all_passed returns False when dry run fails."""
        suite = CheckSuite(
            policy=PolicyResult(passed=True, violations=[], score=1.0),
            lint=LintResult(passed=True, errors=0, warnings=0, score=1.0),
            dryrun=DryRunResult(passed=False, exit_code=1, output="error", score=0.0)
        )
        
        assert suite.all_passed() is False
    
    def test_overall_score_all_passed(self):
        """Test overall_score returns 1.0 when all checks pass."""
        suite = CheckSuite(
            policy=PolicyResult(passed=True, violations=[], score=1.0),
            lint=LintResult(passed=True, errors=0, warnings=0, score=1.0),
            dryrun=DryRunResult(passed=True, exit_code=0, output="", score=1.0)
        )
        
        assert suite.overall_score() == pytest.approx(1.0)
    
    def test_overall_score_one_failed(self):
        """Test overall_score when one check fails."""
        suite = CheckSuite(
            policy=PolicyResult(passed=False, violations=["v1"], score=0.0),
            lint=LintResult(passed=True, errors=0, warnings=0, score=1.0),
            dryrun=DryRunResult(passed=True, exit_code=0, output="", score=1.0)
        )
        
        score = suite.overall_score()
        assert 0.0 < score < 1.0
        assert score == pytest.approx(2/3, 0.01)
    
    def test_overall_score_all_failed(self):
        """Test overall_score returns 0.0 when all checks fail."""
        suite = CheckSuite(
            policy=PolicyResult(passed=False, violations=["v1"], score=0.0),
            lint=LintResult(passed=False, errors=5, warnings=0, score=0.0),
            dryrun=DryRunResult(passed=False, exit_code=1, output="e1", score=0.0)
        )
        
        assert suite.overall_score() == pytest.approx(0.0)
    
    def test_from_dict(self):
        """Test creating CheckSuite from dict."""
        data = {
            "policy": {"ok": True, "violations": []},
            "lint": {"ok": True, "issues": []},
            "dryrun": {"ok": False, "errors": ["syntax error"]}
        }
        
        suite = CheckSuite.from_dict(data)
        
        assert suite.policy.passed is True
        assert suite.lint.passed is True
        assert suite.dryrun.passed is False
        assert "syntax error" in suite.dryrun.output

