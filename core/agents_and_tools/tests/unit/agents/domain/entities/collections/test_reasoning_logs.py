"""Unit tests for ReasoningLogs collection."""

from datetime import datetime

from core.agents_and_tools.agents.domain.entities.collections.reasoning_logs import ReasoningLogs


class TestReasoningLogsCreation:
    """Test ReasoningLogs collection creation."""

    def test_create_empty_logs(self):
        """Test creating empty reasoning logs collection."""
        logs = ReasoningLogs()

        assert logs.entries == []
        assert logs.count() == 0


class TestReasoningLogsAdd:
    """Test ReasoningLogs.add() method."""

    def test_add_entry_with_required_fields(self):
        """Test adding entry with required fields."""
        logs = ReasoningLogs()

        logs.add(
            agent_id="agent-001",
            role="developer",
            iteration=1,
            thought_type="analysis",
            content="I need to analyze the codebase",
        )

        assert logs.count() == 1
        entry = logs.entries[0]
        assert entry.agent_id == "agent-001"
        assert entry.role == "developer"
        assert entry.iteration == 1
        assert entry.thought_type == "analysis"
        assert entry.related_operations == []
        assert entry.confidence is None

    def test_add_entry_with_all_fields(self):
        """Test adding entry with all fields."""
        logs = ReasoningLogs()

        logs.add(
            agent_id="agent-001",
            role="developer",
            iteration=1,
            thought_type="decision",
            content="I will use files tool",
            related_operations=["files.read_file"],
            confidence=0.85,
        )

        entry = logs.entries[0]
        assert entry.related_operations == ["files.read_file"]
        assert entry.confidence == 0.85

    def test_add_entry_creates_timestamp(self):
        """Test that add() creates a timestamp for the entry."""
        logs = ReasoningLogs()
        before = datetime.now()

        logs.add(
            agent_id="agent-001",
            role="developer",
            iteration=1,
            thought_type="analysis",
            content="Test",
        )

        after = datetime.now()
        entry = logs.entries[0]
        assert before <= entry.timestamp <= after


class TestReasoningLogsGetAll:
    """Test ReasoningLogs.get_all() method."""

    def test_get_all_returns_all_entries(self):
        """Test get_all returns all entries."""
        logs = ReasoningLogs()

        logs.add(agent_id="agent-001", role="developer", iteration=1, thought_type="analysis", content="Test 1")
        logs.add(agent_id="agent-001", role="developer", iteration=2, thought_type="decision", content="Test 2")

        all_entries = logs.get_all()

        assert len(all_entries) == 2


class TestReasoningLogsGetByThoughtType:
    """Test ReasoningLogs.get_by_thought_type() method."""

    def test_get_by_thought_type_returns_matching_entries(self):
        """Test get_by_thought_type returns entries with specific type."""
        logs = ReasoningLogs()

        logs.add(agent_id="agent-001", role="developer", iteration=1, thought_type="analysis", content="Test 1")
        logs.add(agent_id="agent-001", role="developer", iteration=2, thought_type="decision", content="Test 2")
        logs.add(agent_id="agent-001", role="developer", iteration=3, thought_type="analysis", content="Test 3")

        analysis_entries = logs.get_by_thought_type("analysis")

        assert len(analysis_entries) == 2
        assert all(entry.thought_type == "analysis" for entry in analysis_entries)


class TestReasoningLogsGetByIteration:
    """Test ReasoningLogs.get_by_iteration() method."""

    def test_get_by_iteration_returns_matching_entries(self):
        """Test get_by_iteration returns entries for specific iteration."""
        logs = ReasoningLogs()

        logs.add(agent_id="agent-001", role="developer", iteration=1, thought_type="analysis", content="Test 1")
        logs.add(agent_id="agent-001", role="developer", iteration=2, thought_type="decision", content="Test 2")
        logs.add(agent_id="agent-001", role="developer", iteration=2, thought_type="observation", content="Test 3")

        iteration_2_entries = logs.get_by_iteration(2)

        assert len(iteration_2_entries) == 2
        assert all(entry.iteration == 2 for entry in iteration_2_entries)


class TestReasoningLogsGetLastN:
    """Test ReasoningLogs.get_last_n() method."""

    def test_get_last_n_returns_last_n_entries(self):
        """Test get_last_n returns last n entries."""
        logs = ReasoningLogs()

        for i in range(5):
            logs.add(
                agent_id="agent-001",
                role="developer",
                iteration=i + 1,
                thought_type="analysis",
                content=f"Test {i+1}",
            )

        last_3 = logs.get_last_n(3)

        assert len(last_3) == 3
        assert last_3[0].iteration == 3

    def test_get_last_n_returns_all_when_n_exceeds_count(self):
        """Test get_last_n returns all when n exceeds count."""
        logs = ReasoningLogs()
        logs.add(agent_id="agent-001", role="developer", iteration=1, thought_type="analysis", content="Test")

        last_5 = logs.get_last_n(5)

        assert len(last_5) == 1


class TestReasoningLogsCount:
    """Test ReasoningLogs.count() method."""

    def test_count_returns_correct_number(self):
        """Test count returns correct number."""
        logs = ReasoningLogs()

        assert logs.count() == 0

        logs.add(agent_id="agent-001", role="developer", iteration=1, thought_type="analysis", content="Test")
        assert logs.count() == 1

