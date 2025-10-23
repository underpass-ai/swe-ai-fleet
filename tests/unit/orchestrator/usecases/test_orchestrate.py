"""Unit tests for Orchestrate use case."""

import asyncio
from unittest.mock import Mock

import pytest

from core.orchestrator.domain.agents.mock_agent import (
    AgentBehavior,
    create_mock_council,
)
from core.orchestrator.domain.agents.role import Role
from core.orchestrator.domain.check_results.check_suite import CheckSuiteResult
from core.orchestrator.domain.check_results.services.scoring import Scoring
from core.orchestrator.domain.tasks.task import Task
from core.orchestrator.domain.tasks.task_constraints import TaskConstraints
from core.orchestrator.usecases.orchestrate_usecase import Orchestrate
from core.orchestrator.usecases.peer_deliberation_usecase import Deliberate


class TestOrchestrate:
    """Unit tests for Orchestrate use case."""
    
    @pytest.fixture
    def constraints(self):
        """Create test constraints."""
        return TaskConstraints(
            rubric={"quality": "high", "tests": "required"},
            architect_rubric={"k": 3}
        )
    
    @pytest.fixture
    def mock_scoring(self):
        """Create mock scoring service."""
        scoring = Mock(spec=Scoring)
        scoring.run_check_suite.return_value = CheckSuiteResult(
            lint=None, dryrun=None, policy=None
        )
        scoring.score_checks.return_value = 0.8
        return scoring
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.default_rounds = 1
        return config
    
    @pytest.fixture
    def dev_council(self, mock_scoring):
        """Create a DEV council (Deliberate use case)."""
        agents = create_mock_council("DEV", num_agents=3)
        return Deliberate(agents=agents, tooling=mock_scoring, rounds=1)
    
    @pytest.fixture
    def qa_council(self, mock_scoring):
        """Create a QA council (Deliberate use case)."""
        agents = create_mock_council("QA", num_agents=3)
        return Deliberate(agents=agents, tooling=mock_scoring, rounds=1)
    
    @pytest.fixture
    def architect_council(self, mock_scoring):
        """Create an ARCHITECT council (Deliberate use case)."""
        agents = create_mock_council("ARCHITECT", num_agents=2)
        return Deliberate(agents=agents, tooling=mock_scoring, rounds=1)
    
    @pytest.fixture
    def mock_architect(self):
        """Create mock architect that selects winners."""
        architect = Mock()
        
        # Architect.choose() returns a dict with winner and candidates
        def choose_winner(ranked_results, constraints):
            # Select the highest scored result as winner
            winner = ranked_results[0] if ranked_results else None
            candidates = ranked_results[1:] if len(ranked_results) > 1 else []
            return {
                "winner": winner,
                "candidates": candidates,
                "reasoning": "Selected highest scoring proposal",
            }
        
        architect.choose.side_effect = choose_winner
        return architect
    
    def test_execute_delegates_to_correct_council(
        self, mock_config, dev_council, qa_council, mock_architect, constraints
    ):
        """Test that orchestrate delegates to the correct council based on role."""
        # Arrange
        councils = {
            "DEV": dev_council,
            "QA": qa_council,
        }
        
        orchestrate = Orchestrate(
            config=mock_config,
            councils=councils,
            architect=mock_architect
        )
        
        role = Role.from_string("DEV")
        task = Task.from_string("Implement login API", "TASK-001")
        
        # Act
        result = asyncio.run(orchestrate.execute(role, task, constraints))
        
        # Assert
        # The result should come from DEV council deliberation
        assert result is not None
        assert "winner" in result
        # Winner should be a DeliberationResult with a proposal
        assert result["winner"].proposal is not None
    
    def test_execute_architect_selects_winner(
        self, mock_config, dev_council, mock_architect, constraints
    ):
        """Test that architect is called to select winner from proposals."""
        # Arrange
        councils = {"DEV": dev_council}
        
        orchestrate = Orchestrate(
            config=mock_config,
            councils=councils,
            architect=mock_architect
        )
        
        role = Role.from_string("DEV")
        task = Task.from_string("Implement feature", "TASK-001")
        
        # Act
        asyncio.run(orchestrate.execute(role, task, constraints))
        
        # Assert
        # Architect should have been called
        assert mock_architect.choose.called
        
        # Verify it was called with deliberation results
        call_args = mock_architect.choose.call_args
        ranked_results = call_args[0][0]
        passed_constraints = call_args[0][1]
        
        # Should have received results from council
        assert len(ranked_results) > 0
        assert passed_constraints == constraints
    
    def test_execute_returns_winner_and_candidates(
        self, mock_config, dev_council, mock_architect, constraints
    ):
        """Test that orchestrate returns winner and candidates."""
        # Arrange
        councils = {"DEV": dev_council}
        
        orchestrate = Orchestrate(
            config=mock_config,
            councils=councils,
            architect=mock_architect
        )
        
        role = Role.from_string("DEV")
        task = Task.from_string("Implement feature", "TASK-001")
        
        # Act
        result = asyncio.run(orchestrate.execute(role, task, constraints))
        
        # Assert
        assert "winner" in result
        assert "candidates" in result
        
        # Winner should be the highest scored
        assert result["winner"] is not None
        
        # Candidates should be the rest
        assert isinstance(result["candidates"], list)
    
    def test_execute_with_different_roles(
        self, mock_config, dev_council, qa_council, architect_council, 
        mock_architect, constraints
    ):
        """Test orchestration with different role types."""
        # Arrange
        councils = {
            "DEV": dev_council,
            "QA": qa_council,
            "ARCHITECT": architect_council,
        }
        
        orchestrate = Orchestrate(
            config=mock_config,
            councils=councils,
            architect=mock_architect
        )
        
        test_cases = [
            ("DEV", "Implement API"),
            ("QA", "Write test suite"),
            ("ARCHITECT", "Design system"),
        ]
        
        for role_str, task_desc in test_cases:
            # Act
            role = Role.from_string(role_str)
            task = Task.from_string(task_desc, f"TASK-{role_str}")
            
            result = asyncio.run(orchestrate.execute(role, task, constraints))
            
            # Assert
            assert result is not None
            assert "winner" in result
            assert result["winner"] is not None
    
    def test_execute_preserves_task_context(
        self, mock_config, dev_council, mock_architect, constraints
    ):
        """Test that task context is preserved through orchestration."""
        # Arrange
        councils = {"DEV": dev_council}
        
        orchestrate = Orchestrate(
            config=mock_config,
            councils=councils,
            architect=mock_architect
        )
        
        role = Role.from_string("DEV")
        task_description = "Implement complex authentication system"
        task = Task.from_string(task_description, "TASK-AUTH-001")
        
        # Act
        result = asyncio.run(orchestrate.execute(role, task, constraints))
        
        # Assert
        # Winner's proposal should reference the task
        winner_content = result["winner"].proposal.content
        assert "authentication" in winner_content.lower() or "complex" in winner_content.lower()
    
    def test_execute_handles_single_proposal(
        self, mock_config, mock_scoring, mock_architect, constraints
    ):
        """Test orchestration with single agent council (edge case)."""
        # Arrange
        single_agent_council = create_mock_council("DEV", num_agents=1)
        council = Deliberate(agents=single_agent_council, tooling=mock_scoring, rounds=0)
        
        councils = {"DEV": council}
        
        orchestrate = Orchestrate(
            config=mock_config,
            councils=councils,
            architect=mock_architect
        )
        
        role = Role.from_string("DEV")
        task = Task.from_string("Simple task", "TASK-001")
        
        # Act
        result = asyncio.run(orchestrate.execute(role, task, constraints))
        
        # Assert
        assert result["winner"] is not None
        assert len(result["candidates"]) == 0  # Only one proposal, no candidates
    
    def test_execute_winner_has_highest_score(
        self, mock_config, mock_scoring, mock_architect, constraints
    ):
        """Test that winner is the highest scored proposal."""
        # Arrange
        # Create agents with different quality levels
        agents = [
            create_mock_council("DEV", num_agents=1, behaviors=[AgentBehavior.POOR])[0],
            create_mock_council("DEV", num_agents=1, behaviors=[AgentBehavior.EXCELLENT])[0],
            create_mock_council("DEV", num_agents=1, behaviors=[AgentBehavior.NORMAL])[0],
        ]
        
        # Give different scores
        mock_scoring.score_checks.side_effect = [0.5, 0.95, 0.7]
        
        council = Deliberate(agents=agents, tooling=mock_scoring, rounds=0)
        councils = {"DEV": council}
        
        orchestrate = Orchestrate(
            config=mock_config,
            councils=councils,
            architect=mock_architect
        )
        
        role = Role.from_string("DEV")
        task = Task.from_string("Task", "TASK-001")
        
        # Act
        result = asyncio.run(orchestrate.execute(role, task, constraints))
        
        # Assert
        # Winner should be the EXCELLENT agent (highest score: 0.95)
        assert result["winner"].score == 0.95
        
        # Candidates should be sorted by score
        if len(result["candidates"]) > 0:
            assert result["candidates"][0].score >= result["candidates"][-1].score
    
    def test_execute_with_missing_council_raises_error(
        self, mock_config, dev_council, mock_architect, constraints
    ):
        """Test that missing council raises appropriate error."""
        # Arrange
        councils = {"DEV": dev_council}  # Only DEV council
        
        orchestrate = Orchestrate(
            config=mock_config,
            councils=councils,
            architect=mock_architect
        )
        
        # Try to use QA role (not in councils)
        role = Role.from_string("QA")
        task = Task.from_string("Write tests", "TASK-001")
        
        # Act & Assert
        with pytest.raises(KeyError):
            asyncio.run(orchestrate.execute(role, task, constraints))

