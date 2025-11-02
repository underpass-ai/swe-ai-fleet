"""Unit tests for Neo4jAdapter - interface verification only.

Note: Full functionality testing of Neo4j adapter requires integration tests
with real Neo4j instance due to complex sync/async wrapping and transaction logic.
"""

from unittest.mock import MagicMock, patch

import pytest

from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter, Neo4jConfig


@pytest.fixture
def neo4j_config():
    """Create Neo4j configuration."""
    return Neo4jConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
        database=None,
    )


def test_neo4j_adapter_init(neo4j_config):
    """Test Neo4jAdapter initialization creates driver."""
    with patch('neo4j.GraphDatabase.driver') as mock_driver_cls:
        mock_driver = MagicMock()
        mock_driver_cls.return_value = mock_driver

        with patch.object(Neo4jAdapter, '_init_constraints'):
            adapter = Neo4jAdapter(config=neo4j_config)

            mock_driver_cls.assert_called_once_with(
                neo4j_config.uri,
                auth=(neo4j_config.user, neo4j_config.password),
            )

            assert adapter.driver == mock_driver


def test_neo4j_adapter_close(neo4j_config):
    """Test Neo4jAdapter close."""
    with patch('neo4j.GraphDatabase.driver') as mock_driver_cls:
        mock_driver = MagicMock()
        mock_driver_cls.return_value = mock_driver

        with patch.object(Neo4jAdapter, '_init_constraints'):
            adapter = Neo4jAdapter(config=neo4j_config)
            adapter.close()

            mock_driver.close.assert_called_once()


def test_neo4j_adapter_has_required_methods(neo4j_config):
    """Test Neo4jAdapter has all required methods (interface verification)."""
    with patch('neo4j.GraphDatabase.driver'):
        with patch.object(Neo4jAdapter, '_init_constraints'):
            adapter = Neo4jAdapter(config=neo4j_config)

            # Verify adapter has all required async methods
            assert hasattr(adapter, 'create_story_node')
            assert hasattr(adapter, 'update_story_state')
            assert hasattr(adapter, 'delete_story_node')
            assert hasattr(adapter, 'get_story_ids_by_state')
            assert hasattr(adapter, 'relate_story_to_user')

            # Verify they are async
            import inspect
            assert inspect.iscoroutinefunction(adapter.create_story_node)
            assert inspect.iscoroutinefunction(adapter.update_story_state)
            assert inspect.iscoroutinefunction(adapter.delete_story_node)
            assert inspect.iscoroutinefunction(adapter.get_story_ids_by_state)
