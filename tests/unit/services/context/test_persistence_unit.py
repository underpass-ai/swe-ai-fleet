"""Unit tests for Context Service persistence methods.

Tests verify persistence logic without requiring real Neo4j/Redis infrastructure.
Uses mocks to verify correct method calls.
"""

import json
from unittest.mock import Mock

import pytest


class TestProcessContextChange:
    """Unit tests for _process_context_change method."""
    
    def test_validate_required_fields(self):
        """Test that missing required fields raise ValueError."""
        from services.context.server import ContextServiceServicer
        
        # Create mock servicer
        servicer = Mock(spec=ContextServiceServicer)
        servicer._process_context_change = ContextServiceServicer._process_context_change.__get__(servicer)
        servicer.graph_command = Mock()
        
        # Test missing operation
        change = Mock()
        change.operation = ""
        change.entity_type = "DECISION"
        change.entity_id = "DEC-001"
        
        with pytest.raises(ValueError, match="Missing required fields"):
            servicer._process_context_change(change, "TEST-001")
        
        # Test missing entity_type
        change.operation = "CREATE"
        change.entity_type = ""
        
        with pytest.raises(ValueError, match="Missing required fields"):
            servicer._process_context_change(change, "TEST-001")
        
        # Test missing entity_id
        change.entity_type = "DECISION"
        change.entity_id = ""
        
        with pytest.raises(ValueError, match="Missing required fields"):
            servicer._process_context_change(change, "TEST-001")
    
    def test_parse_json_payload(self):
        """Test that JSON payload is parsed correctly."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._process_context_change = ContextServiceServicer._process_context_change.__get__(servicer)
        servicer._persist_decision_change = Mock()
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "CREATE"
        change.entity_type = "DECISION"
        change.entity_id = "DEC-001"
        change.payload = json.dumps({"title": "Test Decision", "status": "PROPOSED"})
        
        servicer._process_context_change(change, "TEST-001")
        
        # Verify _persist_decision_change was called with parsed payload
        servicer._persist_decision_change.assert_called_once()
        call_args = servicer._persist_decision_change.call_args
        assert call_args[0][0] == "TEST-001"
        assert call_args[0][2]["title"] == "Test Decision"
        assert call_args[0][2]["status"] == "PROPOSED"
    
    def test_route_to_decision_handler(self):
        """Test that DECISION entity routes to _persist_decision_change."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._process_context_change = ContextServiceServicer._process_context_change.__get__(servicer)
        servicer._persist_decision_change = Mock()
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "CREATE"
        change.entity_type = "DECISION"
        change.entity_id = "DEC-001"
        change.payload = "{}"
        
        servicer._process_context_change(change, "TEST-001")
        
        servicer._persist_decision_change.assert_called_once()
    
    def test_route_to_subtask_handler(self):
        """Test that SUBTASK entity routes to _persist_subtask_change."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._process_context_change = ContextServiceServicer._process_context_change.__get__(servicer)
        servicer._persist_subtask_change = Mock()
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "UPDATE"
        change.entity_type = "SUBTASK"
        change.entity_id = "TASK-001"
        change.payload = "{}"
        
        servicer._process_context_change(change, "TEST-001")
        
        servicer._persist_subtask_change.assert_called_once()
    
    def test_route_to_milestone_handler(self):
        """Test that MILESTONE entity routes to _persist_milestone_change."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._process_context_change = ContextServiceServicer._process_context_change.__get__(servicer)
        servicer._persist_milestone_change = Mock()
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "CREATE"
        change.entity_type = "MILESTONE"
        change.entity_id = "EVENT-001"
        change.payload = "{}"
        
        servicer._process_context_change(change, "TEST-001")
        
        servicer._persist_milestone_change.assert_called_once()
    
    def test_handle_unknown_entity_type(self):
        """Test that unknown entity types are logged but don't crash."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._process_context_change = ContextServiceServicer._process_context_change.__get__(servicer)
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "CREATE"
        change.entity_type = "UNKNOWN_TYPE"
        change.entity_id = "UNK-001"
        change.payload = "{}"
        
        # Should not raise exception
        servicer._process_context_change(change, "TEST-001")
    
    def test_handle_persistence_error_gracefully(self):
        """Test that persistence errors are caught and logged."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._process_context_change = ContextServiceServicer._process_context_change.__get__(servicer)
        servicer._persist_decision_change = Mock(side_effect=Exception("Neo4j connection failed"))
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "CREATE"
        change.entity_type = "DECISION"
        change.entity_id = "DEC-001"
        change.payload = "{}"
        
        # Should not raise exception
        servicer._process_context_change(change, "TEST-001")


