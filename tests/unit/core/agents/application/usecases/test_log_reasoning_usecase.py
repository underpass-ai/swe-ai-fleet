"""Unit tests for LogReasoningUseCase."""

import pytest

from core.agents_and_tools.agents.application.usecases.log_reasoning_usecase import (
    LogReasoningUseCase,
)
from core.agents_and_tools.agents.domain.entities import ReasoningLogs


class TestLogReasoningUseCase:
    """Unit tests for LogReasoningUseCase."""

    def test_log_thought_happy_path(self):
        """Test logging a thought successfully."""
        # Arrange
        use_case = LogReasoningUseCase(
            agent_id="agent-123",
            role="DEV",
        )

        reasoning_log = ReasoningLogs()

        # Act
        use_case.execute(
            reasoning_log=reasoning_log,
            iteration=1,
            thought_type="analysis",
            content="Analyzing task requirements",
            related_operations=["git.status", "files.read_file"],
            confidence=0.8,
        )

        # Assert
        assert reasoning_log.count() == 1
        entry = reasoning_log.get_all()[0]
        assert entry.agent_id == "agent-123"
        assert entry.role == "DEV"
        assert entry.iteration == 1
        assert entry.thought_type == "analysis"
        assert entry.content == "Analyzing task requirements"
        assert len(entry.related_operations) == 2
        assert entry.confidence == 0.8

    def test_log_thought_minimal_required_params(self):
        """Test logging thought with only required parameters."""
        # Arrange
        use_case = LogReasoningUseCase(
            agent_id="agent-123",
            role="DEV",
        )

        reasoning_log = ReasoningLogs()

        # Act
        use_case.execute(
            reasoning_log=reasoning_log,
            iteration=0,
            thought_type="decision",
            content="Decision made",
        )

        # Assert
        assert reasoning_log.count() == 1
        entry = reasoning_log.get_all()[0]
        assert entry.related_operations == []
        assert entry.confidence is None

    def test_log_thought_agent_id_required(self):
        """Test that agent_id is required (fail-fast)."""
        # Act & Assert
        with pytest.raises(ValueError, match="agent_id is required"):
            LogReasoningUseCase(
                agent_id="",
                role="DEV",
            )

    def test_log_thought_role_required(self):
        """Test that role is required (fail-fast)."""
        # Act & Assert
        with pytest.raises(ValueError, match="role is required"):
            LogReasoningUseCase(
                agent_id="agent-123",
                role="",
            )

    def test_execute_reasoning_log_required(self):
        """Test that reasoning_log is required in execute (fail-fast)."""
        # Arrange
        use_case = LogReasoningUseCase(
            agent_id="agent-123",
            role="DEV",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="reasoning_log is required"):
            use_case.execute(
                reasoning_log=None,
                iteration=0,
                thought_type="analysis",
                content="Test",
            )

    def test_execute_thought_type_required(self):
        """Test that thought_type is required in execute (fail-fast)."""
        # Arrange
        use_case = LogReasoningUseCase(
            agent_id="agent-123",
            role="DEV",
        )

        reasoning_log = ReasoningLogs()

        # Act & Assert
        with pytest.raises(ValueError, match="thought_type is required"):
            use_case.execute(
                reasoning_log=reasoning_log,
                iteration=0,
                thought_type="",
                content="Test",
            )

    def test_execute_content_required(self):
        """Test that content is required in execute (fail-fast)."""
        # Arrange
        use_case = LogReasoningUseCase(
            agent_id="agent-123",
            role="DEV",
        )

        reasoning_log = ReasoningLogs()

        # Act & Assert
        with pytest.raises(ValueError, match="content is required"):
            use_case.execute(
                reasoning_log=reasoning_log,
                iteration=0,
                thought_type="analysis",
                content="",
            )

