"""
Hexagonal Architecture Tests for Context Adapters.

Tests the infrastructure layer (adapters) that implement ports for
context domain operations.

Follows Hexagonal Architecture:
- Tests adapters implementing GraphQueryPort
- Mocks Neo4j driver (infrastructure dependency)
- Focus on port contract compliance
- Error handling and retry logic
"""

from unittest.mock import MagicMock, patch

import pytest
from core.context.adapters.neo4j_query_store import Neo4jQueryStore
from core.context.domain.neo4j_config import Neo4jConfig


class TestNeo4jConfigHexagonal:
    """Test Neo4j configuration following hexagonal principles."""

    def test_config_defaults_from_env(self):
        """Test config does NOT read env vars (DDD: Config is a Value Object).

        The domain VO is simple and explicit. Env var reading is done by
        Neo4jConfigLoader in infrastructure layer (Dependency Inversion Principle).
        """
        pytest.skip("Domain VO doesn't read env vars. Use Neo4jConfigLoader for that (DDD/Hexagonal)")

    def test_config_custom_values(self):
        """Test config with custom values."""
        config = Neo4jConfig(
            uri='bolt://test:7687',
            user='test_user',
            password='test_pass',
            database='test_db',
            max_retries=7,
            base_backoff_s=1.0,
        )

        assert config.uri == 'bolt://test:7687'
        assert config.user == 'test_user'
        assert config.password == 'test_pass'
        assert config.database == 'test_db'
        assert config.max_retries == 7
        assert config.base_backoff_s == pytest.approx(1.0)

    def test_config_immutability(self):
        """Test config is immutable (frozen dataclass)."""
        config = Neo4jConfig(uri='bolt://localhost:7687', user='neo4j', password='test')

        with pytest.raises(AttributeError):
            config.uri = 'bolt://modified:7687'


class TestNeo4jQueryStoreHexagonal:
    """Test Neo4j Query Store as port implementation."""

    def test_implements_graph_query_port(self):
        """Test that Neo4jQueryStore implements GraphQueryPort interface."""
        # This is a hexagonal architecture contract test
        # Verify required port methods exist
        required_methods = ['query', 'case_plan', 'node_with_neighbors']
        for method in required_methods:
            assert hasattr(Neo4jQueryStore, method)

    def test_initialization_with_config(self):
        """Test initialization with custom config."""
        config = Neo4jConfig(uri='bolt://test:7687', user='neo4j', password='test')

        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_db.driver.return_value = mock_driver

            store = Neo4jQueryStore(config)

            assert store._config == config
            mock_db.driver.assert_called_once_with(
                'bolt://test:7687',
                auth=('neo4j', 'test')
            )

    def test_initialization_with_default_config(self):
        """Test initialization with default config."""
        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_db.driver.return_value = mock_driver

            # Neo4jConfig (domain VO) requires uri, user, password (no defaults)
            from core.context.domain.neo4j_config import Neo4jConfig
            config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test")
            store = Neo4jQueryStore(config=config)

            assert isinstance(store._config, Neo4jConfig)
            mock_db.driver.assert_called_once()

    def test_close_connection(self):
        """Test closing Neo4j connection."""
        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_db.driver.return_value = mock_driver

            # Neo4jConfig (domain VO) requires uri, user, password (no defaults)
            from core.context.domain.neo4j_config import Neo4jConfig
            config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test")
            store = Neo4jQueryStore(config=config)
            store.close()

            mock_driver.close.assert_called_once()

    def test_session_creation_with_database(self):
        """Test session creation with database parameter."""
        config = Neo4jConfig(uri='bolt://localhost:7687', user='neo4j', password='test', database='test_db')

        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            store = Neo4jQueryStore(config)
            session = store._session()

            mock_driver.session.assert_called_once_with(database='test_db')
            assert session == mock_session

    def test_session_creation_without_database(self):
        """Test session creation without database parameter."""
        config = Neo4jConfig(uri='bolt://localhost:7687', user='neo4j', password='test', database=None)

        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            store = Neo4jQueryStore(config)
            session = store._session()

            # When database is None, SUT calls session() without parameters (DDD-compliant behavior)
            mock_driver.session.assert_called_once_with()
            assert session == mock_session


