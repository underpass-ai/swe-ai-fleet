"""Unit tests for UpdateTaskStatusUseCase."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from core.context.domain.graph_label import GraphLabel
from core.context.usecases.update_task_status import UpdateTaskStatusUseCase


class TestUpdateTaskStatusUseCase:
    """Unit tests for UpdateTaskStatusUseCase."""

    @pytest.mark.parametrize(
        "status",
        [
            "in_progress",
            "completed",
            "failed",
            "blocked",
            "todo",
        ],
    )
    def test_execute_updates_task_status(self, status: str) -> None:
        """Test that execute updates task status correctly for all valid statuses."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateTaskStatusUseCase(writer=mock_writer)

        payload = {
            "task_id": "TASK-001",
            "status": status,
        }

        # Act
        use_case.execute(payload)

        # Assert
        mock_writer.update_node_properties.assert_called_once()
        call_args = mock_writer.update_node_properties.call_args

        # Verify label is TASK
        assert call_args.kwargs["label"] == GraphLabel.TASK

        # Verify task ID
        assert call_args.kwargs["node_id"] == "TASK-001"

        # Verify properties contain status
        properties = call_args.kwargs["properties"]
        assert "status" in properties
        assert properties["status"] == status

    def test_execute_with_different_task_ids(self) -> None:
        """Test that execute works with different task IDs."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateTaskStatusUseCase(writer=mock_writer)

        task_ids = ["TASK-001", "TASK-123", "TASK-ABC", "TASK-999"]

        for task_id in task_ids:
            mock_writer.reset_mock()

            payload = {
                "task_id": task_id,
                "status": "in_progress",
            }

            # Act
            use_case.execute(payload)

            # Assert
            mock_writer.update_node_properties.assert_called_once()
            call_args = mock_writer.update_node_properties.call_args
            assert call_args.kwargs["node_id"] == task_id

    def test_execute_transitions_queued_to_in_progress(self) -> None:
        """Test typical transition from QUEUED to IN_PROGRESS."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateTaskStatusUseCase(writer=mock_writer)

        # Act - First call: todo
        use_case.execute({"task_id": "TASK-001", "status": "todo"})

        # Act - Second call: in_progress
        use_case.execute({"task_id": "TASK-001", "status": "in_progress"})

        # Assert - Both calls should have been made
        assert mock_writer.update_node_properties.call_count == 2

        # Verify final call had in_progress status
        final_call = mock_writer.update_node_properties.call_args
        properties = final_call.kwargs["properties"]
        assert properties["status"] == "in_progress"

    def test_execute_transitions_in_progress_to_completed(self) -> None:
        """Test typical transition from IN_PROGRESS to COMPLETED."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateTaskStatusUseCase(writer=mock_writer)

        # Act
        use_case.execute({"task_id": "TASK-001", "status": "in_progress"})
        use_case.execute({"task_id": "TASK-001", "status": "completed"})

        # Assert
        assert mock_writer.update_node_properties.call_count == 2
        final_call = mock_writer.update_node_properties.call_args
        properties = final_call.kwargs["properties"]
        assert properties["status"] == "completed"

    def test_execute_handles_failed_status(self) -> None:
        """Test that execute handles FAILED status correctly."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateTaskStatusUseCase(writer=mock_writer)

        payload = {
            "task_id": "TASK-FAILED",
            "status": "failed",
        }

        # Act
        use_case.execute(payload)

        # Assert
        mock_writer.update_node_properties.assert_called_once()
        call_args = mock_writer.update_node_properties.call_args
        properties = call_args.kwargs["properties"]
        assert properties["status"] == "failed"

    def test_execute_with_plan_id(self) -> None:
        """Test that execute works with optional plan_id."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateTaskStatusUseCase(writer=mock_writer)

        payload = {
            "task_id": "TASK-001",
            "status": "in_progress",
            "plan_id": "PLAN-123",
        }

        # Act
        use_case.execute(payload)

        # Assert
        mock_writer.update_node_properties.assert_called_once()
        call_args = mock_writer.update_node_properties.call_args
        assert call_args.kwargs["node_id"] == "TASK-001"

