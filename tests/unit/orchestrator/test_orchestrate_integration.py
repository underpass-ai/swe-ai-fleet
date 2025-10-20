"""Integration tests for Orchestrate use case.

Integration tests use real components but no infrastructure (gRPC/NATS/Redis).
"""

import asyncio
import pytest

from swe_ai_fleet.orchestrator.config_module.system_config import SystemConfig
from swe_ai_fleet.orchestrator.domain.agents.architect_agent import ArchitectAgent
from swe_ai_fleet.orchestrator.domain.agents.mock_agent import AgentBehavior, MockAgent
from swe_ai_fleet.orchestrator.domain.agents.services import ArchitectSelectorService
from swe_ai_fleet.orchestrator.domain.check_results.services import Scoring
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints
from swe_ai_fleet.orchestrator.usecases.dispatch_usecase import Orchestrate
from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate


class TestOrchestrateIntegration:
    """Integration tests for Orchestrate use case with real components."""

    def test_orchestrate_complete_workflow_single_role(self):
        """Test complete orchestration workflow for a single role."""
        # Setup councils
        dev_agents = [
            MockAgent(
                f"dev-{i}",
                "DEV",
                behavior=AgentBehavior.EXCELLENT if i == 0 else AgentBehavior.NORMAL,
                seed=i,
            )
            for i in range(3)
        ]
        
        scoring = Scoring()
        dev_council = Deliberate(agents=dev_agents, tooling=scoring, rounds=1)
        
        councils = {"DEV": dev_council}
        
        # Setup architect and config
        architect = ArchitectSelectorService(architect=ArchitectAgent())
        config = SystemConfig(roles=[])
        
        # Create orchestrate use case
        orchestrate = Orchestrate(config=config, councils=councils, architect=architect)
        
        # Execute
        task = "Implement REST API endpoint for user registration"
        constraints = TaskConstraints(
            rubric={"quality": "high", "security": "critical"},
            architect_rubric={"k": 3}
        )
        
        result = asyncio.run(orchestrate.execute(role="DEV", task=task, constraints=constraints))
        
        # Verify
        assert result is not None
        assert "winner" in result
        assert "candidates" in result
        
        # Winner should be a DeliberationResult
        winner = result["winner"]
        assert winner.proposal is not None
        assert winner.proposal.content != ""
        assert winner.score >= 0
        
        # Should have candidates
        candidates = result["candidates"]
        assert len(candidates) > 0
        assert all(isinstance(c, dict) for c in candidates)

    def test_orchestrate_multiple_roles(self):
        """Test orchestration with multiple role councils."""
        # Setup councils for different roles
        roles_configs = {
            "DEV": 3,
            "QA": 3,
            "ARCHITECT": 2,
        }
        
        councils = {}
        scoring = Scoring()
        
        for role, num_agents in roles_configs.items():
            agents = [
                MockAgent(f"{role.lower()}-{i}", role, behavior=AgentBehavior.NORMAL, seed=i)
                for i in range(num_agents)
            ]
            councils[role] = Deliberate(agents=agents, tooling=scoring, rounds=1)
        
        architect = ArchitectSelectorService(architect=ArchitectAgent())
        config = SystemConfig(roles=[])
        orchestrate = Orchestrate(config=config, councils=councils, architect=architect)
        
        # Execute for different roles
        tasks = {
            "DEV": "Implement OAuth2 authentication",
            "QA": "Create comprehensive test suite",
            "ARCHITECT": "Design microservices architecture",
        }
        
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 2}
        )
        
        for role, task in tasks.items():
            result = asyncio.run(orchestrate.execute(role=role, task=task, constraints=constraints))
            
            assert result is not None
            assert result["winner"] is not None
            assert result["winner"].proposal.author.role == role

    def test_orchestrate_architect_selection_picks_best(self):
        """Test that architect correctly selects the best proposal."""
        # Create agents with EXCELLENT first (should win)
        agents = [
            MockAgent("excellent", "DEV", behavior=AgentBehavior.EXCELLENT, seed=1),
            MockAgent("poor-1", "DEV", behavior=AgentBehavior.POOR, seed=2),
            MockAgent("poor-2", "DEV", behavior=AgentBehavior.POOR, seed=3),
        ]
        
        scoring = Scoring()
        council = Deliberate(agents=agents, tooling=scoring, rounds=1)
        councils = {"DEV": council}
        
        architect = ArchitectSelectorService(architect=ArchitectAgent())
        config = SystemConfig(roles=[])
        orchestrate = Orchestrate(config=config, councils=councils, architect=architect)
        
        task = "Implement critical payment processing"
        constraints = TaskConstraints(
            rubric={"correctness": "critical", "security": "critical"},
            architect_rubric={"k": 3}
        )
        
        result = asyncio.run(orchestrate.execute(role="DEV", task=task, constraints=constraints))
        
        # EXCELLENT agent should win
        winner = result["winner"]
        assert winner.proposal.author.agent_id == "excellent"
        assert winner.score > 0

    def test_orchestrate_with_varied_k_values(self):
        """Test orchestration with different k values for architect selection."""
        agents = [
            MockAgent(f"agent-{i}", "DEV", behavior=AgentBehavior.NORMAL, seed=i)
            for i in range(5)
        ]
        
        scoring = Scoring()
        council = Deliberate(agents=agents, tooling=scoring, rounds=1)
        councils = {"DEV": council}
        
        architect = ArchitectSelectorService(architect=ArchitectAgent())
        config = SystemConfig(roles=[])
        orchestrate = Orchestrate(config=config, councils=councils, architect=architect)
        
        task = "Implement caching strategy"
        
        # Test with k=1 (top 1)
        constraints_k1 = TaskConstraints(
            rubric={"performance": "high"},
            architect_rubric={"k": 1}
        )
        result_k1 = asyncio.run(orchestrate.execute(role="DEV", task=task, constraints=constraints_k1))
        assert len(result_k1["candidates"]) == 1
        
        # Test with k=3 (top 3)
        constraints_k3 = TaskConstraints(
            rubric={"performance": "high"},
            architect_rubric={"k": 3}
        )
        result_k3 = asyncio.run(orchestrate.execute(role="DEV", task=task, constraints=constraints_k3))
        assert len(result_k3["candidates"]) == 3
        
        # Test with k=5 (all)
        constraints_k5 = TaskConstraints(
            rubric={"performance": "high"},
            architect_rubric={"k": 5}
        )
        result_k5 = asyncio.run(orchestrate.execute(role="DEV", task=task, constraints=constraints_k5))
        assert len(result_k5["candidates"]) == 5

    def test_orchestrate_error_prone_agents_are_scored_lower(self):
        """Test that error-prone agents score lower than normal agents."""
        agents = [
            MockAgent("normal", "DEV", behavior=AgentBehavior.NORMAL, seed=1),
            MockAgent("error-prone", "DEV", behavior=AgentBehavior.ERROR_PRONE, seed=2),
            MockAgent("excellent", "DEV", behavior=AgentBehavior.EXCELLENT, seed=3),
        ]
        
        scoring = Scoring()
        council = Deliberate(agents=agents, tooling=scoring, rounds=1)
        councils = {"DEV": council}
        
        architect = ArchitectSelectorService(architect=ArchitectAgent())
        config = SystemConfig(roles=[])
        orchestrate = Orchestrate(config=config, councils=councils, architect=architect)
        
        task = "Implement transaction rollback mechanism"
        constraints = TaskConstraints(
            rubric={"correctness": "critical"},
            architect_rubric={"k": 3}
        )
        
        result = asyncio.run(orchestrate.execute(role="DEV", task=task, constraints=constraints))
        
        # Winner should not be ERROR_PRONE agent
        winner = result["winner"]
        assert winner.proposal.author.agent_id != "error-prone"
        
        # Verify winner has a score
        assert winner.score >= 0

    def test_orchestrate_with_complex_task_and_multiple_rounds(self):
        """Test orchestration with complex task requiring multiple review rounds."""
        agents = [
            MockAgent(f"dev-{i}", "DEV", behavior=AgentBehavior.NORMAL, seed=i)
            for i in range(4)
        ]
        
        scoring = Scoring()
        council = Deliberate(agents=agents, tooling=scoring, rounds=3)
        councils = {"DEV": council}
        
        architect = ArchitectSelectorService(architect=ArchitectAgent())
        config = SystemConfig(roles=[])
        orchestrate = Orchestrate(config=config, councils=councils, architect=architect)
        
        task = """
        Design and implement a distributed task queue with:
        1. At-least-once delivery guarantees
        2. Horizontal scalability
        3. Monitoring and alerting
        4. Dead letter queue handling
        5. Priority-based task execution
        """
        
        constraints = TaskConstraints(
            rubric={
                "completeness": "all requirements covered",
                "scalability": "horizontal scaling",
                "reliability": "no data loss"
            },
            architect_rubric={"k": 4}
        )
        
        result = asyncio.run(orchestrate.execute(role="DEV", task=task, constraints=constraints))
        
        # Verify complex task was handled
        assert result["winner"] is not None
        assert len(result["winner"].proposal.content) > 100  # Should be substantive
        assert len(result["candidates"]) == 4


  
