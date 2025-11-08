"""Unit tests for ArtifactCollectionApplicationService."""

from unittest.mock import Mock

import pytest
from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
from core.agents_and_tools.agents.application.services.artifact_collection_service import (
    ArtifactCollectionApplicationService,
)
from core.agents_and_tools.agents.domain.entities import Artifact, ExecutionStep
from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_tool_execution_port():
    """Create mock ToolExecutionPort."""
    return Mock(spec=ToolExecutionPort)


@pytest.fixture
def mock_artifact_mapper():
    """Create mock ArtifactMapper."""
    return Mock(spec=ArtifactMapper)


# =============================================================================
# Constructor Validation Tests
# =============================================================================

class TestArtifactCollectionServiceConstructor:
    """Test constructor fail-fast validation."""

    def test_rejects_missing_tool_execution_port(self, mock_artifact_mapper):
        """Should raise ValueError if tool_execution_port is None."""
        with pytest.raises(ValueError, match="tool_execution_port is required"):
            ArtifactCollectionApplicationService(
                tool_execution_port=None,
                artifact_mapper=mock_artifact_mapper,
            )

    def test_rejects_missing_artifact_mapper(self, mock_tool_execution_port):
        """Should raise ValueError if artifact_mapper is None."""
        with pytest.raises(ValueError, match="artifact_mapper is required"):
            ArtifactCollectionApplicationService(
                tool_execution_port=mock_tool_execution_port,
                artifact_mapper=None,
            )

    def test_accepts_all_required_dependencies(self, mock_tool_execution_port, mock_artifact_mapper):
        """Should create instance when all dependencies are provided."""
        service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )

        assert service.tool_execution_port is mock_tool_execution_port
        assert service.artifact_mapper is mock_artifact_mapper


# =============================================================================
# Collection Tests
# =============================================================================

class TestArtifactCollectionService:
    """Test artifact collection logic."""

    def test_collect_delegates_to_tool_and_mapper(
        self, mock_tool_execution_port, mock_artifact_mapper
    ):
        """Should delegate to tool's collect_artifacts and then to mapper."""
        # Arrange
        tool_mock = Mock()
        raw_artifacts = {"source_code": "/path/to/file.py", "coverage": "85%"}
        tool_mock.collect_artifacts.return_value = raw_artifacts
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        mapped_artifacts = {
            "source_code": Artifact(name="source_code", value="/path/to/file.py", artifact_type="file"),
            "coverage": Artifact(name="coverage", value="85%", artifact_type="metric"),
        }
        mock_artifact_mapper.to_entity_dict.return_value = mapped_artifacts

        service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )

        step = ExecutionStep(tool="files", operation="read_file", params={"path": "file.py"})
        result = StepExecutionDTO(success=True, result=Mock(), error=None)

        # Act
        artifacts = service.collect(step, result)

        # Assert
        assert artifacts == mapped_artifacts
        mock_tool_execution_port.get_tool_by_name.assert_called_once_with("files")
        tool_mock.collect_artifacts.assert_called_once_with("read_file", result.result, {"path": "file.py"})
        mock_artifact_mapper.to_entity_dict.assert_called_once_with(raw_artifacts)

    def test_collect_handles_missing_tool(
        self, mock_tool_execution_port, mock_artifact_mapper
    ):
        """Should return empty dict when tool is not found."""
        # Arrange
        mock_tool_execution_port.get_tool_by_name.return_value = None

        service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )

        step = ExecutionStep(tool="unknown", operation="unknown_op", params={})
        result = StepExecutionDTO(success=True, result=Mock(), error=None)

        # Act
        artifacts = service.collect(step, result)

        # Assert
        assert artifacts == {}
        mock_tool_execution_port.get_tool_by_name.assert_called_once_with("unknown")
        mock_artifact_mapper.to_entity_dict.assert_not_called()

    def test_collect_handles_step_with_no_params(
        self, mock_tool_execution_port, mock_artifact_mapper
    ):
        """Should handle step with no params gracefully."""
        # Arrange
        tool_mock = Mock()
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        mock_artifact_mapper.to_entity_dict.return_value = {}

        service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )

        step = ExecutionStep(tool="git", operation="status", params=None)
        result = StepExecutionDTO(success=True, result=Mock(), error=None)

        # Act
        artifacts = service.collect(step, result)

        # Assert
        assert artifacts == {}
        tool_mock.collect_artifacts.assert_called_once_with("status", result.result, {})

    def test_collect_with_empty_artifacts(
        self, mock_tool_execution_port, mock_artifact_mapper
    ):
        """Should handle tools that return no artifacts."""
        # Arrange
        tool_mock = Mock()
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        mock_artifact_mapper.to_entity_dict.return_value = {}

        service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )

        step = ExecutionStep(tool="shell", operation="run", params={"command": "echo test"})
        result = StepExecutionDTO(success=True, result=Mock(), error=None)

        # Act
        artifacts = service.collect(step, result)

        # Assert
        assert artifacts == {}
        tool_mock.collect_artifacts.assert_called_once()
        mock_artifact_mapper.to_entity_dict.assert_called_once_with({})

    def test_collect_with_multiple_artifacts(
        self, mock_tool_execution_port, mock_artifact_mapper
    ):
        """Should handle multiple artifacts from a single operation."""
        # Arrange
        tool_mock = Mock()
        raw_artifacts = {
            "log_file": "/var/log/app.log",
            "error_count": "3",
            "warning_count": "12",
        }
        tool_mock.collect_artifacts.return_value = raw_artifacts
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        mapped_artifacts = {
            "log_file": Artifact(name="log_file", value="/var/log/app.log", artifact_type="file"),
            "error_count": Artifact(name="error_count", value="3", artifact_type="metric"),
            "warning_count": Artifact(name="warning_count", value="12", artifact_type="metric"),
        }
        mock_artifact_mapper.to_entity_dict.return_value = mapped_artifacts

        service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )

        step = ExecutionStep(tool="logging", operation="analyze", params={"file": "app.log"})
        result = StepExecutionDTO(success=True, result=Mock(), error=None)

        # Act
        artifacts = service.collect(step, result)

        # Assert
        assert len(artifacts) == 3
        assert "log_file" in artifacts
        assert "error_count" in artifacts
        assert "warning_count" in artifacts
        mock_artifact_mapper.to_entity_dict.assert_called_once_with(raw_artifacts)

