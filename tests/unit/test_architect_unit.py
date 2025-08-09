from edgecrew.orchestrator.architect import ArchitectAgent, ArchitectSelector


def test_architect_selector_picks_highest_scored_candidate():
    selector = ArchitectSelector(architect=ArchitectAgent())
    ranked = [
        {
            "proposal": {"content": "P0"},
            "checks": {"lint": {"ok": False}, "dryrun": {"ok": True}, "policy": {"ok": True}},
            "score": 1.0,
        },
        {
            "proposal": {"content": "P1"},
            "checks": {"lint": {"ok": True}, "dryrun": {"ok": True}, "policy": {"ok": True}},
            "score": 3.0,
        },
    ]
    result = selector.choose(ranked, rubric={"k": 2})
    assert result["winner"] == "P1"
    assert len(result["candidates"]) == 2


def test_architect_selector_handles_empty_rubric():
    selector = ArchitectSelector(architect=ArchitectAgent())
    ranked = [
        {
            "proposal": {"content": "X"},
            "checks": {"lint": {"ok": True}, "dryrun": {"ok": True}, "policy": {"ok": True}},
            "score": 3.0,
        },
    ]
    result = selector.choose(ranked, rubric={})
    assert result["winner"] == "X"
