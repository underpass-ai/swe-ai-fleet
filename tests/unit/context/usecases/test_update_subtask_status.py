"""Unit tests for UpdateSubtaskStatusUseCase."""

from unittest.mock import Mock

import pytest

from swe_ai_fleet.context.usecases.update_subtask_status import UpdateSubtaskStatusUseCase


class TestUpdateSubtaskStatusUseCase:
    """Unit tests for UpdateSubtaskStatusUseCase."""
    
    @pytest.mark.parametrize("status", [
        "QUEUED",
        "IN_PROGRESS",
        "COMPLETED",
        "FAILED",
        "BLOCKED",
    ])
    def test_execute_updates_subtask_status(self, status):
        """Test that execute updates subtask status correctly for all valid statuses."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateSubtaskStatusUseCase(writer=mock_writer)
        
        payload = {
            "sub_id": "TASK-001",
            "status": status,
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        mock_writer.upsert_entity.assert_called_once()
        call_args = mock_writer.upsert_entity.call_args
        
        # Verify entity type
        assert call_args[0][0] == "Subtask"
        
        # Verify entity ID
        assert call_args[0][1] == "TASK-001"
        
        # Verify status in properties (domain uses 'last_status')
        properties = call_args[0][2]
        assert "last_status" in properties
        assert properties["last_status"] == status
    
    def test_execute_with_different_task_ids(self):
        """Test that execute works with different task IDs."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateSubtaskStatusUseCase(writer=mock_writer)
        
        task_ids = ["TASK-001", "TASK-123", "SUBTASK-ABC", "ST-999"]
        
        for task_id in task_ids:
            mock_writer.reset_mock()
            
            payload = {
                "sub_id": task_id,
                "status": "IN_PROGRESS",
            }
            
            # Act
            use_case.execute(payload)
            
            # Assert
            mock_writer.upsert_entity.assert_called_once()
            call_args = mock_writer.upsert_entity.call_args
            assert call_args[0][1] == task_id
    
    def test_execute_transitions_queued_to_in_progress(self):
        """Test typical transition from QUEUED to IN_PROGRESS."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateSubtaskStatusUseCase(writer=mock_writer)
        
        # Act - First call: QUEUED
        use_case.execute({"sub_id": "TASK-001", "status": "QUEUED"})
        
        # Act - Second call: IN_PROGRESS
        use_case.execute({"sub_id": "TASK-001", "status": "IN_PROGRESS"})
        
        # Assert - Both calls should have been made
        assert mock_writer.upsert_entity.call_count == 2
        
        # Verify final call had IN_PROGRESS status
        final_call = mock_writer.upsert_entity.call_args
        properties = final_call[0][2]
        assert properties["last_status"] == "IN_PROGRESS"
    
    def test_execute_transitions_in_progress_to_completed(self):
        """Test typical transition from IN_PROGRESS to COMPLETED."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateSubtaskStatusUseCase(writer=mock_writer)
        
        # Act
        use_case.execute({"sub_id": "TASK-001", "status": "IN_PROGRESS"})
        use_case.execute({"sub_id": "TASK-001", "status": "COMPLETED"})
        
        # Assert
        assert mock_writer.upsert_entity.call_count == 2
        final_call = mock_writer.upsert_entity.call_args
        properties = final_call[0][2]
        assert properties["last_status"] == "COMPLETED"
    
    def test_execute_handles_failed_status(self):
        """Test that execute handles FAILED status correctly."""
        # Arrange
        mock_writer = Mock()
        use_case = UpdateSubtaskStatusUseCase(writer=mock_writer)
        
        payload = {
            "sub_id": "TASK-FAILED",
            "status": "FAILED",
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        mock_writer.upsert_entity.assert_called_once()
        call_args = mock_writer.upsert_entity.call_args
        properties = call_args[0][2]
        assert properties["last_status"] == "FAILED"

