"""Unit tests for ReasoningLogEntry domain entity."""

import pytest
from datetime import datetime
from core.agents_and_tools.agents.domain.entities.collections.reasoning_log import ReasoningLogEntry


class TestReasoningLogEntryCreation:
    """Test ReasoningLogEntry entity creation."""

    def test_create_entry_with_required_fields(self):
        """Test creating entry with required fields."""
        timestamp = datetime.now()

        entry = ReasoningLogEntry(
            agent_id="agent-001",
            role="developer",
            iteration=1,
            thought_type="analysis",
            content="I need to analyze the codebase",
            related_operations=["files.read_file"],
            confidence=0.8,
            timestamp=timestamp,
        )

        assert entry.agent_id == "agent-001"
        assert entry.role == "developer"
        assert entry.iteration == 1
        assert entry.thought_type == "analysis"
        assert entry.content == "I need to analyze the codebase"
        assert entry.related_operations == ["files.read_file"]
        assert entry.confidence == 0.8
        assert entry.timestamp == timestamp

    def test_create_entry_with_minimal_fields(self):
        """Test creating entry with minimal required fields."""
        timestamp = datetime.now()

        entry = ReasoningLogEntry(
            agent_id="agent-001",
            role="developer",
            iteration=1,
            thought_type="decision",
            content="I will proceed with the task",
            related_operations=[],
            confidence=None,
            timestamp=timestamp,
        )

        assert entry.related_operations == []
        assert entry.confidence is None


class TestReasoningLogEntryImmutability:
    """Test ReasoningLogEntry immutability."""

    def test_entry_is_immutable(self):
        """Test entry is frozen (immutable)."""
        timestamp = datetime.now()
        entry = ReasoningLogEntry(
            agent_id="agent-001",
            role="developer",
            iteration=1,
            thought_type="analysis",
            content="Test",
            related_operations=[],
            confidence=None,
            timestamp=timestamp,
        )

        with pytest.raises(AttributeError):
            entry.content = "New content"  # type: ignore

        with pytest.raises(AttributeError):
            entry.confidence = 0.9  # type: ignore

