"""Unit tests for core.context.adapters.neo4j_query_store

Tests Neo4j implementation of GraphQueryPort with comprehensive coverage
of configuration, queries, retry logic, and error handling.
"""

import os
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from core.context.adapters.neo4j_query_store import Neo4jConfig, Neo4jQueryStore


class TestNeo4jConfig:
    """Test Neo4jConfig dataclass"""

    def test_neo4j_config_defaults(self):
        """Test Neo4jConfig uses default values."""
        config = Neo4jConfig()
        
        assert config.uri == "bolt://localhost:7687"
        assert config.user == "neo4j"
        assert config.password == "test"
        assert config.database is None
        assert config.max_retries == 3
        assert config.base_backoff_s == 0.25

    def test_neo4j_config_with_env_vars(self):
        """Test Neo4jConfig reads from environment variables."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://neo4j:7687",
                "NEO4J_USER": "custom_user",
                "NEO4J_PASSWORD": "custom_pass",
                "NEO4J_DATABASE": "custom_db",
                "NEO4J_MAX_RETRIES": "5",
                "NEO4J_BACKOFF": "0.5",
            },
        ):
            config = Neo4jConfig()
            
            assert config.uri == "bolt://neo4j:7687"
            assert config.user == "custom_user"
            assert config.password == "custom_pass"
            assert config.database == "custom_db"
            assert config.max_retries == 5
            assert config.base_backoff_s == 0.5

    def test_neo4j_config_custom_values(self):
        """Test Neo4jConfig with explicit values."""
        config = Neo4jConfig(
            uri="bolt://custom:7687",
            user="admin",
            password="secret",
            database="mydb",
            max_retries=2,
            base_backoff_s=0.1,
        )
        
        assert config.uri == "bolt://custom:7687"
        assert config.user == "admin"
        assert config.password == "secret"
        assert config.database == "mydb"
        assert config.max_retries == 2
        assert config.base_backoff_s == 0.1

    def test_neo4j_config_is_frozen(self):
        """Test Neo4jConfig is immutable (frozen dataclass)."""
        config = Neo4jConfig()
        
        with pytest.raises(AttributeError):
            config.uri = "bolt://new:7687"


class TestNeo4jQueryStore:
    """Test Neo4jQueryStore adapter"""

    @pytest.fixture
    def mock_driver(self):
        """Mock Neo4j driver."""
        driver = MagicMock()
        driver.session = MagicMock()
        return driver

    @pytest.fixture
    def mock_session(self):
        """Mock Neo4j session."""
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=None)
        return session

    def test_neo4j_query_store_initialization(self, mock_driver):
        """Test Neo4jQueryStore initialization."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            
            config = Neo4jConfig(uri="bolt://localhost:7687")
            store = Neo4jQueryStore(config)
            
            assert store._config == config
            assert store._driver == mock_driver
            mock_gd.driver.assert_called_once_with(
                "bolt://localhost:7687", auth=("neo4j", "test")
            )

    def test_neo4j_query_store_default_config(self):
        """Test Neo4jQueryStore uses default config."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_gd.driver = MagicMock(return_value=mock_driver)
            
            store = Neo4jQueryStore()
            
            assert store._config.uri == "bolt://localhost:7687"
            assert store._config.user == "neo4j"
            assert store._config.password == "test"

    def test_neo4j_query_store_graphdatabase_unavailable(self):
        """Test initialization fails when Neo4j driver not available."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase", None):
            with pytest.raises(ImportError, match="Neo4j driver not available"):
                Neo4jQueryStore()

    def test_neo4j_query_store_close(self, mock_driver):
        """Test closing Neo4jQueryStore."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            
            store = Neo4jQueryStore()
            store.close()
            
            mock_driver.close.assert_called_once()

    def test_query_success(self, mock_driver, mock_session):
        """Test successful query execution."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            # Mock query result
            record1 = {"id": "1", "name": "Test1"}
            record2 = {"id": "2", "name": "Test2"}
            mock_session.run = MagicMock(return_value=[record1, record2])
            
            store = Neo4jQueryStore()
            result = store.query("MATCH (n) RETURN n", {"param": "value"})
            
            assert result == [record1, record2]
            mock_session.run.assert_called_once_with(
                "MATCH (n) RETURN n", {"param": "value"}
            )

    def test_query_with_no_params(self, mock_driver, mock_session):
        """Test query with no parameters."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            mock_session.run = MagicMock(return_value=[])
            
            store = Neo4jQueryStore()
            result = store.query("MATCH (n) RETURN n")
            
            # Should pass empty dict as params
            mock_session.run.assert_called_once_with("MATCH (n) RETURN n", {})
            assert result == []

    def test_query_with_retry_on_transient_error(self, mock_driver, mock_session):
        """Test query retries on TransientError."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            # Create a real TransientError-like exception
            from neo4j.exceptions import TransientError as RealTransientError
            
            # First call raises TransientError, second succeeds
            mock_session.run = MagicMock(
                side_effect=[RealTransientError("temp error"), [{"success": True}]]
            )
            
            store = Neo4jQueryStore(Neo4jConfig(max_retries=2, base_backoff_s=0.01))
            
            with patch("time.sleep"):  # Mock sleep to speed up test
                result = store.query("MATCH (n) RETURN n")
            
            # Should have retried (2 calls total)
            assert mock_session.run.call_count == 2

    def test_query_with_retry_on_service_unavailable(self, mock_driver, mock_session):
        """Test query retries on ServiceUnavailable."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            # Create a real ServiceUnavailable-like exception
            from neo4j.exceptions import ServiceUnavailable as RealServiceUnavailable
            
            # First call raises ServiceUnavailable, second succeeds
            mock_session.run = MagicMock(
                side_effect=[RealServiceUnavailable("service down"), [{"success": True}]]
            )
            
            store = Neo4jQueryStore(Neo4jConfig(max_retries=3, base_backoff_s=0.01))
            
            with patch("time.sleep") as mock_sleep:
                result = store.query("MATCH (n) RETURN n")
            
            # Should have slept between retries
            mock_sleep.assert_called()
            assert mock_session.run.call_count == 2

    def test_query_max_retries_exceeded(self, mock_driver, mock_session):
        """Test query raises error after max retries exceeded."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            # Create a real TransientError-like exception
            from neo4j.exceptions import TransientError as RealTransientError
            
            # Always raise error
            mock_session.run = MagicMock(side_effect=RealTransientError("always fail"))
            
            store = Neo4jQueryStore(Neo4jConfig(max_retries=2, base_backoff_s=0.01))
            
            with patch("time.sleep"):
                with pytest.raises(Exception):
                    store.query("MATCH (n) RETURN n")

    def test_query_exponential_backoff(self, mock_driver, mock_session):
        """Test exponential backoff on retry."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            # Create a real TransientError-like exception
            from neo4j.exceptions import TransientError as RealTransientError
            
            # Always raise error to trigger retries
            mock_session.run = MagicMock(side_effect=RealTransientError("always fail"))
            
            store = Neo4jQueryStore(
                Neo4jConfig(max_retries=3, base_backoff_s=0.25)
            )
            
            with patch("time.sleep") as mock_sleep:
                try:
                    store.query("MATCH (n) RETURN n")
                except Exception:
                    pass
            
            # Should have been called with exponential backoff: 0.25, 0.5
            calls = mock_sleep.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == 0.25  # First retry: 0.25 * 2^0
            assert calls[1][0][0] == 0.5   # Second retry: 0.25 * 2^1

    def test_case_plan_query(self, mock_driver, mock_session):
        """Test case_plan query."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            plan_data = [
                {"plan_id": "plan-1", "version": 1, "case_id": "case-1"},
                {"plan_id": "plan-0", "version": 0, "case_id": "case-1"},
            ]
            mock_session.run = MagicMock(return_value=plan_data)
            
            store = Neo4jQueryStore()
            result = store.case_plan("case-1")
            
            assert result == plan_data
            # Verify correct Cypher query was called
            call_args = mock_session.run.call_args
            assert "MATCH (c:Case" in call_args[0][0]
            assert "HAS_PLAN" in call_args[0][0]
            assert call_args[0][1] == {"case_id": "case-1"}

    def test_case_plan_empty_result(self, mock_driver, mock_session):
        """Test case_plan with no results."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            mock_session.run = MagicMock(return_value=[])
            
            store = Neo4jQueryStore()
            result = store.case_plan("nonexistent-case")
            
            assert result == []

    def test_node_with_neighbors_depth_1(self, mock_driver, mock_session):
        """Test node_with_neighbors with depth 1."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            neighbor_data = [
                {"n": {"id": "node-1"}, "r": {}, "neighbor": {"id": "neighbor-1"}},
                {"n": {"id": "node-1"}, "r": {}, "neighbor": {"id": "neighbor-2"}},
            ]
            mock_session.run = MagicMock(return_value=neighbor_data)
            
            store = Neo4jQueryStore()
            result = store.node_with_neighbors("node-1", depth=1)
            
            assert result == neighbor_data
            # Verify depth parameter is in query
            call_args = mock_session.run.call_args
            assert "*1..1" in call_args[0][0]

    def test_node_with_neighbors_depth_3(self, mock_driver, mock_session):
        """Test node_with_neighbors with depth 3."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            mock_session.run = MagicMock(return_value=[])
            
            store = Neo4jQueryStore()
            store.node_with_neighbors("node-1", depth=3)
            
            # Verify depth 3 is in query
            call_args = mock_session.run.call_args
            assert "*1..3" in call_args[0][0]

    def test_node_with_neighbors_empty_result(self, mock_driver, mock_session):
        """Test node_with_neighbors with no neighbors."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            mock_session.run = MagicMock(return_value=[])
            
            store = Neo4jQueryStore()
            result = store.node_with_neighbors("isolated-node")
            
            assert result == []

    def test_session_uses_configured_database(self, mock_driver, mock_session):
        """Test session uses configured database."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            config = Neo4jConfig(database="custom_db")
            mock_session.run = MagicMock(return_value=[])
            
            store = Neo4jQueryStore(config)
            store.query("MATCH (n) RETURN n")
            
            # Verify session was created with correct database
            mock_driver.session.assert_called_once_with(database="custom_db")

    def test_session_with_no_database(self, mock_driver, mock_session):
        """Test session creation with no database specified."""
        with patch("core.context.adapters.neo4j_query_store.GraphDatabase") as mock_gd:
            mock_gd.driver = MagicMock(return_value=mock_driver)
            mock_driver.session = MagicMock(return_value=mock_session)
            
            config = Neo4jConfig(database=None)
            mock_session.run = MagicMock(return_value=[])
            
            store = Neo4jQueryStore(config)
            store.query("MATCH (n) RETURN n")
            
            # Verify session was created with database=None
            mock_driver.session.assert_called_once_with(database=None)
