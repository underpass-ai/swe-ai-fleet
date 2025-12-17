import math

import pytest

from core.orchestrator.domain.check_results import (
    CheckSuiteResult,
    DryrunCheckResult,
    LintCheckResult,
    PolicyCheckResult,
)


class TestLintCheckResult:
    def test_success_has_no_issues_and_perfect_score(self) -> None:
        result = LintCheckResult.success()

        assert result.ok is True
        assert result.get_issues() == []
        assert math.isclose(result.get_score(), 1.0)

        as_dict = result.to_dict()
        assert as_dict["ok"] is True
        assert as_dict["issues"] == []

    def test_failure_has_issues_and_zero_score(self) -> None:
        issues = ["missing-field", "invalid-syntax"]

        result = LintCheckResult.failure(issues=issues)

        assert result.ok is False
        assert result.get_issues() == issues
        assert math.isclose(result.get_score(), 0.0)

        as_dict = result.to_dict()
        assert as_dict["ok"] is False
        assert as_dict["issues"] == issues


class TestDryrunCheckResult:
    def test_success_has_no_errors_and_perfect_score(self) -> None:
        result = DryrunCheckResult.success()

        assert result.ok is True
        assert result.get_issues() == []
        assert math.isclose(result.get_score(), 1.0)

        as_dict = result.to_dict()
        assert as_dict["ok"] is True
        assert as_dict["errors"] == []

    def test_failure_has_errors_and_zero_score(self) -> None:
        errors = ["cannot-connect", "invalid-manifest"]

        result = DryrunCheckResult.failure(errors=errors)

        assert result.ok is False
        assert result.get_issues() == errors
        assert math.isclose(result.get_score(), 0.0)

        as_dict = result.to_dict()
        assert as_dict["ok"] is False
        assert as_dict["errors"] == errors


class TestPolicyCheckResult:
    def test_success_has_no_violations_and_perfect_score(self) -> None:
        result = PolicyCheckResult.success()

        assert result.ok is True
        assert result.get_issues() == []
        assert math.isclose(result.get_score(), 1.0)

        as_dict = result.to_dict()
        assert as_dict["ok"] is True
        assert as_dict["violations"] == []

    def test_failure_has_violations_and_zero_score(self) -> None:
        violations = ["disallowed-namespace", "missing-label"]

        result = PolicyCheckResult.failure(violations=violations)

        assert result.ok is False
        assert result.get_issues() == violations
        assert math.isclose(result.get_score(), 0.0)

        as_dict = result.to_dict()
        assert as_dict["ok"] is False
        assert as_dict["violations"] == violations


class TestCheckSuiteResult:
    def test_perfect_suite_has_full_score_and_no_issues(self) -> None:
        lint = LintCheckResult.success()
        dryrun = DryrunCheckResult.success()
        policy = PolicyCheckResult.success()

        suite = CheckSuiteResult(lint=lint, dryrun=dryrun, policy=policy)

        assert math.isclose(suite.overall_score, 1.0)
        assert suite.is_perfect is True
        assert suite.has_issues is False
        assert suite.get_all_issues() == {
            "lint": [],
            "dryrun": [],
            "policy": [],
        }

        as_dict = suite.to_dict()
        assert as_dict["lint"] == lint.to_dict()
        assert as_dict["dryrun"] == dryrun.to_dict()
        assert as_dict["policy"] == policy.to_dict()
        assert math.isclose(as_dict["score"], 1.0)

    def test_mixed_suite_scores_and_issues_aggregated(self) -> None:
        lint = LintCheckResult.failure(["lint-issue"])
        dryrun = DryrunCheckResult.success()
        policy = PolicyCheckResult.failure(["policy-violation-1", "policy-violation-2"])

        suite = CheckSuiteResult(lint=lint, dryrun=dryrun, policy=policy)

        expected_scores = [lint.get_score(), dryrun.get_score(), policy.get_score()]
        expected_overall = sum(expected_scores) / len(expected_scores)

        assert suite.has_issues is True
        assert math.isclose(suite.overall_score, expected_overall)
        assert suite.is_perfect is False
        assert suite.get_all_issues() == {
            "lint": ["lint-issue"],
            "dryrun": [],
            "policy": ["policy-violation-1", "policy-violation-2"],
        }

        as_dict = suite.to_dict()
        assert math.isclose(as_dict["score"], expected_overall)


@pytest.mark.parametrize(
    "lint_result,dryrun_result,policy_result,expected_score",
    [
        (LintCheckResult.success(), DryrunCheckResult.success(), PolicyCheckResult.success(), 1.0),
        (LintCheckResult.failure(["x"]), DryrunCheckResult.success(), PolicyCheckResult.success(), 2.0 / 3.0),
        (LintCheckResult.failure(["x"]), DryrunCheckResult.failure(["y"]), PolicyCheckResult.failure(["z"]), 0.0),
    ],
)
def test_check_suite_overall_score_parametrized(
    lint_result: LintCheckResult,
    dryrun_result: DryrunCheckResult,
    policy_result: PolicyCheckResult,
    expected_score: float,
) -> None:
    suite = CheckSuiteResult(lint=lint_result, dryrun=dryrun_result, policy=policy_result)

    assert math.isclose(suite.overall_score, expected_score)
