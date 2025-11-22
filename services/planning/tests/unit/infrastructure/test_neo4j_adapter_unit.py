"""Unit tests for Neo4jAdapter - Configuration and retry logic."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from neo4j.exceptions import ServiceUnavailable, TransientError
from planning.domain import StoryId, StoryState, StoryStateEnum
from planning.domain.value_objects.content.dependency_reason import DependencyReason
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter
from planning.infrastructure.adapters.neo4j_config import Neo4jConfig


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
        assert config.base_backoff_s == pytest.approx(0.25)

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
        assert config.base_backoff_s == pytest.approx(0.5)

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
        adapter._session()

        # Should call driver.session() without database parameter
        mock_driver_instance.session.assert_called_once_with()

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    def test_session_with_database_name(self, mock_init, mock_driver):
        """Should create session with database parameter."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance

        adapter = Neo4jAdapter(Neo4jConfig(database="planning"))
        adapter._session()

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


class TestNeo4jAdapterConstraints:
    """Test constraint initialization."""

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    def test_init_constraints_calls_all_constraints(self, mock_driver):
        """Should initialize all constraints."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_driver_instance.session.return_value = mock_session

        # Creating adapter calls _init_constraints() in __init__
        Neo4jAdapter(Neo4jConfig())

        # Verify session was used and execute_write was called
        mock_driver_instance.session.assert_called()
        mock_session.execute_write.assert_called_once()


class TestNeo4jAdapterStoryOperations:
    """Test story node operations."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("planning.infrastructure.adapters.neo4j_adapter.asyncio.to_thread")
    async def test_create_story_node_calls_sync_method(
        self, mock_to_thread, mock_init, mock_driver
    ):
        """Should call sync method via asyncio.to_thread."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig())

        # Mock to_thread to return a completed coroutine
        async def mock_coro(*args, **kwargs):
            pass

        mock_to_thread.return_value = mock_coro()
        mock_to_thread.side_effect = lambda *args, **kwargs: mock_coro()

        story_id = StoryId("story-123")
        created_by = "user-1"
        initial_state = StoryState(StoryStateEnum.TODO)

        await adapter.create_story_node(story_id, created_by, initial_state)

        # Verify asyncio.to_thread was called
        assert mock_to_thread.called

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    def test_create_story_node_sync_executes_query(
        self, mock_init, mock_driver
    ):
        """Should execute CREATE_STORY_NODE query."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_driver_instance.session.return_value = mock_session

        # Mock the transaction function that will be passed to execute_write
        def mock_execute_write(fn):
            mock_tx = MagicMock()
            fn(mock_tx)
            return None

        mock_session.execute_write = Mock(side_effect=mock_execute_write)

        adapter = Neo4jAdapter(Neo4jConfig())

        story_id = StoryId("story-123")
        created_by = "user-1"
        initial_state = StoryState(StoryStateEnum.TODO)

        adapter._create_story_node_sync(story_id, created_by, initial_state)

        # Verify execute_write was called
        mock_session.execute_write.assert_called_once()

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("planning.infrastructure.adapters.neo4j_adapter.asyncio.to_thread")
    async def test_update_story_state_success(
        self, mock_to_thread, mock_init, mock_driver
    ):
        """Should successfully update story state."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig())

        mock_to_thread.return_value = None

        story_id = StoryId("story-123")
        new_state = StoryState(StoryStateEnum.IN_PROGRESS)

        await adapter.update_story_state(story_id, new_state)

        # Verify asyncio.to_thread was called
        mock_to_thread.assert_called_once()

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("planning.infrastructure.adapters.neo4j_adapter.Neo4jQuery")
    def test_update_story_state_sync_success(
        self, mock_query, mock_init, mock_driver
    ):
        """Should successfully update story state synchronously."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"id": "story-123"}  # Story found
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_session.execute_write = Mock(return_value=True)  # Story found

        adapter = Neo4jAdapter(Neo4jConfig())

        story_id = StoryId("story-123")
        new_state = StoryState(StoryStateEnum.IN_PROGRESS)

        # Should not raise
        adapter._update_story_state_sync(story_id, new_state)

        # Verify execute_write was called
        mock_session.execute_write.assert_called_once()

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("planning.infrastructure.adapters.neo4j_adapter.asyncio.to_thread")
    async def test_delete_story_node_calls_sync_method(
        self, mock_to_thread, mock_init, mock_driver
    ):
        """Should call sync method via asyncio.to_thread."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig())

        mock_to_thread.return_value = None

        story_id = StoryId("story-123")

        await adapter.delete_story_node(story_id)

        # Verify asyncio.to_thread was called
        mock_to_thread.assert_called_once()
        call_args = mock_to_thread.call_args
        assert call_args[0][0] == adapter._delete_story_node_sync
        assert call_args[0][1] == story_id

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("planning.infrastructure.adapters.neo4j_adapter.Neo4jQuery")
    def test_delete_story_node_sync_executes_query(
        self, mock_query, mock_init, mock_driver
    ):
        """Should execute DELETE_STORY_NODE query."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance
        mock_session = MagicMock()
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_session.execute_write = Mock(return_value=None)

        adapter = Neo4jAdapter(Neo4jConfig())

        story_id = StoryId("story-123")

        adapter._delete_story_node_sync(story_id)

        # Verify execute_write was called
        mock_session.execute_write.assert_called_once()


