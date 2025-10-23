"""Unit tests for MockAgent."""

import pytest

from core.orchestrator.domain.agents.mock_agent import (
    AgentBehavior,
    MockAgent,
    create_mock_council,
)
from core.orchestrator.domain.tasks.task_constraints import TaskConstraints


class TestMockAgent:
    """Unit tests for MockAgent."""
    
    def test_create_agent_with_defaults(self):
        """Test creating an agent with default behavior."""
        agent = MockAgent("agent-001", "DEV")
        
        assert agent.agent_id == "agent-001"
        assert agent.role == "DEV"
        assert agent.behavior == AgentBehavior.NORMAL
    
    def test_generate_returns_content(self):
        """Test that generate returns content dictionary."""
        agent = MockAgent("agent-001", "DEV")
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3}
        )
        
        result = agent.generate("Implement login", constraints, diversity=False)
        
        assert isinstance(result, dict)
        assert "content" in result
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
    
    def test_generate_includes_task_in_content(self):
        """Test that generated content mentions the task."""
        agent = MockAgent("agent-001", "DEV")
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3}
        )
        
        task = "Implement user authentication"
        result = agent.generate(task, constraints)
        
        assert task in result["content"]
    
    def test_critique_returns_feedback(self):
        """Test that critique returns feedback string."""
        agent = MockAgent("agent-001", "DEV")
        proposal = "Sample proposal content"
        rubric = {"quality": "high", "tests": "required"}
        
        feedback = agent.critique(proposal, rubric)
        
        assert isinstance(feedback, str)
        assert len(feedback) > 0
    
    def test_revise_returns_modified_content(self):
        """Test that revise returns modified content."""
        agent = MockAgent("agent-001", "DEV")
        original = "Original proposal"
        feedback = "Add more detail"
        
        revised = agent.revise(original, feedback)
        
        assert isinstance(revised, str)
        # Should contain original (for NORMAL behavior)
        assert original in revised
    
    @pytest.mark.parametrize("behavior", [
        AgentBehavior.EXCELLENT,
        AgentBehavior.POOR,
        AgentBehavior.VERBOSE,
        AgentBehavior.CONCISE,
        AgentBehavior.ERROR_PRONE,
    ])
    def test_different_behaviors_generate_different_content(self, behavior):
        """Test that different behaviors produce different proposals."""
        agent = MockAgent("agent-001", "DEV", behavior=behavior)
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3}
        )
        
        result = agent.generate("Implement API", constraints)
        
        assert "content" in result
        assert len(result["content"]) > 0
        # Each behavior should mention agent_id or task
        content = result["content"]
        assert "agent-001" in content or "API" in content
    
    def test_excellent_behavior_produces_detailed_content(self):
        """Test that EXCELLENT behavior produces high-quality content."""
        agent = MockAgent("agent-001", "DEV", behavior=AgentBehavior.EXCELLENT)
        constraints = TaskConstraints(
            rubric={"quality": "high", "tests": "required"},
            architect_rubric={"k": 3}
        )
        
        result = agent.generate("Implement feature", constraints)
        content = result["content"]
        
        # Excellent proposals should have multiple sections
        assert "##" in content or "Phase" in content
        assert len(content) > 200  # Should be detailed
    
    def test_poor_behavior_produces_minimal_content(self):
        """Test that POOR behavior produces low-quality content."""
        agent = MockAgent("agent-001", "DEV", behavior=AgentBehavior.POOR)
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3}
        )
        
        result = agent.generate("Implement feature", constraints)
        content = result["content"]
        
        # Poor proposals should be brief
        assert len(content) < 200
    
    def test_stubborn_agent_does_not_revise(self):
        """Test that STUBBORN agent doesn't change content on revision."""
        agent = MockAgent("agent-001", "DEV", behavior=AgentBehavior.STUBBORN)
        original = "Original proposal"
        feedback = "Please improve this significantly"
        
        revised = agent.revise(original, feedback)
        
        # Stubborn agent returns unchanged content
        assert revised == original
    
    def test_stubborn_agent_provides_minimal_critique(self):
        """Test that STUBBORN agent provides unhelpful feedback."""
        agent = MockAgent("agent-001", "DEV", behavior=AgentBehavior.STUBBORN)
        proposal = "Some proposal"
        rubric = {"quality": "high"}
        
        feedback = agent.critique(proposal, rubric)
        
        # Stubborn agents don't provide useful feedback
        assert len(feedback) < 50
    
    def test_metadata_included_in_generate(self):
        """Test that generate includes metadata."""
        agent = MockAgent("agent-001", "DEV", behavior=AgentBehavior.NORMAL)
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3}
        )
        
        result = agent.generate("Task", constraints, diversity=True)
        
        assert "metadata" in result
        metadata = result["metadata"]
        assert metadata["agent_id"] == "agent-001"
        assert metadata["role"] == "DEV"
        assert metadata["behavior"] == "normal"
        assert metadata["diversity"] is True
    
    def test_agent_string_representation(self):
        """Test agent's string representations."""
        agent = MockAgent("agent-dev-001", "DEV", behavior=AgentBehavior.EXCELLENT)
        
        repr_str = repr(agent)
        assert "MockAgent" in repr_str
        assert "agent-dev-001" in repr_str
        assert "DEV" in repr_str
        
        str_str = str(agent)
        assert "agent-dev-001" in str_str
        assert "DEV" in str_str