class TestPersistDecisionChange:
    """Unit tests for _persist_decision_change method."""
    
    def test_create_decision(self):
        """Test CREATE operation calls upsert_entity with correct properties."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._persist_decision_change = ContextServiceServicer._persist_decision_change.__get__(servicer)
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "CREATE"
        change.entity_id = "DEC-001"
        
        payload = {
            "title": "Use PostgreSQL",
            "rationale": "Better performance",
            "status": "PROPOSED"
        }
        
        servicer._persist_decision_change("TEST-001", change, payload)
        
        # Verify upsert_entity was called
        servicer.graph_command.upsert_entity.assert_called_once()
        call_args = servicer.graph_command.upsert_entity.call_args
        
        assert call_args[1]["label"] == "Decision"
        assert call_args[1]["id"] == "DEC-001"
        assert call_args[1]["properties"]["id"] == "DEC-001"
        assert call_args[1]["properties"]["case_id"] == "TEST-001"
        assert call_args[1]["properties"]["title"] == "Use PostgreSQL"
    
    def test_update_decision(self):
        """Test UPDATE operation calls upsert_entity with updated properties."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._persist_decision_change = ContextServiceServicer._persist_decision_change.__get__(servicer)
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "UPDATE"
        change.entity_id = "DEC-001"
        
        payload = {
            "status": "APPROVED",
            "approved_by": "architect"
        }
        
        servicer._persist_decision_change("TEST-001", change, payload)
        
        servicer.graph_command.upsert_entity.assert_called_once()
        call_args = servicer.graph_command.upsert_entity.call_args
        
        assert call_args[1]["properties"]["status"] == "APPROVED"
        assert call_args[1]["properties"]["approved_by"] == "architect"
    
    def test_delete_decision(self):
        """Test DELETE operation marks decision as DELETED."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._persist_decision_change = ContextServiceServicer._persist_decision_change.__get__(servicer)
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "DELETE"
        change.entity_id = "DEC-001"
        
        payload = {"title": "Old Decision"}
        
        servicer._persist_decision_change("TEST-001", change, payload)
        
        servicer.graph_command.upsert_entity.assert_called_once()
        call_args = servicer.graph_command.upsert_entity.call_args
        
        # Verify status is set to DELETED
        assert call_args[1]["properties"]["status"] == "DELETED"


class TestPersistSubtaskChange:
    """Unit tests for _persist_subtask_change method."""
    
    def test_update_subtask(self):
        """Test UPDATE operation calls upsert_entity for subtask."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._persist_subtask_change = ContextServiceServicer._persist_subtask_change.__get__(servicer)
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "UPDATE"
        change.entity_id = "TASK-001"
        
        payload = {
            "status": "IN_PROGRESS",
            "assignee": "dev-agent-1"
        }
        
        servicer._persist_subtask_change("TEST-001", change, payload)
        
        servicer.graph_command.upsert_entity.assert_called_once()
        call_args = servicer.graph_command.upsert_entity.call_args
        
        assert call_args[1]["label"] == "Subtask"
        assert call_args[1]["id"] == "TASK-001"
        assert call_args[1]["properties"]["status"] == "IN_PROGRESS"
        assert call_args[1]["properties"]["assignee"] == "dev-agent-1"


class TestPersistMilestoneChange:
    """Unit tests for _persist_milestone_change method."""
    
    def test_create_milestone(self):
        """Test CREATE operation calls upsert_entity for milestone."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        method = ContextServiceServicer._persist_milestone_change
        servicer._persist_milestone_change = method.__get__(servicer)
        servicer.graph_command = Mock()
        
        change = Mock()
        change.operation = "CREATE"
        change.entity_id = "EVENT-001"
        
        payload = {
            "event_type": "plan_approved",
            "description": "Plan approved by architect"
        }
        
        servicer._persist_milestone_change("TEST-001", change, payload)
        
        servicer.graph_command.upsert_entity.assert_called_once()
        call_args = servicer.graph_command.upsert_entity.call_args
        
        assert call_args[1]["label"] == "Event"
        assert call_args[1]["id"] == "EVENT-001"
        assert call_args[1]["properties"]["case_id"] == "TEST-001"
        assert call_args[1]["properties"]["event_type"] == "plan_approved"
        assert call_args[1]["properties"]["description"] == "Plan approved by architect"
        # Verify timestamp was added
        assert "timestamp_ms" in call_args[1]["properties"]
        assert call_args[1]["properties"]["timestamp_ms"] > 0


class TestDetectScopes:
    """Unit tests for _detect_scopes method."""
    
    def test_empty_content(self):
        """Test that empty content returns empty list."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._detect_scopes = ContextServiceServicer._detect_scopes.__get__(servicer)
        
        prompt_blocks = Mock()
        prompt_blocks.context = ""
        
        scopes = servicer._detect_scopes(prompt_blocks)
        
        assert scopes == []
    
    def test_detect_single_scope(self):
        """Test detection of single scope."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._detect_scopes = ContextServiceServicer._detect_scopes.__get__(servicer)
        
        prompt_blocks = Mock()
        prompt_blocks.context = "## Case: Test Case"
        
        scopes = servicer._detect_scopes(prompt_blocks)
        
        assert "CASE_HEADER" in scopes
        assert len(scopes) == 1
    
    def test_ignore_empty_sections(self):
        """Test that empty section indicators are ignored."""
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._detect_scopes = ContextServiceServicer._detect_scopes.__get__(servicer)
        
        prompt_blocks = Mock()
        prompt_blocks.context = """
        ## Your Subtasks:
        - No subtasks assigned.
        
        ## Recent Decisions:
        - No relevant decisions.
        """
        
        scopes = servicer._detect_scopes(prompt_blocks)
        
        # Should not detect SUBTASKS_ROLE or DECISIONS_RELEVANT_ROLE
        assert "SUBTASKS_ROLE" not in scopes
        assert "DECISIONS_RELEVANT_ROLE" not in scopes

