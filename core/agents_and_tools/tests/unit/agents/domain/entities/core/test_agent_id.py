"""Unit tests for AgentId value object."""

import pytest
from core.agents_and_tools.agents.domain.entities.core.agent_id import AgentId


class TestAgentIdCreation:
    """Test AgentId entity creation."""

    def test_create_agent_id_with_valid_value(self):
        """Test creating agent ID with valid value."""
        agent_id = AgentId(value="agent-dev-001")

        assert agent_id.value == "agent-dev-001"
        assert isinstance(agent_id.value, str)

    def test_create_agent_id_with_different_formats(self):
        """Test creating agent ID with different formats."""
        agent_id1 = AgentId(value="agent-arch-001")
        assert agent_id1.value == "agent-arch-001"

        agent_id2 = AgentId(value="agent_001")
        assert agent_id2.value == "agent_001"

        agent_id3 = AgentId(value="my-agent-123")
        assert agent_id3.value == "my-agent-123"


class TestAgentIdValidation:
    """Test AgentId validation."""

    def test_agent_id_raises_error_on_empty_string(self):
        """Test agent ID raises error on empty string."""
        with pytest.raises(ValueError, match="AgentId cannot be empty"):
            AgentId(value="")

    def test_agent_id_accepts_whitespace_only(self):
        """Test agent ID accepts whitespace only (validation only checks empty, not whitespace)."""
        # Note: Current implementation only checks for empty string, not whitespace
        agent_id = AgentId(value="   ")
        assert agent_id.value == "   "


class TestAgentIdImmutability:
    """Test AgentId immutability."""

    def test_agent_id_is_immutable(self):
        """Test agent ID is frozen (immutable)."""
        agent_id = AgentId(value="agent-dev-001")

        with pytest.raises(AttributeError):
            agent_id.value = "new-id"  # type: ignore


class TestAgentIdStringRepresentation:
    """Test AgentId string representation."""

    def test_str_returns_value(self):
        """Test __str__ returns the value."""
        agent_id = AgentId(value="agent-dev-001")

        assert str(agent_id) == "agent-dev-001"

    def test_str_representation_for_logging(self):
        """Test string representation is suitable for logging."""
        agent_id = AgentId(value="agent-arch-002")

        log_message = f"Agent {agent_id} started"
        assert "agent-arch-002" in log_message


class TestAgentIdEquality:
    """Test AgentId equality and comparison."""

    def test_agent_ids_with_same_value_are_equal(self):
        """Test agent IDs with identical values are equal."""
        agent_id1 = AgentId(value="agent-dev-001")
        agent_id2 = AgentId(value="agent-dev-001")

        assert agent_id1 == agent_id2

    def test_agent_ids_with_different_values_are_not_equal(self):
        """Test agent IDs with different values are not equal."""
        agent_id1 = AgentId(value="agent-dev-001")
        agent_id2 = AgentId(value="agent-dev-002")

        assert agent_id1 != agent_id2

