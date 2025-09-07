# tests/unit/test_context_usecases_unit.py
from __future__ import annotations

from unittest.mock import Mock

import pytest

from swe_ai_fleet.context.usecases.project_case import ProjectCaseUseCase
from swe_ai_fleet.context.usecases.project_decision import ProjectDecisionUseCase
from swe_ai_fleet.context.usecases.project_plan_version import ProjectPlanVersionUseCase
from swe_ai_fleet.context.usecases.project_subtask import ProjectSubtaskUseCase
from swe_ai_fleet.context.usecases.update_subtask_status import UpdateSubtaskStatusUseCase


class TestProjectCaseUseCase:
    """Unit tests for ProjectCaseUseCase."""

    def test_execute_with_name(self):
        """Test execute method with name provided."""
        mock_writer = Mock()
        usecase = ProjectCaseUseCase(writer=mock_writer)
        
        payload = {"case_id": "CASE-001", "name": "Test Case"}
        usecase.execute(payload)
        
        mock_writer.upsert_entity.assert_called_once_with(
            "Case", "CASE-001", {"name": "Test Case"}
        )

    def test_execute_without_name(self):
        """Test execute method without name (uses default)."""
        mock_writer = Mock()
        usecase = ProjectCaseUseCase(writer=mock_writer)
        
        payload = {"case_id": "CASE-001"}
        usecase.execute(payload)
        
        mock_writer.upsert_entity.assert_called_once_with(
            "Case", "CASE-001", {"name": ""}
        )

    def test_execute_with_empty_name(self):
        """Test execute method with empty name."""
        mock_writer = Mock()
        usecase = ProjectCaseUseCase(writer=mock_writer)
        
        payload = {"case_id": "CASE-001", "name": ""}
        usecase.execute(payload)
        
        mock_writer.upsert_entity.assert_called_once_with(
            "Case", "CASE-001", {"name": ""}
        )

    def test_execute_missing_case_id(self):
        """Test execute method raises KeyError when case_id is missing."""
        mock_writer = Mock()
        usecase = ProjectCaseUseCase(writer=mock_writer)
        
        payload = {"name": "Test Case"}
        
        with pytest.raises(KeyError):
            usecase.execute(payload)


class TestProjectDecisionUseCase:
    """Unit tests for ProjectDecisionUseCase."""

    def test_execute_with_all_fields(self):
        """Test execute method with all fields provided."""
        mock_writer = Mock()
        usecase = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-001",
            "kind": "architecture",
            "summary": "Use microservices",
            "sub_id": "SUB-001"
        }
        usecase.execute(payload)
        
        # Should upsert the decision entity
        mock_writer.upsert_entity.assert_called_once_with(
            "Decision", "DEC-001", 
            {"kind": "architecture", "summary": "Use microservices"}
        )
        
        # Should create relationship to subtask
        mock_writer.relate.assert_called_once_with(
            "DEC-001", "AFFECTS", "SUB-001",
            src_labels=["Decision"], dst_labels=["Subtask"]
        )

    def test_execute_without_optional_fields(self):
        """Test execute method without optional fields."""
        mock_writer = Mock()
        usecase = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {"node_id": "DEC-001"}
        usecase.execute(payload)
        
        # Should upsert with default values
        mock_writer.upsert_entity.assert_called_once_with(
            "Decision", "DEC-001", 
            {"kind": "", "summary": ""}
        )
        
        # Should not create relationship
        mock_writer.relate.assert_not_called()

    def test_execute_without_sub_id(self):
        """Test execute method without sub_id (no relationship created)."""
        mock_writer = Mock()
        usecase = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-001",
            "kind": "design",
            "summary": "Use REST API"
        }
        usecase.execute(payload)
        
        mock_writer.upsert_entity.assert_called_once()
        mock_writer.relate.assert_not_called()

    def test_execute_missing_node_id(self):
        """Test execute method raises KeyError when node_id is missing."""
        mock_writer = Mock()
        usecase = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {"kind": "architecture", "summary": "Use microservices"}
        
        with pytest.raises(KeyError):
            usecase.execute(payload)


class TestProjectPlanVersionUseCase:
    """Unit tests for ProjectPlanVersionUseCase."""

    def test_execute_with_version(self):
        """Test execute method with version provided."""
        mock_writer = Mock()
        usecase = ProjectPlanVersionUseCase(writer=mock_writer)
        
        payload = {
            "case_id": "CASE-001",
            "plan_id": "PLAN-001",
            "version": 2
        }
        usecase.execute(payload)
        
        # Should upsert the plan version entity
        mock_writer.upsert_entity.assert_called_once_with(
            "PlanVersion", "PLAN-001", {"version": 2}
        )
        
        # Should create relationship from case to plan
        mock_writer.relate.assert_called_once_with(
            "CASE-001", "HAS_PLAN", "PLAN-001",
            src_labels=["Case"], dst_labels=["PlanVersion"]
        )

    def test_execute_without_version(self):
        """Test execute method without version (uses default)."""
        mock_writer = Mock()
        usecase = ProjectPlanVersionUseCase(writer=mock_writer)
        
        payload = {
            "case_id": "CASE-001",
            "plan_id": "PLAN-001"
        }
        usecase.execute(payload)
        
        # Should upsert with default version
        mock_writer.upsert_entity.assert_called_once_with(
            "PlanVersion", "PLAN-001", {"version": 1}
        )
        
        mock_writer.relate.assert_called_once()

    def test_execute_with_string_version(self):
        """Test execute method with string version (converted to int)."""
        mock_writer = Mock()
        usecase = ProjectPlanVersionUseCase(writer=mock_writer)
        
        payload = {
            "case_id": "CASE-001",
            "plan_id": "PLAN-001",
            "version": "3"
        }
        usecase.execute(payload)
        
        # Should convert string to int
        mock_writer.upsert_entity.assert_called_once_with(
            "PlanVersion", "PLAN-001", {"version": 3}
        )

    def test_execute_missing_required_fields(self):
        """Test execute method raises KeyError when required fields are missing."""
        mock_writer = Mock()
        usecase = ProjectPlanVersionUseCase(writer=mock_writer)
        
        # Missing case_id
        payload = {"plan_id": "PLAN-001", "version": 1}
        with pytest.raises(KeyError):
            usecase.execute(payload)
        
        # Missing plan_id
        payload = {"case_id": "CASE-001", "version": 1}
        with pytest.raises(KeyError):
            usecase.execute(payload)


