"""Unit tests for ProjectDecisionUseCase."""

from unittest.mock import Mock

import pytest
from core.context.usecases.project_decision import ProjectDecisionUseCase


class TestProjectDecisionUseCase:
    """Unit tests for ProjectDecisionUseCase."""
    
    def test_execute_creates_decision_node(self):
        """Test that execute creates a Decision node in the graph."""
        # Arrange
        mock_writer = Mock()
        use_case = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-001",
            "kind": "TECHNICAL",
            "summary": "Use Redis for caching to improve performance",
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        mock_writer.upsert_entity.assert_called_once()
        call_args = mock_writer.upsert_entity.call_args
        
        # Verify entity type
        assert call_args[0][0] == "Decision"
        
        # Verify entity ID
        assert call_args[0][1] == "DEC-001"
        
        # Verify properties contain expected fields
        properties = call_args[0][2]
        assert "kind" in properties
        assert "summary" in properties
    
    def test_execute_creates_affects_relationship_when_sub_id_provided(self):
        """Test that execute creates AFFECTS relationship when sub_id is provided."""
        # Arrange
        mock_writer = Mock()
        use_case = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-001",
            "kind": "TECHNICAL",
            "summary": "Use Redis for caching",
            "sub_id": "TASK-001",  # ← Decision affects a subtask
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        # Should create both entity and relationship
        assert mock_writer.upsert_entity.called
        assert mock_writer.relate.called
        
        # Verify relationship details
        relate_call = mock_writer.relate.call_args
        assert relate_call[0][0] == "DEC-001"  # src_id
        assert relate_call[0][1] == "AFFECTS"  # rel_type
        assert relate_call[0][2] == "TASK-001"  # dst_id
        
        # Verify labels
        assert relate_call[1]["src_labels"] == ["Decision"]
        assert relate_call[1]["dst_labels"] == ["Subtask"]
    
    def test_execute_no_relationship_when_no_sub_id(self):
        """Test that execute does NOT create relationship when sub_id is not provided."""
        # Arrange
        mock_writer = Mock()
        use_case = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-002",
            "kind": "ARCHITECTURAL",
            "summary": "Adopt microservices architecture",
            # No sub_id - this is a general decision
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        # Should create entity but NOT relationship
        assert mock_writer.upsert_entity.called
        assert not mock_writer.relate.called
    
    def test_execute_with_minimal_payload(self):
        """Test that execute works with minimal payload (only node_id)."""
        # Arrange
        mock_writer = Mock()
        use_case = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {
            "node_id": "DEC-003",
            # No kind, no summary - testing domain entity defaults
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        mock_writer.upsert_entity.assert_called_once()
        call_args = mock_writer.upsert_entity.call_args
        assert call_args[0][1] == "DEC-003"
    
    @pytest.mark.parametrize("decision_kind", [
        "TECHNICAL",
        "ARCHITECTURAL",
        "BUSINESS",
        "OPERATIONAL",
    ])
    def test_execute_handles_different_decision_kinds(self, decision_kind):
        """Test that execute handles different types of decisions."""
        # Arrange
        mock_writer = Mock()
        use_case = ProjectDecisionUseCase(writer=mock_writer)
        
        payload = {
            "node_id": f"DEC-{decision_kind}",
            "kind": decision_kind,
            "summary": f"A {decision_kind} decision",
        }
        
        # Act
        use_case.execute(payload)
        
        # Assert
        mock_writer.upsert_entity.assert_called_once()
        properties = mock_writer.upsert_entity.call_args[0][2]
        assert properties["kind"] == decision_kind

