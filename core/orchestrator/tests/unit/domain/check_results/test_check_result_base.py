import math
from dataclasses import dataclass

from core.orchestrator.domain.check_results.check_result import CheckResult


@dataclass(frozen=True)
class ConcreteCheckResult(CheckResult):
    issues: list[str]

    def get_issues(self) -> list[str]:
        return self.issues

    def get_score(self) -> float:
        return 1.0 if self.ok and not self.issues else 0.0

    def _get_specific_data(self) -> dict[str, object]:
        return {"issues": self.issues}


class TestCheckResultBase:
    def test_to_dict_includes_ok_and_specific_data(self) -> None:
        result = ConcreteCheckResult(ok=False, issues=["x", "y"])  # type: ignore[call-arg]

        as_dict = result.to_dict()

        assert as_dict["ok"] is False
        assert as_dict["issues"] == ["x", "y"]

    def test_get_issues_and_score_contract(self) -> None:
        ok_result = ConcreteCheckResult(ok=True, issues=[])  # type: ignore[call-arg]
        bad_result = ConcreteCheckResult(ok=True, issues=["x"])  # type: ignore[call-arg]

        assert ok_result.get_issues() == []
        assert math.isclose(ok_result.get_score(), 1.0)

        assert bad_result.get_issues() == ["x"]
        assert math.isclose(bad_result.get_score(), 0.0)
