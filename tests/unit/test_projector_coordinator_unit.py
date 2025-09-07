# tests/unit/test_projector_coordinator_unit.py
from __future__ import annotations

from unittest.mock import Mock

import pytest

from swe_ai_fleet.context.usecases.projector_coordinator import ProjectorCoordinator


class TestProjectorCoordinator:
    """Unit tests for ProjectorCoordinator."""

    def test_init_sets_up_handlers(self):
        """Test that __post_init__ sets up all event handlers."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        # Check that all expected handlers are registered
        expected_events = {
            "case.created",
            "plan.versioned", 
            "subtask.created",
            "subtask.status_changed",
            "decision.made"
        }
        
        assert set(coordinator.handlers.keys()) == expected_events
        
        # All handlers should be callable
        for handler in coordinator.handlers.values():
            assert callable(handler)

    def test_handle_case_created(self):
        """Test handling case.created event."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        payload = {"case_id": "CASE-001", "name": "Test Case"}
        result = coordinator.handle("case.created", payload)
        
        assert result is True
        mock_writer.upsert_entity.assert_called_once_with(
            "Case", "CASE-001", {"name": "Test Case"}
        )

    def test_handle_plan_versioned(self):
        """Test handling plan.versioned event."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        payload = {
            "case_id": "CASE-001",
            "plan_id": "PLAN-001", 
            "version": 2
        }
        result = coordinator.handle("plan.versioned", payload)
        
        assert result is True
        mock_writer.upsert_entity.assert_called_once_with(
            "PlanVersion", "PLAN-001", {"version": 2}
        )
        mock_writer.relate.assert_called_once_with(
            "CASE-001", "HAS_PLAN", "PLAN-001",
            src_labels=["Case"], dst_labels=["PlanVersion"]
        )

    def test_handle_subtask_created(self):
        """Test handling subtask.created event."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        payload = {
            "plan_id": "PLAN-001",
            "sub_id": "SUB-001",
            "title": "Implement feature",
            "type": "development"
        }
        result = coordinator.handle("subtask.created", payload)
        
        assert result is True
        mock_writer.upsert_entity.assert_called_once_with(
            "Subtask", "SUB-001", 
            {"title": "Implement feature", "type": "development"}
        )
        mock_writer.relate.assert_called_once_with(
            "PLAN-001", "HAS_SUBTASK", "SUB-001",
            src_labels=["PlanVersion"], dst_labels=["Subtask"]
        )

    def test_handle_subtask_status_changed(self):
        """Test handling subtask.status_changed event."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        payload = {
            "sub_id": "SUB-001",
            "status": "completed"
        }
        result = coordinator.handle("subtask.status_changed", payload)
        
        assert result is True
        mock_writer.upsert_entity.assert_called_once_with(
            "Subtask", "SUB-001", {"last_status": "completed"}
        )

    def test_handle_decision_made(self):
        """Test handling decision.made event."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-001",
            "kind": "architecture",
            "summary": "Use microservices",
            "sub_id": "SUB-001"
        }
        result = coordinator.handle("decision.made", payload)
        
        assert result is True
        mock_writer.upsert_entity.assert_called_once_with(
            "Decision", "DEC-001", 
            {"kind": "architecture", "summary": "Use microservices"}
        )
        mock_writer.relate.assert_called_once_with(
            "DEC-001", "AFFECTS", "SUB-001",
            src_labels=["Decision"], dst_labels=["Subtask"]
        )

    def test_handle_unknown_event(self):
        """Test handling unknown event type."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        payload = {"some": "data"}
        result = coordinator.handle("unknown.event", payload)
        
        assert result is False
        # No methods should be called on the writer
        mock_writer.assert_not_called()

    def test_handle_with_empty_payload(self):
        """Test handling events with empty payload."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        # This should raise KeyError due to missing required fields
        with pytest.raises(KeyError):
            coordinator.handle("case.created", {})

    def test_handle_with_minimal_payload(self):
        """Test handling events with minimal required payload."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        # Test with minimal required fields
        payload = {"case_id": "CASE-001"}
        result = coordinator.handle("case.created", payload)
        
        assert result is True
        mock_writer.upsert_entity.assert_called_once_with(
            "Case", "CASE-001", {"name": ""}
        )

    def test_handle_decision_made_without_sub_id(self):
        """Test handling decision.made event without sub_id."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-001",
            "kind": "design",
            "summary": "Use REST API"
        }
        result = coordinator.handle("decision.made", payload)
        
        assert result is True
        mock_writer.upsert_entity.assert_called_once_with(
            "Decision", "DEC-001", 
            {"kind": "design", "summary": "Use REST API"}
        )
        # Should not create relationship when sub_id is missing
        mock_writer.relate.assert_not_called()

    def test_handle_plan_versioned_with_string_version(self):
        """Test handling plan.versioned event with string version."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        payload = {
            "case_id": "CASE-001",
            "plan_id": "PLAN-001",
            "version": "3"  # String version
        }
        result = coordinator.handle("plan.versioned", payload)
        
        assert result is True
        # Should convert string to int
        mock_writer.upsert_entity.assert_called_once_with(
            "PlanVersion", "PLAN-001", {"version": 3}
        )

    def test_handle_subtask_created_with_defaults(self):
        """Test handling subtask.created event with default values."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        payload = {
            "plan_id": "PLAN-001",
            "sub_id": "SUB-001"
            # No title or type provided
        }
        result = coordinator.handle("subtask.created", payload)
        
        assert result is True
        mock_writer.upsert_entity.assert_called_once_with(
            "Subtask", "SUB-001", 
            {"title": "", "type": "task"}
        )

    def test_handle_subtask_status_changed_with_none_status(self):
        """Test handling subtask.status_changed event with None status."""
        mock_writer = Mock()
        coordinator = ProjectorCoordinator(writer=mock_writer)
        
        payload = {
            "sub_id": "SUB-001",
            "status": None
        }
        result = coordinator.handle("subtask.status_changed", payload)
        
        assert result is True
        mock_writer.upsert_entity.assert_called_once_with(
            "Subtask", "SUB-001", {"last_status": None}
        )
