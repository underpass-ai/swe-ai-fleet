"""Unit tests for CollectArtifactsUseCase."""

from unittest.mock import Mock

import pytest
from core.agents_and_tools.agents.application.usecases.collect_artifacts_usecase import (
    CollectArtifactsUseCase,
)
from core.agents_and_tools.agents.domain.entities import Artifact
from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort


class TestCollectArtifactsUseCase:
    """Unit tests for CollectArtifactsUseCase."""

    def test_collect_artifacts_happy_path(self):
        """Test artifact collection with successful tool execution."""
        # Arrange
        mock_tool = Mock()
        mock_tool.collect_artifacts.return_value = {
            "commit_sha": "abc123",
            "files_changed": ["file1.py", "file2.py"]
        }

        mock_tool_execution_port = Mock(spec=ToolExecutionPort)
        mock_tool_execution_port.get_tool_by_name.return_value = mock_tool

        artifact_mapper = ArtifactMapper()
        use_case = CollectArtifactsUseCase(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=artifact_mapper,
        )

        mock_result = Mock()

        # Act
        artifacts = use_case.execute(
            tool_name="git",
            operation="commit",
            tool_result=mock_result,
            params={"message": "feat: add feature"},
        )

        # Assert
        assert isinstance(artifacts, dict)
        assert len(artifacts) == 2
        assert "commit_sha" in artifacts
        assert "files_changed" in artifacts
        assert isinstance(artifacts["commit_sha"], Artifact)
        assert artifacts["commit_sha"].value == "abc123"

    def test_collect_artifacts_no_tool_found(self):
        """Test artifact collection when tool is not found."""
        # Arrange
        mock_tool_execution_port = Mock(spec=ToolExecutionPort)
        mock_tool_execution_port.get_tool_by_name.return_value = None

        artifact_mapper = ArtifactMapper()
        use_case = CollectArtifactsUseCase(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=artifact_mapper,
        )

        mock_result = Mock()

        # Act
        artifacts = use_case.execute(
            tool_name="unknown_tool",
            operation="unknown_operation",
            tool_result=mock_result,
            params={},
        )

        # Assert
        assert isinstance(artifacts, dict)
        assert len(artifacts) == 0

    def test_collect_artifacts_tool_execution_port_required(self):
        """Test that tool_execution_port is required (fail-fast)."""
        # Act & Assert
        with pytest.raises(ValueError, match="tool_execution_port is required"):
            CollectArtifactsUseCase(
                tool_execution_port=None,
                artifact_mapper=Mock(),
            )

    def test_collect_artifacts_artifact_mapper_required(self):
        """Test that artifact_mapper is required (fail-fast)."""
        # Act & Assert
        with pytest.raises(ValueError, match="artifact_mapper is required"):
            CollectArtifactsUseCase(
                tool_execution_port=Mock(),
                artifact_mapper=None,
            )

