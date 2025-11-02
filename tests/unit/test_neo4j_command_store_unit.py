# tests/unit/test_neo4j_command_store_unit.py
from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest
from core.context.adapters.neo4j_command_store import Neo4jCommandStore, Neo4jConfig
from neo4j import Driver, Session
from neo4j.exceptions import ServiceUnavailable, TransientError


class TestNeo4jConfig:
    """Unit tests for Neo4jConfig dataclass."""

    def test_default_values(self):
        """Test that Neo4jConfig uses correct default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = Neo4jConfig()
            assert config.uri == "bolt://localhost:7687"
            assert config.user == "neo4j"
            assert config.password == "test"
            assert config.database is None
            assert config.max_retries == 3
            assert config.base_backoff_s == 0.25

    def test_environment_variable_override(self):
        """Test that environment variables override default values."""
        env_vars = {
            "NEO4J_URI": "bolt://test:7687",
            "NEO4J_USER": "testuser",
            "NEO4J_PASSWORD": "testpass",
            "NEO4J_DATABASE": "testdb",
            "NEO4J_MAX_RETRIES": "5",
            "NEO4J_BACKOFF": "0.5",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Neo4jConfig()
            assert config.uri == "bolt://test:7687"
            assert config.user == "testuser"
            assert config.password == "testpass"
            assert config.database == "testdb"
            assert config.max_retries == 5
            assert config.base_backoff_s == 0.5

    def test_database_none_when_empty_string(self):
        """Test that empty string for database becomes None."""
        with patch.dict(os.environ, {"NEO4J_DATABASE": ""}):
            config = Neo4jConfig()
            assert config.database is None

    def test_frozen_dataclass(self):
        """Test that Neo4jConfig is immutable."""
        config = Neo4jConfig()
        with pytest.raises(AttributeError):
            config.uri = "new_uri"


class TestNeo4jCommandStore:
    """Unit tests for Neo4jCommandStore class."""

    def _setup_session_mock(self, mock_driver, mock_session):
        """Helper method to setup session context manager mock."""
        mock_session_context = Mock()
        mock_session_context.__enter__ = Mock(return_value=mock_session)
        mock_session_context.__exit__ = Mock(return_value=None)
        mock_driver.session.return_value = mock_session_context
        return mock_session_context

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        mock_driver = Mock(spec=Driver)

        with patch(
            'core.context.adapters.neo4j_command_store.GraphDatabase.driver'
        ) as mock_driver_factory:
            mock_driver_factory.return_value = mock_driver

            store = Neo4jCommandStore()

            assert isinstance(store.cfg, Neo4jConfig)
            assert store.driver == mock_driver
            mock_driver_factory.assert_called_once_with("bolt://localhost:7687", auth=("neo4j", "test"))

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = Neo4jConfig(uri="bolt://custom:7687", user="custom", password="custom")
        mock_driver = Mock(spec=Driver)

        store = Neo4jCommandStore(cfg=config, driver=mock_driver)

        assert store.cfg == config
        assert store.driver == mock_driver

    def test_close(self):
        """Test that close method calls driver.close()."""
        mock_driver = Mock(spec=Driver)
        store = Neo4jCommandStore(driver=mock_driver)

        store.close()

        mock_driver.close.assert_called_once()

    def test_session_without_database(self):
        """Test _session method without database."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_driver.session.return_value = mock_session

        store = Neo4jCommandStore(driver=mock_driver)
        result = store._session()

        assert result == mock_session
        mock_driver.session.assert_called_once_with()

    def test_session_with_database(self):
        """Test _session method with database."""
        config = Neo4jConfig(database="testdb")
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_driver.session.return_value = mock_session

        store = Neo4jCommandStore(cfg=config, driver=mock_driver)
        result = store._session()

        assert result == mock_session
        mock_driver.session.assert_called_once_with(database="testdb")

    def test_retry_write_success_first_attempt(self):
        """Test _retry_write succeeds on first attempt."""
        mock_driver = Mock(spec=Driver)
        store = Neo4jCommandStore(driver=mock_driver)

        mock_fn = Mock(return_value="success")

        result = store._retry_write(mock_fn, "arg1", "arg2", kwarg="value")

        assert result == "success"
        mock_fn.assert_called_once_with("arg1", "arg2", kwarg="value")

    def test_retry_write_success_after_retries(self):
        """Test _retry_write succeeds after retries."""
        mock_driver = Mock(spec=Driver)
        store = Neo4jCommandStore(driver=mock_driver)

        mock_fn = Mock(side_effect=[ServiceUnavailable("error"), ServiceUnavailable("error"), "success"])

        with patch('time.sleep'):
            result = store._retry_write(mock_fn)

        assert result == "success"
        assert mock_fn.call_count == 3

    def test_retry_write_max_retries_exceeded(self):
        """Test _retry_write raises exception after max retries."""
        mock_driver = Mock(spec=Driver)
        store = Neo4jCommandStore(driver=mock_driver)

        mock_fn = Mock(side_effect=ServiceUnavailable("error"))

        with patch('time.sleep'):
            with pytest.raises(ServiceUnavailable):
                store._retry_write(mock_fn)

        assert mock_fn.call_count == 4  # max_retries + 1

    def test_retry_write_with_transient_error(self):
        """Test _retry_write handles TransientError."""
        mock_driver = Mock(spec=Driver)
        store = Neo4jCommandStore(driver=mock_driver)

        mock_fn = Mock(side_effect=[TransientError("error"), "success"])

        with patch('time.sleep'):
            result = store._retry_write(mock_fn)

        assert result == "success"
        assert mock_fn.call_count == 2

    def test_init_constraints(self):
        """Test init_constraints method."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)
        mock_session.execute_write.return_value = None

        store = Neo4jCommandStore(driver=mock_driver)

        labels = ["Case", "Decision", "Subtask"]
        store.init_constraints(labels)

        mock_session.execute_write.assert_called_once()
        # Verify the transaction function was called with correct cypher statements
        tx_func = mock_session.execute_write.call_args[0][0]
        tx_func(mock_transaction)

        # Should have called tx.run for each label
        assert mock_transaction.run.call_count == 3
        calls = mock_transaction.run.call_args_list
        assert any(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Case) REQUIRE n.id IS UNIQUE" in str(call)
            for call in calls
        )
        assert any(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Decision) REQUIRE n.id IS UNIQUE" in str(call)
            for call in calls
        )
        assert any(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Subtask) REQUIRE n.id IS UNIQUE" in str(call)
            for call in calls
        )

    def test_upsert_entity(self):
        """Test upsert_entity method."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)
        mock_session.execute_write.return_value = None

        store = Neo4jCommandStore(driver=mock_driver)

        store.upsert_entity("Case", "case1", {"name": "Test Case"})

        mock_session.execute_write.assert_called_once()
        tx_func = mock_session.execute_write.call_args[0][0]
        tx_func(mock_transaction)

        mock_transaction.run.assert_called_once()
        call_args = mock_transaction.run.call_args
        assert "MERGE (n:Case {id:$id}) SET n += $props" in call_args[0][0]
        assert call_args[1]["id"] == "case1"
        assert call_args[1]["props"] == {"name": "Test Case", "id": "case1"}

    def test_upsert_entity_without_properties(self):
        """Test upsert_entity method without properties."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)
        mock_session.execute_write.return_value = None

        store = Neo4jCommandStore(driver=mock_driver)

        store.upsert_entity("Case", "case1")

        mock_session.execute_write.assert_called_once()
        tx_func = mock_session.execute_write.call_args[0][0]
        tx_func(mock_transaction)

        call_args = mock_transaction.run.call_args
        assert call_args[1]["props"] == {"id": "case1"}

    def test_upsert_entity_multi(self):
        """Test upsert_entity_multi method."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)
        mock_session.execute_write.return_value = None

        store = Neo4jCommandStore(driver=mock_driver)

        store.upsert_entity_multi(["Case", "Project"], "case1", {"name": "Test"})

        mock_session.execute_write.assert_called_once()
        tx_func = mock_session.execute_write.call_args[0][0]
        tx_func(mock_transaction)

        call_args = mock_transaction.run.call_args
        assert "MERGE (n:Case:Project {id:$id}) SET n += $props" in call_args[0][0]
        assert call_args[1]["props"] == {"name": "Test", "id": "case1"}

    def test_upsert_entity_multi_empty_labels(self):
        """Test upsert_entity_multi method with empty labels raises ValueError."""
        mock_driver = Mock(spec=Driver)
        store = Neo4jCommandStore(driver=mock_driver)

        with pytest.raises(ValueError, match="labels must be non-empty"):
            store.upsert_entity_multi([], "case1")

    def test_upsert_entity_multi_duplicate_labels(self):
        """Test upsert_entity_multi method handles duplicate labels."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)
        mock_session.execute_write.return_value = None

        store = Neo4jCommandStore(driver=mock_driver)

        store.upsert_entity_multi(["Case", "Case", "Project"], "case1")

        tx_func = mock_session.execute_write.call_args[0][0]
        tx_func(mock_transaction)

        call_args = mock_transaction.run.call_args
        # Should deduplicate and sort labels
        assert "MERGE (n:Case:Project {id:$id}) SET n += $props" in call_args[0][0]

    def test_relate(self):
        """Test relate method."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)
        mock_session.execute_write.return_value = None

        store = Neo4jCommandStore(driver=mock_driver)

        store.relate(
            "case1",
            "HAS_PLAN",
            "plan1",
            src_labels=["Case"],
            dst_labels=["PlanVersion"],
            properties={"created_at": "2024-01-01"},
        )

        mock_session.execute_write.assert_called_once()
        tx_func = mock_session.execute_write.call_args[0][0]
        tx_func(mock_transaction)

        call_args = mock_transaction.run.call_args
        expected_cypher = (
            "MATCH (a:Case {id:$src}), (b:PlanVersion {id:$dst}) MERGE (a)-[r:HAS_PLAN]->(b) SET r += $props"
        )
        assert call_args[0][0] == expected_cypher
        assert call_args[1]["src"] == "case1"
        assert call_args[1]["dst"] == "plan1"
        assert call_args[1]["props"] == {"created_at": "2024-01-01"}

    def test_relate_without_labels(self):
        """Test relate method without labels."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)
        mock_session.execute_write.return_value = None

        store = Neo4jCommandStore(driver=mock_driver)

        store.relate("case1", "HAS_PLAN", "plan1")

        tx_func = mock_session.execute_write.call_args[0][0]
        tx_func(mock_transaction)

        call_args = mock_transaction.run.call_args
        expected_cypher = "MATCH (a {id:$src}), (b {id:$dst}) MERGE (a)-[r:HAS_PLAN]->(b) SET r += $props"
        assert call_args[0][0] == expected_cypher

    def test_relate_without_properties(self):
        """Test relate method without properties."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)
        mock_session.execute_write.return_value = None

        store = Neo4jCommandStore(driver=mock_driver)

        store.relate("case1", "HAS_PLAN", "plan1", src_labels=["Case"], dst_labels=["PlanVersion"])

        tx_func = mock_session.execute_write.call_args[0][0]
        tx_func(mock_transaction)

        call_args = mock_transaction.run.call_args
        assert call_args[1]["props"] == {}

    def test_execute_write_success(self):
        """Test execute_write method with successful query execution."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)

        # Mock transaction result
        mock_record1 = Mock()
        mock_record1.__iter__ = Mock(return_value=iter([mock_record1]))
        mock_record2 = Mock()
        mock_record2.__iter__ = Mock(return_value=iter([mock_record2]))
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([mock_record1, mock_record2]))
        mock_transaction.run.return_value = mock_result

        store = Neo4jCommandStore(driver=mock_driver)

        # Execute a raw Cypher query
        cypher = "CREATE (n:TestNode {id: $id, name: $name}) RETURN n"
        params = {"id": "test-123", "name": "Test Node"}

        result = store.execute_write(cypher, params)

        # Assert session and transaction were used
        mock_session.execute_write.assert_called_once()

        # Extract and execute the transaction function
        tx_func = mock_session.execute_write.call_args[0][0]
        tx_result = tx_func(mock_transaction)

        # Assert transaction.run was called with correct query and params
        mock_transaction.run.assert_called_once_with(cypher, params)

        # Assert result contains records
        assert len(tx_result) == 2

    def test_execute_write_with_empty_params(self):
        """Test execute_write method with no parameters."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)

        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_transaction.run.return_value = mock_result

        store = Neo4jCommandStore(driver=mock_driver)

        # Execute query without params
        cypher = "MATCH (n) RETURN count(n) as total"
        result = store.execute_write(cypher)

        # Assert session was called
        mock_session.execute_write.assert_called_once()

        # Extract and execute transaction function
        tx_func = mock_session.execute_write.call_args[0][0]
        tx_func(mock_transaction)

        # Assert run was called with empty params dict
        call_args = mock_transaction.run.call_args
        assert call_args[0][0] == cypher
        assert call_args[0][1] == {}

    def test_execute_write_with_none_params(self):
        """Test execute_write method with None params."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)

        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_transaction.run.return_value = mock_result

        store = Neo4jCommandStore(driver=mock_driver)

        # Execute query with None params
        cypher = "MATCH (n:TestNode) DELETE n"
        result = store.execute_write(cypher, None)

        # Extract and execute transaction function
        tx_func = mock_session.execute_write.call_args[0][0]
        tx_func(mock_transaction)

        # Assert run was called with empty params dict
        call_args = mock_transaction.run.call_args
        assert call_args[0][1] == {}

    def test_execute_write_complex_query(self):
        """Test execute_write with complex multi-statement query."""
        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)

        # Mock multiple records returned
        records = [Mock(), Mock(), Mock()]
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(records))
        mock_transaction.run.return_value = mock_result

        store = Neo4jCommandStore(driver=mock_driver)

        # Complex query like TransitionPhase uses
        cypher = """
        MATCH (s:ProjectCase {story_id: $story_id})
        CREATE (p:PhaseTransition {
            story_id: $story_id,
            from_phase: $from_phase,
            to_phase: $to_phase,
            timestamp: $timestamp
        })
        CREATE (s)-[:HAS_PHASE]->(p)
        SET s.current_phase = $to_phase
        RETURN p.timestamp as when
        """
        params = {
            "story_id": "US-001",
            "from_phase": "DESIGN",
            "to_phase": "BUILD",
            "timestamp": "2025-11-02T00:00:00Z"
        }

        result = store.execute_write(cypher, params)

        # Extract and execute transaction function
        tx_func = mock_session.execute_write.call_args[0][0]
        tx_result = tx_func(mock_transaction)

        # Assert correct query and params
        call_args = mock_transaction.run.call_args
        assert "MATCH (s:ProjectCase {story_id: $story_id})" in call_args[0][0]
        assert call_args[0][1] == params

        # Assert results returned
        assert len(tx_result) == 3

    def test_execute_write_with_retry_on_transient_error(self):
        """Test execute_write retries on transient errors."""
        from neo4j.exceptions import TransientError

        mock_driver = Mock(spec=Driver)
        mock_session = Mock(spec=Session)
        mock_transaction = Mock()

        self._setup_session_mock(mock_driver, mock_session)

        # First call fails with TransientError, second succeeds
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([Mock()]))
        mock_transaction.run.return_value = mock_result

        mock_session.execute_write.side_effect = [
            TransientError("Temporary failure"),
            None  # Success on retry
        ]

        config = Neo4jConfig(max_retries=3, base_backoff_s=0.01)
        store = Neo4jCommandStore(cfg=config, driver=mock_driver)

        # Should succeed after retry
        cypher = "CREATE (n:Test {id: 'retry-test'})"
        result = store.execute_write(cypher)

        # Assert retry was attempted
        assert mock_session.execute_write.call_count == 2