class TestCreateMockCouncil:
    """Unit tests for create_mock_council factory function."""
    
    def test_create_council_default_size(self):
        """Test creating council with default size."""
        council = create_mock_council("DEV")
        
        assert len(council) == 3
        assert all(isinstance(agent, MockAgent) for agent in council)
        assert all(agent.role == "DEV" for agent in council)
    
    def test_create_council_custom_size(self):
        """Test creating council with custom size."""
        council = create_mock_council("QA", num_agents=5)
        
        assert len(council) == 5
    
    def test_create_council_default_behaviors(self):
        """Test that default behaviors include one EXCELLENT and rest NORMAL."""
        council = create_mock_council("DEV", num_agents=3)
        
        behaviors = [agent.behavior for agent in council]
        assert behaviors.count(AgentBehavior.EXCELLENT) == 1
        assert behaviors.count(AgentBehavior.NORMAL) == 2
    
    def test_create_council_custom_behaviors(self):
        """Test creating council with custom behaviors."""
        custom_behaviors = [
            AgentBehavior.EXCELLENT,
            AgentBehavior.POOR,
            AgentBehavior.NORMAL,
        ]
        
        council = create_mock_council(
            "ARCHITECT",
            num_agents=3,
            behaviors=custom_behaviors
        )
        
        assert len(council) == 3
        assert council[0].behavior == AgentBehavior.EXCELLENT
        assert council[1].behavior == AgentBehavior.POOR
        assert council[2].behavior == AgentBehavior.NORMAL
    
    def test_create_council_agent_ids_are_unique(self):
        """Test that all agents in council have unique IDs."""
        council = create_mock_council("DEV", num_agents=5)
        
        agent_ids = [agent.agent_id for agent in council]
        assert len(agent_ids) == len(set(agent_ids))  # All unique
    
    def test_create_council_agent_ids_follow_pattern(self):
        """Test that agent IDs follow expected pattern."""
        council = create_mock_council("QA", num_agents=3)
        
        expected_ids = ["agent-qa-000", "agent-qa-001", "agent-qa-002"]
        actual_ids = [agent.agent_id for agent in council]
        
        assert actual_ids == expected_ids
    
    def test_create_council_mismatched_behaviors_raises_error(self):
        """Test that mismatched behaviors count raises ValueError."""
        with pytest.raises(ValueError, match="must match num_agents"):
            create_mock_council(
                "DEV",
                num_agents=3,
                behaviors=[AgentBehavior.NORMAL, AgentBehavior.EXCELLENT]  # Only 2
            )