class TestProjectSubtaskUseCase:
    """Unit tests for ProjectSubtaskUseCase."""

    def test_execute_with_all_fields(self):
        """Test execute method with all fields provided."""
        mock_writer = Mock()
        usecase = ProjectSubtaskUseCase(writer=mock_writer)
        
        payload = {
            "plan_id": "PLAN-001",
            "sub_id": "SUB-001",
            "title": "Implement feature",
            "type": "development"
        }
        usecase.execute(payload)
        
        # Should upsert the subtask entity
        mock_writer.upsert_entity.assert_called_once_with(
            "Subtask", "SUB-001", 
            {"title": "Implement feature", "type": "development"}
        )
        
        # Should create relationship from plan to subtask
        mock_writer.relate.assert_called_once_with(
            "PLAN-001", "HAS_SUBTASK", "SUB-001",
            src_labels=["PlanVersion"], dst_labels=["Subtask"]
        )

    def test_execute_without_optional_fields(self):
        """Test execute method without optional fields."""
        mock_writer = Mock()
        usecase = ProjectSubtaskUseCase(writer=mock_writer)
        
        payload = {
            "plan_id": "PLAN-001",
            "sub_id": "SUB-001"
        }
        usecase.execute(payload)
        
        # Should upsert with default values
        mock_writer.upsert_entity.assert_called_once_with(
            "Subtask", "SUB-001", 
            {"title": "", "type": "task"}
        )
        
        mock_writer.relate.assert_called_once()

    def test_execute_with_empty_title(self):
        """Test execute method with empty title."""
        mock_writer = Mock()
        usecase = ProjectSubtaskUseCase(writer=mock_writer)
        
        payload = {
            "plan_id": "PLAN-001",
            "sub_id": "SUB-001",
            "title": "",
            "type": "testing"
        }
        usecase.execute(payload)
        
        mock_writer.upsert_entity.assert_called_once_with(
            "Subtask", "SUB-001", 
            {"title": "", "type": "testing"}
        )

    def test_execute_missing_required_fields(self):
        """Test execute method raises KeyError when required fields are missing."""
        mock_writer = Mock()
        usecase = ProjectSubtaskUseCase(writer=mock_writer)
        
        # Missing plan_id
        payload = {"sub_id": "SUB-001", "title": "Test"}
        with pytest.raises(KeyError):
            usecase.execute(payload)
        
        # Missing sub_id
        payload = {"plan_id": "PLAN-001", "title": "Test"}
        with pytest.raises(KeyError):
            usecase.execute(payload)


class TestUpdateSubtaskStatusUseCase:
    """Unit tests for UpdateSubtaskStatusUseCase."""

    def test_execute_with_status(self):
        """Test execute method with status provided."""
        mock_writer = Mock()
        usecase = UpdateSubtaskStatusUseCase(writer=mock_writer)
        
        payload = {
            "sub_id": "SUB-001",
            "status": "completed"
        }
        usecase.execute(payload)
        
        mock_writer.upsert_entity.assert_called_once_with(
            "Subtask", "SUB-001", {"last_status": "completed"}
        )

    def test_execute_without_status(self):
        """Test execute method without status (uses None)."""
        mock_writer = Mock()
        usecase = UpdateSubtaskStatusUseCase(writer=mock_writer)
        
        payload = {"sub_id": "SUB-001"}
        usecase.execute(payload)
        
        mock_writer.upsert_entity.assert_called_once_with(
            "Subtask", "SUB-001", {"last_status": None}
        )

    def test_execute_with_none_status(self):
        """Test execute method with explicit None status."""
        mock_writer = Mock()
        usecase = UpdateSubtaskStatusUseCase(writer=mock_writer)
        
        payload = {
            "sub_id": "SUB-001",
            "status": None
        }
        usecase.execute(payload)
        
        mock_writer.upsert_entity.assert_called_once_with(
            "Subtask", "SUB-001", {"last_status": None}
        )

    def test_execute_missing_sub_id(self):
        """Test execute method raises KeyError when sub_id is missing."""
        mock_writer = Mock()
        usecase = UpdateSubtaskStatusUseCase(writer=mock_writer)
        
        payload = {"status": "in_progress"}
        
        with pytest.raises(KeyError):
            usecase.execute(payload)
