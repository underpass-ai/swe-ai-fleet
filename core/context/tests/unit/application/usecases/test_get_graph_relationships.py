"""Unit tests for GetGraphRelationshipsUseCase."""

from unittest.mock import MagicMock

import pytest
from core.context.application.usecases.get_graph_relationships import (
    GetGraphRelationshipsUseCase,
)
from core.context.domain.graph_relationships import GraphRelationships


@pytest.fixture
def mock_graph_query_port() -> MagicMock:
    """Create a mock GraphQueryPort."""
    return MagicMock()


@pytest.fixture
def use_case(mock_graph_query_port: MagicMock) -> GetGraphRelationshipsUseCase:
    """Create GetGraphRelationshipsUseCase with mocked port."""
    return GetGraphRelationshipsUseCase(graph_query=mock_graph_query_port)


@pytest.fixture
def sample_neo4j_result() -> dict:
    """Sample Neo4j query result for testing."""
    return {
        "node_data": {
            "id": "story-123",
            "labels": ["Story"],
            "properties": {"story_id": "story-123", "title": "Test Story"},
            "title": "Test Story",
        },
        "neighbors_data": [
            {
                "node": {
                    "id": "epic-001",
                    "labels": ["Epic"],
                    "properties": {"epic_id": "epic-001", "title": "Test Epic"},
                    "title": "Test Epic",
                },
                "relationships": [
                    {
                        "type": "CONTAINS_STORY",
                        "from": "epic-001",
                        "to": "story-123",
                        "properties": {},
                    }
                ],
            }
        ],
    }


