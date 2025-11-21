"""Unit tests for AgentThought domain entity."""

import pytest
from core.agents_and_tools.agents.domain.entities.core.agent_thought import AgentThought


class TestAgentThoughtCreation:
    """Test AgentThought entity creation."""

    def test_create_thought_with_required_fields(self):
        """Test creating thought with required fields."""
        thought = AgentThought(
            iteration=1,
            thought_type="analysis",
            content="I need to analyze the codebase structure",
        )

        assert thought.iteration == 1
        assert thought.thought_type == "analysis"
        assert thought.content == "I need to analyze the codebase structure"
        assert thought.related_operations == []
        assert thought.confidence is None
        assert thought.timestamp is None

    def test_create_thought_with_all_fields(self):
        """Test creating thought with all fields."""
        thought = AgentThought(
            iteration=2,
            thought_type="decision",
            content="I will use the files tool to read the config",
            related_operations=["files.read_file"],
            confidence=0.85,
            timestamp="2024-01-01T12:00:00",
        )

        assert thought.iteration == 2
        assert thought.thought_type == "decision"
        assert thought.content == "I will use the files tool to read the config"
        assert thought.related_operations == ["files.read_file"]
        assert thought.confidence == pytest.approx(0.85)
        assert thought.timestamp == "2024-01-01T12:00:00"

    def test_create_thought_with_empty_related_operations(self):
        """Test creating thought with empty related operations."""
        thought = AgentThought(
            iteration=1,
            thought_type="observation",
            content="Task completed",
            related_operations=[],
        )

        assert thought.related_operations == []


class TestAgentThoughtImmutability:
    """Test AgentThought immutability."""

    def test_thought_is_immutable(self):
        """Test thought is frozen (immutable)."""
        thought = AgentThought(
            iteration=1,
            thought_type="analysis",
            content="Test thought",
        )

        with pytest.raises(AttributeError):
            thought.content = "New content"  # type: ignore

        with pytest.raises(AttributeError):
            thought.confidence = 0.9  # type: ignore


class TestAgentThoughtEquality:
    """Test AgentThought equality and comparison."""

    def test_thoughts_with_same_values_are_equal(self):
        """Test thoughts with identical values are equal."""
        thought1 = AgentThought(
            iteration=1,
            thought_type="analysis",
            content="Test thought",
            related_operations=["op1"],
            confidence=0.8,
        )
        thought2 = AgentThought(
            iteration=1,
            thought_type="analysis",
            content="Test thought",
            related_operations=["op1"],
            confidence=0.8,
        )

        assert thought1 == thought2

    def test_thoughts_with_different_iterations_are_not_equal(self):
        """Test thoughts with different iterations are not equal."""
        thought1 = AgentThought(iteration=1, thought_type="analysis", content="Test")
        thought2 = AgentThought(iteration=2, thought_type="analysis", content="Test")

        assert thought1 != thought2