class TestNeo4jAdapterTaskDependencies:
    """Test task dependency operations."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    async def test_create_task_dependencies_empty_tuple(
        self, mock_init, mock_driver
    ):
        """Should return early when dependencies tuple is empty."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig())

        # Should not raise or call anything
        await adapter.create_task_dependencies(())

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("planning.infrastructure.adapters.neo4j_adapter.asyncio.to_thread")
    async def test_create_task_dependencies_calls_sync_method(
        self, mock_to_thread, mock_init, mock_driver
    ):
        """Should call sync method via asyncio.to_thread."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig())

        mock_to_thread.return_value = None

        dependency = DependencyEdge(
            from_task_id=TaskId("task-1"),
            to_task_id=TaskId("task-2"),
            reason=DependencyReason("test dependency"),
        )

        await adapter.create_task_dependencies((dependency,))

        # Verify asyncio.to_thread was called
        mock_to_thread.assert_called_once()
        call_args = mock_to_thread.call_args
        assert call_args[0][0] == adapter._create_task_dependencies_sync
        assert call_args[0][1] == (dependency,)

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("planning.infrastructure.adapters.neo4j_adapter.Neo4jQuery")
    def test_create_task_dependencies_sync_success(
        self, mock_query, mock_init, mock_driver
    ):
        """Should successfully create task dependencies."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance
        mock_session = MagicMock()
        mock_tx = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"id": "relationship-1"}  # Dependency created
        mock_tx.run.return_value = mock_result
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_session.execute_write = Mock(side_effect=lambda fn: fn(mock_tx))

        adapter = Neo4jAdapter(Neo4jConfig())

        dependency = DependencyEdge(
            from_task_id=TaskId("task-1"),
            to_task_id=TaskId("task-2"),
            reason=DependencyReason("test dependency"),
        )

        # Should not raise
        adapter._create_task_dependencies_sync((dependency,))

        # Verify execute_write was called
        mock_session.execute_write.assert_called_once()

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("planning.infrastructure.adapters.neo4j_adapter.Neo4jQuery")
    def test_create_task_dependencies_sync_raises_when_not_found(
        self, mock_query, mock_init, mock_driver
    ):
        """Should raise ValueError when dependency creation fails."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance
        mock_session = MagicMock()
        mock_tx = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = None  # Dependency not created
        mock_tx.run.return_value = mock_result
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_session.execute_write = Mock(side_effect=lambda fn: fn(mock_tx))

        adapter = Neo4jAdapter(Neo4jConfig())

        dependency = DependencyEdge(
            from_task_id=TaskId("task-1"),
            to_task_id=TaskId("task-2"),
            reason=DependencyReason("test dependency"),
        )

        with pytest.raises(ValueError, match="Failed to create dependency"):
            adapter._create_task_dependencies_sync((dependency,))


class TestNeo4jAdapterStoryQuery:
    """Test story query operations."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    @patch("planning.infrastructure.adapters.neo4j_adapter.asyncio.to_thread")
    async def test_get_story_ids_by_state_calls_sync_method(
        self, mock_to_thread, mock_init, mock_driver
    ):
        """Should call sync method via asyncio.to_thread."""
        mock_driver.return_value = MagicMock()
        adapter = Neo4jAdapter(Neo4jConfig())

        # Mock to_thread to return a coroutine that yields the result
        async def mock_coro(*args, **kwargs):
            await asyncio.sleep(0)  # Use async feature
            return ["story-1", "story-2"]

        mock_to_thread.side_effect = lambda *args, **kwargs: mock_coro()

        state = StoryState(StoryStateEnum.TODO)

        result = await adapter.get_story_ids_by_state(state)

        assert result == ["story-1", "story-2"]
        # Verify asyncio.to_thread was called
        assert mock_to_thread.called

    @patch("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver")
    @patch.object(Neo4jAdapter, "_init_constraints")
    def test_get_story_ids_by_state_sync_returns_ids(
        self, mock_init, mock_driver
    ):
        """Should return list of story IDs."""
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_driver_instance.session.return_value = mock_session

        # Mock transaction and result
        mock_record1 = {"story_id": "story-1"}
        mock_record2 = {"story_id": "story-2"}
        mock_result = [mock_record1, mock_record2]
        mock_tx = MagicMock()
        mock_tx.run.return_value = mock_result

        def mock_execute_read(fn):
            return fn(mock_tx)

        mock_session.execute_read = Mock(side_effect=mock_execute_read)

        adapter = Neo4jAdapter(Neo4jConfig())

        state = StoryState(StoryStateEnum.TODO)

        result = adapter._get_story_ids_by_state_sync(state)

        assert result == ["story-1", "story-2"]
        # Verify execute_read was called
        mock_session.execute_read.assert_called_once()

