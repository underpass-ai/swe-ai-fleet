"""Tests for DeliberationTrackerPort interface and related exceptions."""

import pytest

from services.orchestrator.domain.ports import DeliberationNotFoundError


class TestDeliberationNotFoundError:
    """Test suite for DeliberationNotFoundError."""
    
    def test_create_error(self):
        """Test creating DeliberationNotFoundError."""
        error = DeliberationNotFoundError("task-001")
        
        assert "task-001" in str(error)
        assert "not found" in str(error).lower()
        assert error.task_id == "task-001"
    
    def test_error_is_exception(self):
        """Test that error is a proper Exception."""
        error = DeliberationNotFoundError("task-002")
        
        assert isinstance(error, Exception)
    
    def test_can_raise_and_catch(self):
        """Test that error can be raised and caught."""
        with pytest.raises(DeliberationNotFoundError) as exc_info:
            raise DeliberationNotFoundError("task-003")
        
        assert exc_info.value.task_id == "task-003"
    
    def test_different_task_ids(self):
        """Test error with different task IDs."""
        error1 = DeliberationNotFoundError("task-aaa")
        error2 = DeliberationNotFoundError("task-bbb")
        
        assert error1.task_id == "task-aaa"
        assert error2.task_id == "task-bbb"
        assert "task-aaa" in str(error1)
        assert "task-bbb" in str(error2)

