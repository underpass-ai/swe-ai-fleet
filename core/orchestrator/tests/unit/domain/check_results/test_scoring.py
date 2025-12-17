import math

from core.orchestrator.domain.check_results import (
    CheckSuiteResult,
    DryrunCheckResult,
    LintCheckResult,
    PolicyCheckResult,
)
from core.orchestrator.domain.check_results.services.scoring import Scoring


class TestScoringPrimitiveChecks:
    def test_kube_lint_returns_success_result(self) -> None:
        scoring = Scoring()

        result = scoring.kube_lint(manifest="apiVersion: v1")

        assert isinstance(result, LintCheckResult)
        assert result.ok is True
        assert result.get_issues() == []

    def test_kube_dryrun_returns_success_result(self) -> None:
        scoring = Scoring()

        result = scoring.kube_dryrun(manifest="apiVersion: v1")

        assert isinstance(result, DryrunCheckResult)
        assert result.ok is True
        assert result.get_issues() == []

    def test_opa_policy_check_returns_success_result(self) -> None:
        scoring = Scoring()

        result = scoring.opa_policy_check(manifest="apiVersion: v1")

        assert isinstance(result, PolicyCheckResult)
        assert result.ok is True
        assert result.get_issues() == []


class TestScoringSuiteAndScore:
    def test_run_check_suite_uses_all_primitive_checks(self, mocker) -> None:
        scoring = Scoring()
        manifest = "apiVersion: v1"

        kube_lint_mock = mocker.patch.object(
            scoring,
            "kube_lint",
            return_value=LintCheckResult.success(),
        )
        kube_dryrun_mock = mocker.patch.object(
            scoring,
            "kube_dryrun",
            return_value=DryrunCheckResult.success(),
        )
        opa_policy_mock = mocker.patch.object(
            scoring,
            "opa_policy_check",
            return_value=PolicyCheckResult.success(),
        )

        suite = scoring.run_check_suite(manifest=manifest)

        kube_lint_mock.assert_called_once_with(manifest)
        kube_dryrun_mock.assert_called_once_with(manifest)
        opa_policy_mock.assert_called_once_with(manifest)

        assert isinstance(suite, CheckSuiteResult)
        assert suite.lint is kube_lint_mock.return_value
        assert suite.dryrun is kube_dryrun_mock.return_value
        assert suite.policy is opa_policy_mock.return_value

    def test_score_checks_delegates_to_check_suite_overall_score(self, mocker) -> None:
        scoring = Scoring()
        check_suite = mocker.create_autospec(CheckSuiteResult, instance=True)
        check_suite.overall_score = 0.75

        score = scoring.score_checks(check_suite=check_suite)

        assert math.isclose(score, 0.75)
