"""Tests for ListCouncilsUseCase."""

from unittest.mock import Mock

from services.orchestrator.application.usecases.list_councils_usecase import ListCouncilsUseCase
from services.orchestrator.domain.entities import CouncilRegistry


class TestListCouncilsUseCase:
    """Test cases for ListCouncilsUseCase."""

    def test_list_councils_usecase_initialization(self):
        """Test ListCouncilsUseCase initialization."""
        mock_council_query = Mock()
        use_case = ListCouncilsUseCase(council_query=mock_council_query)
        
        assert use_case.council_query == mock_council_query

    def test_execute_without_agents(self):
        """Test execute method without including agents."""
        mock_council_query = Mock()
        mock_council_registry = Mock(spec=CouncilRegistry)
        expected_result = [{"id": "council-1", "name": "Test Council"}]
        
        mock_council_query.list_councils.return_value = expected_result
        
        use_case = ListCouncilsUseCase(council_query=mock_council_query)
        result = use_case.execute(
            council_registry=mock_council_registry,
            include_agents=False
        )
        
        assert result == expected_result
        mock_council_query.list_councils.assert_called_once_with(
            council_registry=mock_council_registry,
            include_agents=False
        )

    def test_execute_with_agents(self):
        """Test execute method with agents included."""
        mock_council_query = Mock()
        mock_council_registry = Mock(spec=CouncilRegistry)
        expected_result = [
            {
                "id": "council-1", 
                "name": "Test Council",
                "agents": [{"id": "agent-1", "role": "developer"}]
            }
        ]
        
        mock_council_query.list_councils.return_value = expected_result
        
        use_case = ListCouncilsUseCase(council_query=mock_council_query)
        result = use_case.execute(
            council_registry=mock_council_registry,
            include_agents=True
        )
        
        assert result == expected_result
        mock_council_query.list_councils.assert_called_once_with(
            council_registry=mock_council_registry,
            include_agents=True
        )

    def test_execute_empty_result(self):
        """Test execute method with empty result."""
        mock_council_query = Mock()
        mock_council_registry = Mock(spec=CouncilRegistry)
        expected_result = []
        
        mock_council_query.list_councils.return_value = expected_result
        
        use_case = ListCouncilsUseCase(council_query=mock_council_query)
        result = use_case.execute(
            council_registry=mock_council_registry,
            include_agents=False
        )
        
        assert result == expected_result
        mock_council_query.list_councils.assert_called_once_with(
            council_registry=mock_council_registry,
            include_agents=False
        )

    def test_execute_multiple_councils(self):
        """Test execute method with multiple councils."""
        mock_council_query = Mock()
        mock_council_registry = Mock(spec=CouncilRegistry)
        expected_result = [
            {"id": "council-1", "name": "Frontend Council"},
            {"id": "council-2", "name": "Backend Council"},
            {"id": "council-3", "name": "DevOps Council"}
        ]
        
        mock_council_query.list_councils.return_value = expected_result
        
        use_case = ListCouncilsUseCase(council_query=mock_council_query)
        result = use_case.execute(
            council_registry=mock_council_registry,
            include_agents=False
        )
        
        assert result == expected_result
        assert len(result) == 3
        mock_council_query.list_councils.assert_called_once_with(
            council_registry=mock_council_registry,
            include_agents=False
        )

    def test_execute_delegates_to_port(self):
        """Test that execute method properly delegates to the port."""
        mock_council_query = Mock()
        mock_council_registry = Mock(spec=CouncilRegistry)
        
        use_case = ListCouncilsUseCase(council_query=mock_council_query)
        use_case.execute(mock_council_registry, include_agents=True)
        
        # Verify that the port method was called with correct parameters
        mock_council_query.list_councils.assert_called_once_with(
            council_registry=mock_council_registry,
            include_agents=True
        )
