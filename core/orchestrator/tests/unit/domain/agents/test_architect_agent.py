from core.orchestrator.domain.agents.architect_agent import ArchitectAgent


class TestArchitectAgent:
    def test_select_best_with_empty_telemetry_returns_first_proposal(self) -> None:
        agent = ArchitectAgent()
        proposals = ["proposal-1", "proposal-2", "proposal-3"]
        telemetry: list[dict[str, object]] = []

        result = agent.select_best(proposals=proposals, telemetry=telemetry)

        assert result == "proposal-1"

    def test_select_best_with_perfect_scores_returns_first(self) -> None:
        agent = ArchitectAgent()
        proposals = ["proposal-1", "proposal-2"]
        telemetry = [
            {"dryrun": {"ok": True}, "lint": {"ok": True}},
            {"dryrun": {"ok": True}, "lint": {"ok": True}},
        ]

        result = agent.select_best(proposals=proposals, telemetry=telemetry)

        assert result == "proposal-1"

    def test_select_best_selects_highest_scoring_proposal(self) -> None:
        agent = ArchitectAgent()
        proposals = ["proposal-1", "proposal-2", "proposal-3"]
        telemetry = [
            {"dryrun": {"ok": False}, "lint": {"ok": True}},
            {"dryrun": {"ok": True}, "lint": {"ok": True}},
            {"dryrun": {"ok": False}, "lint": {"ok": False}},
        ]

        result = agent.select_best(proposals=proposals, telemetry=telemetry)

        assert result == "proposal-2"

    def test_select_best_handles_missing_telemetry_fields(self) -> None:
        agent = ArchitectAgent()
        proposals = ["proposal-1", "proposal-2"]
        telemetry = [
            {},
            {"dryrun": {"ok": True}, "lint": {"ok": True}},
        ]

        result = agent.select_best(proposals=proposals, telemetry=telemetry)

        assert result == "proposal-2"
