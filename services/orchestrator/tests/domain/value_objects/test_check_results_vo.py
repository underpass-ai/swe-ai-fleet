from __future__ import annotations

from typing import Any

import pytest

from services.orchestrator.domain.value_objects.check_results import (
    CheckSuiteVO,
    DryRunResultVO,
    LintResultVO,
    PolicyResultVO,
)


class TestPolicyResultVO:
    def test_to_dict_and_from_dict_round_trip(self) -> None:
        vo = PolicyResultVO(passed=True, violations=("v1", "v2"), score=0.75)

        as_dict = vo.to_dict()

        assert as_dict == {
            "passed": True,
            "violations": ["v1", "v2"],
            "score": 0.75,
        }

        restored = PolicyResultVO.from_dict(as_dict)

        assert restored == vo
        assert isinstance(restored.violations, tuple)

    def test_from_dict_uses_empty_tuple_when_violations_missing(self) -> None:
        data: dict[str, Any] = {"passed": False, "score": 0.0}

        vo = PolicyResultVO.from_dict(data)

        assert vo.passed is False
        assert vo.score == pytest.approx(0.0)
        assert vo.violations == ()
        assert isinstance(vo.violations, tuple)


class TestLintResultVO:
    def test_to_dict_and_from_dict_round_trip(self) -> None:
        vo = LintResultVO(passed=False, errors=3, warnings=1, score=0.4)

        as_dict = vo.to_dict()

        assert as_dict == {
            "passed": False,
            "errors": 3,
            "warnings": 1,
            "score": 0.4,
        }

        restored = LintResultVO.from_dict(as_dict)

        assert restored == vo


class TestDryRunResultVO:
    def test_to_dict_and_from_dict_round_trip(self) -> None:
        vo = DryRunResultVO(passed=True, exit_code=0, output="ok", score=1.0)

        as_dict = vo.to_dict()

        assert as_dict == {
            "passed": True,
            "exit_code": 0,
            "output": "ok",
            "score": 1.0,
        }

        restored = DryRunResultVO.from_dict(as_dict)

        assert restored == vo


class TestCheckSuiteVO:
    def test_to_dict_includes_only_non_none_checks(self) -> None:
        policy = PolicyResultVO(passed=True, violations=(), score=1.0)
        lint = LintResultVO(passed=True, errors=0, warnings=0, score=0.9)
        dryrun = DryRunResultVO(passed=False, exit_code=1, output="err", score=0.0)

        suite_all = CheckSuiteVO(policy=policy, lint=lint, dryrun=dryrun)
        dict_all = suite_all.to_dict()

        assert dict_all["policy"] == policy.to_dict()
        assert dict_all["lint"] == lint.to_dict()
        assert dict_all["dryrun"] == dryrun.to_dict()

        suite_partial = CheckSuiteVO(policy=policy, lint=None, dryrun=None)
        dict_partial = suite_partial.to_dict()

        assert dict_partial == {"policy": policy.to_dict()}

        suite_empty = CheckSuiteVO()
        assert suite_empty.to_dict() == {}

    def test_from_dict_creates_nested_value_objects(self) -> None:
        data = {
            "policy": {"passed": True, "violations": ["v1"], "score": 0.9},
            "lint": {"passed": False, "errors": 1, "warnings": 2, "score": 0.5},
            "dryrun": {"passed": True, "exit_code": 0, "output": "", "score": 1.0},
        }

        suite = CheckSuiteVO.from_dict(data)

        assert isinstance(suite.policy, PolicyResultVO)
        assert isinstance(suite.lint, LintResultVO)
        assert isinstance(suite.dryrun, DryRunResultVO)
        assert suite.policy.violations == ("v1",)

    def test_from_dict_omits_missing_or_empty_sections(self) -> None:
        data_missing: dict[str, Any] = {}

        suite_missing = CheckSuiteVO.from_dict(data_missing)

        assert suite_missing.policy is None
        assert suite_missing.lint is None
        assert suite_missing.dryrun is None

        data_empty_sections: dict[str, Any] = {"policy": {}, "lint": None, "dryrun": {}}

        suite_empty_sections = CheckSuiteVO.from_dict(data_empty_sections)

        assert suite_empty_sections.policy is None
        assert suite_empty_sections.lint is None
        assert suite_empty_sections.dryrun is None
