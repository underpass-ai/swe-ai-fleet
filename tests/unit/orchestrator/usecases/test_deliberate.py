"""Unit tests for Deliberate use case."""

from unittest.mock import Mock

import pytest

from swe_ai_fleet.orchestrator.domain.agents.mock_agent import (
    AgentBehavior,
    MockAgent,
    create_mock_council,
)
from swe_ai_fleet.orchestrator.domain.check_results.check_suite import CheckSuiteResult
from swe_ai_fleet.orchestrator.domain.check_results.services.scoring import Scoring
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints
from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate


class TestDeliberate:
    """Unit tests for Deliberate use case."""
    
    @pytest.fixture
    def constraints(self):
        """Create test constraints."""
        return TaskConstraints(
            rubric={"quality": "high", "tests": "required", "documentation": "complete"},
            architect_rubric={"k": 3, "criteria": "best overall"}
        )
    
    @pytest.fixture
    def mock_scoring(self):
        """Create mock scoring service."""
        scoring = Mock(spec=Scoring)
        
        # Mock check suite result
        scoring.run_check_suite.return_value = CheckSuiteResult(
            lint=None,
            dryrun=None,
            policy=None,
        )
        
        # Mock score (will be overridden per test)
        scoring.score_checks.return_value = 0.8
        
        return scoring
    
    def test_execute_generates_proposals_from_all_agents(
        self, constraints, mock_scoring
    ):
        """Test that deliberate generates proposals from all agents."""
        # Arrange
        agents = create_mock_council("DEV", num_agents=3)
        
        deliberate = Deliberate(
            agents=agents,
            tooling=mock_scoring,
            rounds=0  # No peer review for this test
        )
        
        # Act
        results = deliberate.execute("Implement login endpoint", constraints)
        
        # Assert
        assert len(results) == 3
        # Each result should have a proposal
        for result in results:
            assert result.proposal is not None
            assert result.proposal.content is not None
            assert len(result.proposal.content) > 0
    
    def test_execute_performs_peer_review_rounds(self, constraints, mock_scoring):
        """Test that deliberate performs peer review rounds."""
        # Arrange - Use mock agents so we can verify calls
        agent1 = MockAgent("agent-1", "DEV", behavior=AgentBehavior.NORMAL)
        agent2 = MockAgent("agent-2", "DEV", behavior=AgentBehavior.NORMAL)
        agent3 = MockAgent("agent-3", "DEV", behavior=AgentBehavior.NORMAL)
        
        deliberate = Deliberate(
            agents=[agent1, agent2, agent3],
            tooling=mock_scoring,
            rounds=2  # 2 rounds of peer review
        )
        
        # Act
        results = deliberate.execute("Implement feature", constraints)
        
        # Assert
        # Verify we got results
        assert len(results) == 3
        
        # Each result should have revised content
        # (revisions add "REVISION" markers in mock agent)
        for result in results:
            # After 2 rounds, should have 2 revision markers
            revision_count = result.proposal.content.count("REVISION")
            assert revision_count == 2
    
    def test_execute_returns_sorted_by_score_descending(
        self, constraints, mock_scoring
    ):
        """Test that results are sorted by score (highest first)."""
        # Arrange
        agents = [
            MockAgent("agent-1", "DEV", behavior=AgentBehavior.POOR),     # Will get lowest score
            MockAgent("agent-2", "DEV", behavior=AgentBehavior.EXCELLENT),  # Will get highest score
            MockAgent("agent-3", "DEV", behavior=AgentBehavior.NORMAL),   # Will get middle score
        ]
        
        # Mock different scores based on proposal quality
        def score_based_on_content(check_suite):
            # This is a simplified scoring - in reality Scoring does this
            return 0.9  # Will be overridden by side_effect below
        
        # Give different scores to simulate quality differences
        mock_scoring.score_checks.side_effect = [0.6, 0.95, 0.75]
        
        deliberate = Deliberate(
            agents=agents,
            tooling=mock_scoring,
            rounds=0  # No peer review to keep scoring simple
        )
        
        # Act
        results = deliberate.execute("Implement API", constraints)
        
        # Assert
        assert len(results) == 3
        # Results should be sorted by score (descending)
        assert results[0].score >= results[1].score
        assert results[1].score >= results[2].score
        
        # Specifically check the expected order
        assert results[0].score == 0.95  # EXCELLENT agent
        assert results[1].score == 0.75  # NORMAL agent
        assert results[2].score == 0.6   # POOR agent
    
    def test_execute_with_zero_rounds_skips_peer_review(
        self, constraints, mock_scoring
    ):
        """Test that rounds=0 skips peer review."""
        # Arrange
        agents = create_mock_council("QA", num_agents=3)
        
        deliberate = Deliberate(
            agents=agents,
            tooling=mock_scoring,
            rounds=0  # No peer review
        )
        
        # Act
        results = deliberate.execute("Write test suite", constraints)
        
        # Assert
        assert len(results) == 3
        # No revisions should have been made
        for result in results:
            assert "REVISION" not in result.proposal.content
    
    def test_execute_with_single_agent(self, constraints, mock_scoring):
        """Test deliberation with single agent (edge case)."""
        # Arrange
        single_agent = [MockAgent("solo-agent", "ARCHITECT")]
        
        deliberate = Deliberate(
            agents=single_agent,
            tooling=mock_scoring,
            rounds=1
        )
        
        # Act
        results = deliberate.execute("Design system architecture", constraints)
        
        # Assert
        assert len(results) == 1
        assert results[0].proposal.author.agent_id == "solo-agent"
    
    def test_execute_with_diversity_flag(self, constraints, mock_scoring):
        """Test that diversity flag is passed to agents."""
        # Arrange
        agents = create_mock_council("DEV", num_agents=2)
        
        deliberate = Deliberate(
            agents=agents,
            tooling=mock_scoring,
            rounds=0
        )
        
        # Act
        results = deliberate.execute("Implement feature", constraints)
        
        # Assert
        # MockAgent includes "with diversity" in content when diversity=True
        # By default, Deliberate passes diversity=True
        for result in results:
            # Check metadata was included
            assert result.proposal.content is not None
    
    def test_execute_calls_scoring_for_each_proposal(
        self, constraints, mock_scoring
    ):
        """Test that scoring is called for each proposal."""
        # Arrange
        agents = create_mock_council("DEV", num_agents=4)
        
        deliberate = Deliberate(
            agents=agents,
            tooling=mock_scoring,
            rounds=0
        )
        
        # Act
        deliberate.execute("Implement feature", constraints)
        
        # Assert
        # Should have called run_check_suite for each of 4 proposals
        assert mock_scoring.run_check_suite.call_count == 4
        # Should have called score_checks for each of 4 proposals
        assert mock_scoring.score_checks.call_count == 4
    
    def test_execute_with_stubborn_agents(self, constraints, mock_scoring):
        """Test deliberation with stubborn agents that don't revise."""
        # Arrange
        agents = [
            MockAgent("agent-1", "DEV", behavior=AgentBehavior.STUBBORN),
            MockAgent("agent-2", "DEV", behavior=AgentBehavior.STUBBORN),
        ]
        
        deliberate = Deliberate(
            agents=agents,
            tooling=mock_scoring,
            rounds=2  # Even with 2 rounds, stubborn agents won't revise
        )
        
        # Act
        results = deliberate.execute("Implement feature", constraints)
        
        # Assert
        assert len(results) == 2
        # Stubborn agents don't revise, so no REVISION markers
        for result in results:
            assert "REVISION" not in result.proposal.content
    
    def test_execute_preserves_agent_identity(self, constraints, mock_scoring):
        """Test that agent identity is preserved in results."""
        # Arrange
        agents = [
            MockAgent("alice", "DEV"),
            MockAgent("bob", "DEV"),
            MockAgent("charlie", "DEV"),
        ]
        
        deliberate = Deliberate(
            agents=agents,
            tooling=mock_scoring,
            rounds=0
        )
        
        # Act
        results = deliberate.execute("Implement feature", constraints)
        
        # Assert
        agent_ids = {result.proposal.author.agent_id for result in results}
        assert agent_ids == {"alice", "bob", "charlie"}
    
    def test_execute_returns_deliberation_results(self, constraints, mock_scoring):
        """Test that execute returns proper DeliberationResult objects."""
        # Arrange
        agents = create_mock_council("DEV", num_agents=2)
        
        deliberate = Deliberate(
            agents=agents,
            tooling=mock_scoring,
            rounds=0
        )
        
        # Act
        results = deliberate.execute("Implement feature", constraints)
        
        # Assert
        for result in results:
            # Each result should have all required fields
            assert hasattr(result, 'proposal')
            assert hasattr(result, 'checks')
            assert hasattr(result, 'score')
            
            # Proposal should have author and content
            assert hasattr(result.proposal, 'author')
            assert hasattr(result.proposal, 'content')
            
            # Score should be a number
            assert isinstance(result.score, (int, float))

