"""Tests for Ray Executor Mapper."""

from unittest.mock import MagicMock, patch

from services.orchestrator.domain.entities import DeliberationStatus, DeliberationSubmission
from services.orchestrator.infrastructure.mappers.ray_executor_mapper import (
    RayExecutorMapper,
)


class TestRayExecutorMapper:
    """Test suite for RayExecutorMapper."""

    def test_to_execute_request(self):
        """Test converting domain objects to ExecuteDeliberationRequest."""
        # Arrange
        task_id = "task-123"
        task_description = "Do something"
        role = "developer"
        agents = [
            {"id": "agent-1", "role": "coder", "model": "gpt-4"},
            {"id": "agent-2", "role": "reviewer"},  # Missing model, should use default
        ]
        constraints = {
            "story_id": "story-1",
            "timeout": 600,
        }
        vllm_url = "http://localhost:8000"
        vllm_model = "default-model"

        # Mock the protobuf module imported in the mapper
        with patch(
            "services.orchestrator.infrastructure.mappers."
            "ray_executor_mapper.ray_executor_pb2"
        ) as mock_pb2:
            # Act
            RayExecutorMapper.to_execute_request(
                task_id,
                task_description,
                role,
                agents,
                constraints,
                vllm_url,
                vllm_model,
            )

            # Assert
            # Check that ExecuteDeliberationRequest was instantiated
            mock_pb2.ExecuteDeliberationRequest.assert_called_once()
            _, kwargs = mock_pb2.ExecuteDeliberationRequest.call_args

            assert kwargs["task_id"] == task_id
            assert kwargs["task_description"] == task_description
            assert kwargs["role"] == role
            assert kwargs["vllm_url"] == vllm_url
            assert kwargs["vllm_model"] == vllm_model

            # Check agents creation
            assert mock_pb2.Agent.call_count == 2

            # Check constraints creation
            mock_pb2.TaskConstraints.assert_called_once()
            _, constraints_kwargs = mock_pb2.TaskConstraints.call_args
            assert constraints_kwargs["story_id"] == "story-1"
            assert constraints_kwargs["timeout_seconds"] == 600
            # Check default
            assert constraints_kwargs["max_retries"] == 3

    def test_to_deliberation_submission(self):
        """Test converting response to DeliberationSubmission."""
        # Arrange
        mock_response = MagicMock()
        mock_response.deliberation_id = "delib-123"
        mock_response.status = "PENDING"
        mock_response.message = "Submitted"

        # Act
        submission = RayExecutorMapper.to_deliberation_submission(mock_response)

        # Assert
        assert isinstance(submission, DeliberationSubmission)
        assert submission.deliberation_id == "delib-123"
        assert submission.status == "PENDING"
        assert submission.message == "Submitted"

    def test_to_get_status_request(self):
        """Test creating GetDeliberationStatusRequest."""
        # Arrange
        deliberation_id = "delib-123"

        with patch(
            "services.orchestrator.infrastructure.mappers."
            "ray_executor_mapper.ray_executor_pb2"
        ) as mock_pb2:
            # Act
            RayExecutorMapper.to_get_status_request(deliberation_id)

            # Assert
            mock_pb2.GetDeliberationStatusRequest.assert_called_once_with(
                deliberation_id=deliberation_id
            )

    def test_to_deliberation_status_with_result(self):
        """Test converting status response with result."""
        # Arrange
        deliberation_id = "delib-123"
        mock_response = MagicMock()
        mock_response.status = "COMPLETED"
        mock_response.HasField.return_value = True
        mock_response.result = "Result data"
        mock_response.error_message = ""

        # Act
        status = RayExecutorMapper.to_deliberation_status(deliberation_id, mock_response)

        # Assert
        assert isinstance(status, DeliberationStatus)
        assert status.deliberation_id == deliberation_id
        assert status.status == "COMPLETED"
        assert status.result == "Result data"
        assert status.error_message is None
        mock_response.HasField.assert_called_with("result")

    def test_to_deliberation_status_failed(self):
        """Test converting status response with error."""
        # Arrange
        deliberation_id = "delib-123"
        mock_response = MagicMock()
        mock_response.status = "FAILED"
        mock_response.HasField.return_value = False
        mock_response.error_message = "Something went wrong"

        # Act
        status = RayExecutorMapper.to_deliberation_status(deliberation_id, mock_response)

        # Assert
        assert isinstance(status, DeliberationStatus)
        assert status.deliberation_id == deliberation_id
        assert status.status == "FAILED"
        assert status.result is None
        assert status.error_message == "Something went wrong"