class TestOrchestrateEdgeCases:
    """Integration tests for edge cases and error scenarios."""

    def test_orchestrate_with_no_councils_raises_error(self):
        """Test that orchestration fails gracefully with no councils."""
        architect = ArchitectSelectorService(architect=ArchitectAgent())
        config = SystemConfig(roles=[])
        
        # Empty councils
        orchestrate = Orchestrate(config=config, councils={}, architect=architect)
        
        task = "Some task"
        constraints = TaskConstraints(rubric={}, architect_rubric={"k": 1})
        
        # Should raise KeyError for missing role
        with pytest.raises(KeyError):
            asyncio.run(orchestrate.execute(role="DEV", task=task, constraints=constraints))

    def test_orchestrate_with_mismatched_role(self):
        """Test orchestration with role that doesn't exist in councils."""
        agents = [MockAgent("dev-1", "DEV", behavior=AgentBehavior.NORMAL, seed=1)]
        scoring = Scoring()
        council = Deliberate(agents=agents, tooling=scoring, rounds=1)
        
        councils = {"DEV": council}  # Only DEV council
        
        architect = ArchitectSelectorService(architect=ArchitectAgent())
        config = SystemConfig(roles=[])
        orchestrate = Orchestrate(config=config, councils=councils, architect=architect)
        
        task = "QA task"
        constraints = TaskConstraints(rubric={}, architect_rubric={"k": 1})
        
        # Should raise KeyError for QA role (not in councils)
        with pytest.raises(KeyError):
            asyncio.run(orchestrate.execute(role="QA", task=task, constraints=constraints))

