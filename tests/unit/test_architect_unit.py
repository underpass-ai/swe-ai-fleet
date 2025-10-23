from core.orchestrator.domain.agents.architect_agent import ArchitectAgent
from core.orchestrator.domain.agents.services import ArchitectSelectorService
from core.orchestrator.domain.check_results import (
    CheckSuiteResult,
    DryrunCheckResult,
    LintCheckResult,
    PolicyCheckResult,
)
from core.orchestrator.domain.deliberation_result import DeliberationResult, Proposal
from core.orchestrator.domain.tasks.task_constraints import TaskConstraints


def test_architect_selector_picks_highest_scored_candidate():
    selector = ArchitectSelectorService(architect=ArchitectAgent())
    
    # Create DeliberationResult objects
    proposal0 = Proposal(author=None, content="P0")
    proposal1 = Proposal(author=None, content="P1")
    
    checks0 = CheckSuiteResult(
        lint=LintCheckResult(ok=False, issues=[]),
        dryrun=DryrunCheckResult(ok=True, errors=[]),
        policy=PolicyCheckResult(ok=True, violations=[])
    )
    checks1 = CheckSuiteResult(
        lint=LintCheckResult(ok=True, issues=[]),
        dryrun=DryrunCheckResult(ok=True, errors=[]),
        policy=PolicyCheckResult(ok=True, violations=[])
    )
    
    ranked = [
        DeliberationResult(proposal=proposal0, checks=checks0, score=1.0),
        DeliberationResult(proposal=proposal1, checks=checks1, score=3.0),
    ]
    
    constraints = TaskConstraints(rubric={}, architect_rubric={"k": 2})
    result = selector.choose(ranked, constraints)
    # Winner is now the full DeliberationResult object, not just content string
    assert result["winner"].proposal.content == "P1"
    assert result["winner"].score == 3.0
    assert len(result["candidates"]) == 2


def test_architect_selector_handles_empty_rubric():
    selector = ArchitectSelectorService(architect=ArchitectAgent())
    
    proposal = Proposal(author=None, content="X")
    checks = CheckSuiteResult(
        lint=LintCheckResult(ok=True, issues=[]),
        dryrun=DryrunCheckResult(ok=True, errors=[]),
        policy=PolicyCheckResult(ok=True, violations=[])
    )
    
    ranked = [
        DeliberationResult(proposal=proposal, checks=checks, score=3.0),
    ]
    
    constraints = TaskConstraints(rubric={}, architect_rubric={})
    result = selector.choose(ranked, constraints)
    # Winner is now the full DeliberationResult object, not just content string
    assert result["winner"].proposal.content == "X"
    assert result["winner"].score == 3.0
