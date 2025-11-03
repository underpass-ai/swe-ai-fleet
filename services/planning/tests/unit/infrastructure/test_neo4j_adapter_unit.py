"""Unit tests for Neo4jAdapter - Configuration and retry logic."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from neo4j.exceptions import ServiceUnavailable, TransientError

from planning.domain import StoryId, StoryState, StoryStateEnum
from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter, Neo4jConfig


class TestNeo4jConfig:
    """Test Neo4j configuration."""

    def test_default_config_from_environment(self):
        """Should create config with default values."""
        config = Neo4jConfig()

        assert config.uri == "bolt://localhost:7687"
        assert config.user == "neo4j"
        assert config.password == "password"
        assert config.database is None
        assert config.max_retries == 3
        assert config.base_backoff_s == 0.25

    def test_custom_config(self):
        """Should accept custom configuration values."""
        config = Neo4jConfig(
            uri="bolt://custom:7687",
            user="admin",
            password="secret",
            database="planning",
            max_retries=5,
            base_backoff_s=0.5,
        )

        assert config.uri == "bolt://custom:7687"
        assert config.user == "admin"
        assert config.password == "secret"
        assert config.database == "planning"
        assert config.max_retries == 5
        assert config.base_backoff_s == 0.5

    def test_config_is_immutable(self):
        """Should be frozen dataclass (immutable)."""
        config = Neo4jConfig()

        with pytest.raises(Exception):  # FrozenInstanceError
            config.uri = "bolt://modified:7687"  # type: ignore


class TestNeo4jAdapterRetryLogic:
    """Test retry logic without real database."""

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    def test_retry_operation_success_first_attempt(self, mock_init, mock_driver):
        """Should succeed on first attempt."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig())

        mock_fn = Mock(return_value="success")
        result = adapter._retry_operation(mock_fn, "arg1", kwarg1="val1")

        assert result == "success"
        mock_fn.assert_called_once_with("arg1", kwarg1="val1")

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("time.sleep")
    def test_retry_operation_succeeds_after_transient_error(
        self, mock_sleep, mock_init, mock_driver
    ):
        """Should retry and succeed after transient error."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig(max_retries=3, base_backoff_s=0.1))

        # Fail twice, then succeed
        mock_fn = Mock(side_effect=[
            TransientError("temporary failure"),
            ServiceUnavailable("still failing"),
            "success"
        ])

        result = adapter._retry_operation(mock_fn)

        assert result == "success"
        assert mock_fn.call_count == 3
        assert mock_sleep.call_count == 2  # Slept twice (after 1st and 2nd failure)

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("time.sleep")
    def test_retry_operation_fails_after_max_retries(
        self, mock_sleep, mock_init, mock_driver
    ):
        """Should raise after max retries exhausted."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig(max_retries=2, base_backoff_s=0.1))

        mock_fn = Mock(side_effect=ServiceUnavailable("persistent failure"))

        with pytest.raises(ServiceUnavailable, match="persistent failure"):
            adapter._retry_operation(mock_fn)

        assert mock_fn.call_count == 3  # Initial + 2 retries
        assert mock_sleep.call_count == 2

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("time.sleep")
    def test_retry_operation_exponential_backoff(
        self, mock_sleep, mock_init, mock_driver
    ):
        """Should use exponential backoff."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig(max_retries=3, base_backoff_s=0.25))

        mock_fn = Mock(side_effect=[
            TransientError("fail 1"),
            TransientError("fail 2"),
            TransientError("fail 3"),
            "success"
        ])

        result = adapter._retry_operation(mock_fn)

        assert result == "success"
        # Check exponential backoff: 0.25, 0.5, 1.0
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert len(sleep_calls) == 3
        assert sleep_calls[0] == pytest.approx(0.25)
        assert sleep_calls[1] == pytest.approx(0.5)
        assert sleep_calls[2] == pytest.approx(1.0)

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    def test_retry_operation_does_not_retry_other_exceptions(
        self, mock_init, mock_driver
    ):
        """Should not retry non-transient errors."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig())

        mock_fn = Mock(side_effect=ValueError("not a transient error"))

        with pytest.raises(ValueError, match="not a transient error"):
            adapter._retry_operation(mock_fn)

        mock_fn.assert_called_once()  # No retries


class TestNeo4jAdapterSessionManagement:
    """Test session management logic."""

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    def test_session_without_database_name(self, mock_init, mock_driver):
        """Should create session without database parameter."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance

        adapter = Neo4jAdapter(Neo4jConfig(database=None))
        session = adapter._session()

        # Should call driver.session() without database parameter
        mock_driver_instance.session.assert_called_once_with()

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    def test_session_with_database_name(self, mock_init, mock_driver):
        """Should create session with database parameter."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance

        adapter = Neo4jAdapter(Neo4jConfig(database="planning"))
        session = adapter._session()

        # Should call driver.session(database="planning")
        mock_driver_instance.session.assert_called_once_with(database="planning")


class TestNeo4jAdapterErrorHandling:
    """Test error handling."""

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    def test_close_closes_driver(self, mock_init, mock_driver):
        """Should close driver when close() called."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance

        adapter = Neo4jAdapter(Neo4jConfig())
        adapter.close()

        mock_driver_instance.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("planning.infrastructure.adapters.neo4j_adapter.asyncio.to_thread")
    async def test_update_story_state_raises_on_not_found(
        self, mock_to_thread, mock_init, mock_driver
    ):
        """Should raise ValueError when story not found."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig())

        # Mock the sync method to return False (not found)
        mock_to_thread.side_effect = ValueError("Story node not found in graph")

        story_id = StoryId("story-123")
        new_state = StoryState(StoryStateEnum.IN_PROGRESS)

        with pytest.raises(ValueError, match="Story node not found in graph"):
            await adapter.update_story_state(story_id, new_state)