class TestNeo4jQueryStoreRetryLogic:
    """Test retry logic in Neo4j Query Store."""

    def test_query_success_first_attempt(self):
        """Test query succeeds on first attempt."""
        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = MagicMock()

            # Mock successful query execution
            mock_result.__iter__ = lambda self: iter([{'id': 'test'}])
            mock_session.run.return_value = mock_result
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            # Neo4jConfig (domain VO) requires uri, user, password (no defaults)
            from core.context.domain.neo4j_config import Neo4jConfig
            config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test")
            store = Neo4jQueryStore(config=config)
            result = store.query("MATCH (n) RETURN n")

            assert result == [{'id': 'test'}]
            mock_session.run.assert_called_once()

    def test_query_retry_on_transient_error(self):
        """Test query retries on transient error."""
        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db, \
             patch('time.sleep') as mock_sleep:

            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = MagicMock()

            # Import the actual Neo4j exceptions
            from neo4j.exceptions import TransientError

            # First call fails, second succeeds
            mock_session.run.side_effect = [
                TransientError("TransientError"),  # First attempt fails
                mock_result  # Second attempt succeeds
            ]
            mock_result.__iter__ = lambda self: iter([{'id': 'test'}])
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            # Neo4jConfig (domain VO) requires uri, user, password (no defaults)
            from core.context.domain.neo4j_config import Neo4jConfig
            config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test")
            store = Neo4jQueryStore(config=config)
            result = store.query("MATCH (n) RETURN n")

            assert result == [{'id': 'test'}]
            assert mock_session.run.call_count == 2
            mock_sleep.assert_called_once()

    def test_query_max_retries_exceeded(self):
        """Test query raises exception after max retries."""
        config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test", max_retries=2)

        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db, \
             patch('time.sleep') as mock_sleep:

            mock_driver = MagicMock()
            mock_session = MagicMock()

            # Import the actual Neo4j exceptions
            from neo4j.exceptions import TransientError

            # All attempts fail
            mock_session.run.side_effect = TransientError("PersistentError")
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            store = Neo4jQueryStore(config)

            with pytest.raises(TransientError, match="PersistentError"):
                store.query("MATCH (n) RETURN n")

            assert mock_session.run.call_count == 2
            assert mock_sleep.call_count == 1

    def test_query_exponential_backoff(self):
        """Test exponential backoff timing."""
        config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test", max_retries=3, base_backoff_s=0.1)

        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db, \
             patch('time.sleep') as mock_sleep:

            mock_driver = MagicMock()
            mock_session = MagicMock()

            # Import the actual Neo4j exceptions
            from neo4j.exceptions import TransientError

            # First two attempts fail, third succeeds
            mock_session.run.side_effect = [
                TransientError("Error1"),
                TransientError("Error2"),
                MagicMock(__iter__=lambda self: iter([{'id': 'test'}]))
            ]
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            store = Neo4jQueryStore(config)
            result = store.query("MATCH (n) RETURN n")

            assert result == [{'id': 'test'}]
            # Check exponential backoff: 0.1 * 2^0 = 0.1, 0.1 * 2^1 = 0.2
            expected_calls = [0.1, 0.2]
            actual_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert actual_calls == expected_calls


