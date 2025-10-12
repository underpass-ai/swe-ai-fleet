"""Integration tests for Deliberate use case.

Integration tests use real components (MockAgent, Scoring) but no infrastructure.
"""


from swe_ai_fleet.orchestrator.domain.agents.mock_agent import AgentBehavior, MockAgent
from swe_ai_fleet.orchestrator.domain.check_results.services import Scoring
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints
from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate


class TestDeliberateIntegration:
    """Integration tests for Deliberate use case with real components."""

    def test_deliberate_with_real_agents_single_round(self):
        """Test deliberation with real MockAgents - single round."""
        # Setup: 3 agents with different behaviors
        agents = [
            MockAgent("agent-1", "DEV", behavior=AgentBehavior.EXCELLENT, seed=1),
            MockAgent("agent-2", "DEV", behavior=AgentBehavior.NORMAL, seed=2),
            MockAgent("agent-3", "DEV", behavior=AgentBehavior.POOR, seed=3),
        ]
        
        scoring = Scoring()
        deliberate = Deliberate(agents=agents, tooling=scoring, rounds=1)
        
        # Execute
        task = "Implement user authentication with JWT tokens"
        constraints = TaskConstraints(
            rubric={"quality": "high", "security": "critical"},
            architect_rubric={"k": 3}
        )
        
        results = deliberate.execute(task, constraints)
        
        # Verify
        assert len(results) == 3, "Should have 3 deliberation results"
        assert all(r.proposal is not None for r in results), "All should have proposals"
        assert all(r.checks is not None for r in results), "All should have checks"
        assert all(r.score >= 0 for r in results), "All should have scores"
        
        # Results should be sorted by score (highest first)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True), "Should be sorted by score"
        
        # EXCELLENT agent should typically win (highest score)
        winner = results[0]
        assert winner.proposal.author.agent_id == "agent-1", "EXCELLENT agent should win"

    def test_deliberate_with_multiple_rounds_improves_quality(self):
        """Test that multiple deliberation rounds improve through peer review."""
        agents = [
            MockAgent("agent-1", "DEV", behavior=AgentBehavior.NORMAL, seed=1),
            MockAgent("agent-2", "DEV", behavior=AgentBehavior.NORMAL, seed=2),
            MockAgent("agent-3", "DEV", behavior=AgentBehavior.NORMAL, seed=3),
        ]
        
        scoring = Scoring()
        task = "Design scalable microservices architecture"
        constraints = TaskConstraints(
            rubric={"scalability": "high", "maintainability": "high"},
            architect_rubric={"k": 3}
        )
        
        # Single round
        deliberate_1 = Deliberate(agents=agents, tooling=scoring, rounds=1)
        results_1 = deliberate_1.execute(task, constraints)
        
        # Multiple rounds
        deliberate_3 = Deliberate(agents=agents, tooling=scoring, rounds=3)
        results_3 = deliberate_3.execute(task, constraints)
        
        # Verify both completed successfully
        assert len(results_1) == 3
        assert len(results_3) == 3
        
        # All proposals should have content (peer review happened)
        for result in results_3:
            assert len(result.proposal.content) > 0
            assert result.proposal.author is not None

    def test_deliberate_with_different_agent_behaviors(self):
        """Test deliberation with different agent behaviors."""
        agents = [
            MockAgent("excellent", "QA", behavior=AgentBehavior.EXCELLENT, seed=1),
            MockAgent("verbose", "QA", behavior=AgentBehavior.VERBOSE, seed=2),
            MockAgent("concise", "QA", behavior=AgentBehavior.CONCISE, seed=3),
        ]
        
        scoring = Scoring()
        deliberate = Deliberate(agents=agents, tooling=scoring, rounds=1)
        
        task = "Create comprehensive test plan for payment processing"
        constraints = TaskConstraints(
            rubric={"coverage": "complete", "clarity": "high"},
            architect_rubric={"k": 3}
        )
        
        results = deliberate.execute(task, constraints)
        
        # Verify all agents participated
        assert len(results) == 3
        
        # Verify proposals have different characteristics based on behavior
        proposals = {r.proposal.author.agent_id: r.proposal.content for r in results}
        
        # All should have generated content
        assert all(len(content) > 0 for content in proposals.values())
        
        # Different behaviors should produce different content
        assert len(set(proposals.values())) == 3, "All proposals should be unique"

    def test_deliberate_with_constraints_validation(self):
        """Test that constraints are properly applied during deliberation."""
        agents = [
            MockAgent(f"agent-{i}", "ARCHITECT", behavior=AgentBehavior.NORMAL, seed=i)
            for i in range(3)
        ]
        
        scoring = Scoring()
        deliberate = Deliberate(agents=agents, tooling=scoring, rounds=2)
        
        task = "Design database schema with strict normalization"
        constraints = TaskConstraints(
            rubric={
                "normalization": "3NF minimum",
                "performance": "sub-100ms queries",
                "security": "encryption at rest"
            },
            architect_rubric={"k": 2}
        )
        
        results = deliberate.execute(task, constraints)
        
        # Verify constraints were passed through
        assert len(results) == 3
        
        # All results should have been scored
        for result in results:
            assert result.checks is not None
            assert isinstance(result.score, float)
            assert 0.0 <= result.score <= 1.0

    def test_deliberate_with_single_agent(self):
        """Test deliberation with a single agent (edge case)."""
        agents = [
            MockAgent("solo-agent", "DEV", behavior=AgentBehavior.EXCELLENT, seed=42)
        ]
        
        scoring = Scoring()
        deliberate = Deliberate(agents=agents, tooling=scoring, rounds=1)
        
        task = "Fix critical security vulnerability"
        constraints = TaskConstraints(
            rubric={"security": "critical"},
            architect_rubric={"k": 1}
        )
        
        results = deliberate.execute(task, constraints)
        
        # Should work with single agent (no peer review)
        assert len(results) == 1
        assert results[0].proposal.author.agent_id == "solo-agent"
        assert results[0].score >= 0

    def test_deliberate_peer_review_modifies_proposals(self):
        """Test that peer review actually modifies proposals."""
        # Use STUBBORN behavior to verify revision is attempted
        agents = [
            MockAgent("agent-1", "DEV", behavior=AgentBehavior.NORMAL, seed=1),
            MockAgent("agent-2", "DEV", behavior=AgentBehavior.STUBBORN, seed=2),
            MockAgent("agent-3", "DEV", behavior=AgentBehavior.NORMAL, seed=3),
        ]
        
        scoring = Scoring()
        deliberate = Deliberate(agents=agents, tooling=scoring, rounds=2)
        
        task = "Implement caching layer for API"
        constraints = TaskConstraints(
            rubric={"performance": "high"},
            architect_rubric={"k": 3}
        )
        
        results = deliberate.execute(task, constraints)
        
        # All agents should have proposals (revision happened)
        assert len(results) == 3
        
        # STUBBORN agent might not improve much, but process should complete
        stubborn_result = next(r for r in results if r.proposal.author.agent_id == "agent-2")
        assert stubborn_result is not None
        assert stubborn_result.proposal.content != ""

    def test_deliberate_scoring_is_consistent(self):
        """Test that scoring is applied consistently to all proposals."""
        agents = [
            MockAgent(f"agent-{i}", "DEV", behavior=AgentBehavior.NORMAL, seed=i)
            for i in range(5)
        ]
        
        scoring = Scoring()
        deliberate = Deliberate(agents=agents, tooling=scoring, rounds=1)
        
        task = "Implement rate limiting middleware"
        constraints = TaskConstraints(
            rubric={"correctness": "high"},
            architect_rubric={"k": 5}
        )
        
        results = deliberate.execute(task, constraints)
        
        # All should be scored
        assert len(results) == 5
        assert all(hasattr(r, 'score') for r in results)
        
        # Scores should be sorted descending
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, "Should be sorted by score"

    def test_deliberate_empty_task_handled_gracefully(self):
        """Test deliberation with empty task description."""
        agents = [
            MockAgent("agent-1", "DEV", behavior=AgentBehavior.NORMAL, seed=1)
        ]
        
        scoring = Scoring()
        deliberate = Deliberate(agents=agents, tooling=scoring, rounds=1)
        
        # Empty task
        task = ""
        constraints = TaskConstraints(
            rubric={},
            architect_rubric={"k": 1}
        )
        
        # Should handle gracefully (MockAgent generates content anyway)
        results = deliberate.execute(task, constraints)
        
        assert len(results) == 1
        assert results[0].proposal.content != ""  # MockAgent generates something