class TestGetGraphRelationshipsUseCaseExecute:
    """Test execute method of GetGraphRelationshipsUseCase."""

    def test_execute_success(
        self,
        use_case: GetGraphRelationshipsUseCase,
        mock_graph_query_port: MagicMock,
        sample_neo4j_result: dict,
    ) -> None:
        """Test successful execution returns GraphRelationships aggregate."""
        # Arrange
        mock_graph_query_port.get_graph_relationships.return_value = sample_neo4j_result

        # Act
        result = use_case.execute(
            node_id="story-123",
            node_type="Story",
            depth=2,
        )

        # Assert
        assert isinstance(result, GraphRelationships)
        assert result.node.get_id_string() == "story-123"
        assert result.neighbor_count() == 1
        assert result.relationship_count() == 1
        mock_graph_query_port.get_graph_relationships.assert_called_once_with(
            node_id="story-123",
            node_type="Story",
            depth=2,
        )

    def test_execute_with_default_depth(
        self,
        use_case: GetGraphRelationshipsUseCase,
        mock_graph_query_port: MagicMock,
        sample_neo4j_result: dict,
    ) -> None:
        """Test execution with default depth (2)."""
        # Arrange
        mock_graph_query_port.get_graph_relationships.return_value = sample_neo4j_result

        # Act
        result = use_case.execute(
            node_id="story-123",
            node_type="Story",
        )

        # Assert
        assert isinstance(result, GraphRelationships)
        mock_graph_query_port.get_graph_relationships.assert_called_once_with(
            node_id="story-123",
            node_type="Story",
            depth=2,  # Default depth
        )

    def test_execute_clamps_depth_to_minimum(
        self,
        use_case: GetGraphRelationshipsUseCase,
        mock_graph_query_port: MagicMock,
        sample_neo4j_result: dict,
    ) -> None:
        """Test that depth < 1 is clamped to 1."""
        # Arrange
        mock_graph_query_port.get_graph_relationships.return_value = sample_neo4j_result

        # Act
        use_case.execute(
            node_id="story-123",
            node_type="Story",
            depth=0,  # Below minimum
        )

        # Assert
        mock_graph_query_port.get_graph_relationships.assert_called_once_with(
            node_id="story-123",
            node_type="Story",
            depth=1,  # Clamped to minimum
        )

    def test_execute_clamps_depth_to_maximum(
        self,
        use_case: GetGraphRelationshipsUseCase,
        mock_graph_query_port: MagicMock,
        sample_neo4j_result: dict,
    ) -> None:
        """Test that depth > 3 is clamped to 3."""
        # Arrange
        mock_graph_query_port.get_graph_relationships.return_value = sample_neo4j_result

        # Act
        use_case.execute(
            node_id="story-123",
            node_type="Story",
            depth=5,  # Above maximum
        )

        # Assert
        mock_graph_query_port.get_graph_relationships.assert_called_once_with(
            node_id="story-123",
            node_type="Story",
            depth=3,  # Clamped to maximum
        )

    def test_execute_rejects_empty_node_id(
        self,
        use_case: GetGraphRelationshipsUseCase,
    ) -> None:
        """Test that empty node_id raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="node_id is required and cannot be empty"):
            use_case.execute(
                node_id="",
                node_type="Story",
            )

    def test_execute_rejects_whitespace_node_id(
        self,
        use_case: GetGraphRelationshipsUseCase,
    ) -> None:
        """Test that whitespace-only node_id raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="node_id is required and cannot be empty"):
            use_case.execute(
                node_id="   ",
                node_type="Story",
            )

    def test_execute_rejects_invalid_node_type(
        self,
        use_case: GetGraphRelationshipsUseCase,
    ) -> None:
        """Test that invalid node_type raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid node_type"):
            use_case.execute(
                node_id="story-123",
                node_type="InvalidType",
            )

    def test_execute_accepts_all_valid_node_types(
        self,
        use_case: GetGraphRelationshipsUseCase,
        mock_graph_query_port: MagicMock,
        sample_neo4j_result: dict,
    ) -> None:
        """Test that all valid node types are accepted."""
        # Arrange
        mock_graph_query_port.get_graph_relationships.return_value = sample_neo4j_result
        valid_types = ["Project", "Epic", "Story", "Task"]

        # Act & Assert
        for node_type in valid_types:
            use_case.execute(
                node_id=f"{node_type.lower()}-123",
                node_type=node_type,
            )

        assert mock_graph_query_port.get_graph_relationships.call_count == len(valid_types)

    def test_execute_raises_when_node_not_found(
        self,
        use_case: GetGraphRelationshipsUseCase,
        mock_graph_query_port: MagicMock,
    ) -> None:
        """Test that None result from port raises ValueError."""
        # Arrange
        mock_graph_query_port.get_graph_relationships.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Node not found"):
            use_case.execute(
                node_id="nonexistent-123",
                node_type="Story",
            )

    def test_execute_raises_when_port_returns_empty_dict(
        self,
        use_case: GetGraphRelationshipsUseCase,
        mock_graph_query_port: MagicMock,
    ) -> None:
        """Test that empty dict result from port raises ValueError."""
        # Arrange
        mock_graph_query_port.get_graph_relationships.return_value = {}

        # Act & Assert
        with pytest.raises(ValueError, match="Node not found"):
            use_case.execute(
                node_id="story-123",
                node_type="Story",
            )

    def test_execute_with_no_neighbors(
        self,
        use_case: GetGraphRelationshipsUseCase,
        mock_graph_query_port: MagicMock,
    ) -> None:
        """Test execution with node that has no neighbors."""
        # Arrange
        result_without_neighbors = {
            "node_data": {
                "id": "story-123",
                "labels": ["Story"],
                "properties": {"story_id": "story-123", "title": "Test Story"},
                "title": "Test Story",
            },
            "neighbors_data": [],
        }
        mock_graph_query_port.get_graph_relationships.return_value = result_without_neighbors

        # Act
        result = use_case.execute(
            node_id="story-123",
            node_type="Story",
        )

        # Assert
        assert isinstance(result, GraphRelationships)
        assert result.node.get_id_string() == "story-123"
        assert result.neighbor_count() == 0
        assert result.relationship_count() == 0

    def test_execute_with_multiple_neighbors(
        self,
        use_case: GetGraphRelationshipsUseCase,
        mock_graph_query_port: MagicMock,
    ) -> None:
        """Test execution with node that has multiple neighbors."""
        # Arrange
        result_with_multiple_neighbors = {
            "node_data": {
                "id": "story-123",
                "labels": ["Story"],
                "properties": {"story_id": "story-123", "title": "Test Story"},
                "title": "Test Story",
            },
            "neighbors_data": [
                {
                    "node": {
                        "id": "epic-001",
                        "labels": ["Epic"],
                        "properties": {"epic_id": "epic-001", "title": "Epic 1"},
                        "title": "Epic 1",
                    },
                    "relationships": [
                        {
                            "type": "CONTAINS_STORY",
                            "from": "epic-001",
                            "to": "story-123",
                            "properties": {},
                        }
                    ],
                },
                {
                    "node": {
                        "id": "task-001",
                        "labels": ["Task"],
                        "properties": {"task_id": "task-001", "title": "Task 1"},
                        "title": "Task 1",
                    },
                    "relationships": [
                        {
                            "type": "HAS_TASK",
                            "from": "story-123",
                            "to": "task-001",
                            "properties": {},
                        }
                    ],
                },
            ],
        }
        mock_graph_query_port.get_graph_relationships.return_value = result_with_multiple_neighbors

        # Act
        result = use_case.execute(
            node_id="story-123",
            node_type="Story",
        )

        # Assert
        assert isinstance(result, GraphRelationships)
        assert result.node.get_id_string() == "story-123"
        assert result.neighbor_count() == 2
        assert result.relationship_count() == 2

    def test_execute_logs_result(
        self,
        use_case: GetGraphRelationshipsUseCase,
        mock_graph_query_port: MagicMock,
        sample_neo4j_result: dict,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that execute logs the result."""
        # Arrange
        import logging
        mock_graph_query_port.get_graph_relationships.return_value = sample_neo4j_result

        # Act
        with caplog.at_level(logging.INFO):
            use_case.execute(
                node_id="story-123",
                node_type="Story",
            )

        # Assert
        assert "GetGraphRelationships:" in caplog.text
        assert "node=story-123" in caplog.text or "story-123" in caplog.text
        assert "neighbors=1" in caplog.text
        assert "relationships=1" in caplog.text