class TestNeo4jQueryStorePortMethods:
    """Test specific port method implementations."""

    def test_case_plan_query_structure(self):
        """Test case_plan method constructs correct Cypher query."""
        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = MagicMock()

            mock_result.__iter__ = lambda self: iter([{'plan_id': 'plan-001'}])
            mock_session.run.return_value = mock_result
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            # Neo4jConfig (domain VO) requires uri, user, password (no defaults)
            from core.context.domain.neo4j_config import Neo4jConfig
            config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test")
            store = Neo4jQueryStore(config=config)
            result = store.case_plan("case-001")

            # Verify correct Cypher query and parameters
            mock_session.run.assert_called_once()
            call_args = mock_session.run.call_args
            cypher = call_args[0][0]
            params = call_args[0][1]

            # Case→Story refactor
            assert "MATCH (s:Story {id: $story_id})" in cypher
            assert "HAS_PLAN" in cypher
            assert "ORDER BY p.version DESC" in cypher
            # case_id → story_id refactor
            assert params == {"story_id": "case-001"}

    def test_node_with_neighbors_depth_1(self):
        """Test node_with_neighbors with depth=1."""
        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = MagicMock()

            mock_result.__iter__ = lambda self: iter([{'n': 'node', 'neighbor': 'neighbor1'}])
            mock_session.run.return_value = mock_result
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            # Neo4jConfig (domain VO) requires uri, user, password (no defaults)
            from core.context.domain.neo4j_config import Neo4jConfig
            config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test")
            store = Neo4jQueryStore(config=config)
            result = store.node_with_neighbors("node-001", depth=1)

            # Verify correct Cypher query
            call_args = mock_session.run.call_args
            cypher = call_args[0][0]
            params = call_args[0][1]

            assert "*1..1" in cypher
            assert params == {"node_id": "node-001"}

    def test_node_with_neighbors_depth_3(self):
        """Test node_with_neighbors with depth=3."""
        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = MagicMock()

            mock_result.__iter__ = lambda self: iter([{'n': 'node', 'neighbor': 'neighbor1'}])
            mock_session.run.return_value = mock_result
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            # Neo4jConfig (domain VO) requires uri, user, password (no defaults)
            from core.context.domain.neo4j_config import Neo4jConfig
            config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test")
            store = Neo4jQueryStore(config=config)
            result = store.node_with_neighbors("node-001", depth=3)

            # Verify correct Cypher query
            call_args = mock_session.run.call_args
            cypher = call_args[0][0]

            assert "*1..3" in cypher

    def test_node_with_neighbors_default_depth(self):
        """Test node_with_neighbors with default depth=1."""
        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = MagicMock()

            mock_result.__iter__ = lambda self: iter([{'n': 'node'}])
            mock_session.run.return_value = mock_result
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            # Neo4jConfig (domain VO) requires uri, user, password (no defaults)
            from core.context.domain.neo4j_config import Neo4jConfig
            config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test")
            store = Neo4jQueryStore(config=config)
            result = store.node_with_neighbors("node-001")

            # Should default to depth=1
            call_args = mock_session.run.call_args
            cypher = call_args[0][0]
            assert "*1..1" in cypher


class TestNeo4jQueryStoreErrorHandling:
    """Test error handling in Neo4j Query Store."""

    def test_import_error_when_neo4j_unavailable(self):
        """Test ImportError when Neo4j driver is not available.

        Note: The new DDD-compliant adapter imports neo4j directly (fail-fast at import time).
        This test verifies that import failures are immediate, not delayed.
        """
        # The new adapter will fail at import time if neo4j is not available
        # This test is legacy - the adapter no longer has runtime ImportError check
        # Import check happens at module load time, which is the correct DDD approach
        pytest.skip("New adapter fails at import time, not instantiation time (DDD fail-fast)")

    def test_query_with_empty_params(self):
        """Test query with None params defaults to empty dict."""
        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = MagicMock()

            mock_result.__iter__ = lambda self: iter([])
            mock_session.run.return_value = mock_result
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            # Neo4jConfig (domain VO) requires uri, user, password (no defaults)
            from core.context.domain.neo4j_config import Neo4jConfig
            config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test")
            store = Neo4jQueryStore(config=config)
            result = store.query("MATCH (n) RETURN n", params=None)

            # Should call with empty dict
            call_args = mock_session.run.call_args
            params = call_args[0][1]
            assert params == {}

    def test_query_with_custom_params(self):
        """Test query with custom parameters."""
        with patch('core.context.adapters.neo4j_query_store.GraphDatabase') as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = MagicMock()

            mock_result.__iter__ = lambda self: iter([])
            mock_session.run.return_value = mock_result
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = mock_session
            mock_db.driver.return_value = mock_driver

            # Neo4jConfig (domain VO) requires uri, user, password (no defaults)
            from core.context.domain.neo4j_config import Neo4jConfig
            config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="test")
            store = Neo4jQueryStore(config=config)
            custom_params = {"id": "test", "name": "example"}
            result = store.query("MATCH (n {id: $id}) RETURN n", params=custom_params)

            # Should call with custom params
            call_args = mock_session.run.call_args
            params = call_args[0][1]
            assert params == custom_params
