"""Unit tests for Neo4jAdapter Project methods."""

from unittest.mock import MagicMock, patch

import pytest
from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter
from planning.infrastructure.adapters.neo4j_config import Neo4jConfig
from planning.infrastructure.adapters.neo4j_queries import Neo4jQuery


@pytest.fixture
def neo4j_config():
    """Create Neo4j configuration."""
    return Neo4jConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
        database=None,
    )


@pytest.fixture
def mock_neo4j_adapter(neo4j_config):
    """Create Neo4jAdapter with mocked driver."""
    with patch('neo4j.GraphDatabase.driver') as mock_driver_cls:
        mock_driver = MagicMock()
        mock_driver_cls.return_value = mock_driver

        with patch.object(Neo4jAdapter, '_init_constraints'):
            adapter = Neo4jAdapter(config=neo4j_config)
            adapter.driver = mock_driver
            yield adapter


@pytest.fixture
def mock_session():
    """Create mock Neo4j session."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


@pytest.mark.asyncio
async def test_create_project_node_async_wrapper(mock_neo4j_adapter):
    """Test create_project_node async wrapper delegates to sync method."""
    mock_neo4j_adapter._create_project_node_sync = MagicMock()

    await mock_neo4j_adapter.create_project_node(
        project_id="PROJ-123",
        name="Test Project",
        status="active",
        created_at="2025-01-28T10:00:00Z",
        updated_at="2025-01-28T10:00:00Z",
    )

    mock_neo4j_adapter._create_project_node_sync.assert_called_once_with(
        "PROJ-123",
        "Test Project",
        "active",
        "2025-01-28T10:00:00Z",
        "2025-01-28T10:00:00Z",
    )


def test_create_project_node_sync_executes_query(mock_neo4j_adapter, mock_session):
    """Test _create_project_node_sync executes correct Cypher query."""
    mock_neo4j_adapter._session = MagicMock(return_value=mock_session)

    # Create mock transaction
    mock_tx = MagicMock()

    # Mock execute_write to call the transaction function with mock_tx
    mock_execute_write = MagicMock()
    mock_execute_write.side_effect = lambda tx_func: tx_func(mock_tx)

    # Mock retry_operation to execute the function passed
    mock_neo4j_adapter._retry_operation = MagicMock(
        side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)
    )

    # Mock session.execute_write
    mock_session.execute_write = mock_execute_write

    mock_neo4j_adapter._create_project_node_sync(
        project_id="PROJ-456",
        name="Sync Project",
        status="completed",
        created_at="2025-01-28T10:00:00Z",
        updated_at="2025-01-28T11:00:00Z",
    )

    # Verify query was executed with correct parameters
    assert mock_tx.run.called
    call_args = mock_tx.run.call_args
    assert call_args[0][0] == Neo4jQuery.CREATE_PROJECT_NODE.value
    assert call_args[1]["project_id"] == "PROJ-456"
    assert call_args[1]["name"] == "Sync Project"
    assert call_args[1]["status"] == "completed"
    assert call_args[1]["created_at"] == "2025-01-28T10:00:00Z"
    assert call_args[1]["updated_at"] == "2025-01-28T11:00:00Z"


def test_create_project_node_sync_uses_retry_operation(mock_neo4j_adapter, mock_session):
    """Test _create_project_node_sync uses retry operation for transaction."""
    mock_neo4j_adapter._session = MagicMock(return_value=mock_session)
    mock_neo4j_adapter._retry_operation = MagicMock()

    mock_neo4j_adapter._create_project_node_sync(
        project_id="PROJ-789",
        name="Retry Project",
        status="active",
        created_at="2025-01-28T10:00:00Z",
        updated_at="2025-01-28T10:00:00Z",
    )

    # Verify retry_operation was called
    assert mock_neo4j_adapter._retry_operation.called
    # Verify it was called with execute_write
    call_args = mock_neo4j_adapter._retry_operation.call_args
    assert call_args[0][0] == mock_session.execute_write


@pytest.mark.asyncio
async def test_update_project_status_async_wrapper(mock_neo4j_adapter):
    """Test update_project_status async wrapper delegates to sync method."""
    mock_neo4j_adapter._update_project_status_sync = MagicMock(return_value=None)

    await mock_neo4j_adapter.update_project_status(
        project_id="PROJ-123",
        status="completed",
        updated_at="2025-01-28T11:00:00Z",
    )

    mock_neo4j_adapter._update_project_status_sync.assert_called_once_with(
        "PROJ-123",
        "completed",
        "2025-01-28T11:00:00Z",
    )


def test_update_project_status_sync_executes_query(mock_neo4j_adapter, mock_session):
    """Test _update_project_status_sync executes correct Cypher query."""
    mock_neo4j_adapter._session = MagicMock(return_value=mock_session)

    # Create mock transaction with result
    mock_tx = MagicMock()
    mock_result = MagicMock()
    mock_single = MagicMock()
    mock_result.single.return_value = mock_single  # Node found
    mock_tx.run.return_value = mock_result

    # Mock execute_write to call the transaction function with mock_tx
    mock_execute_write = MagicMock()
    mock_execute_write.side_effect = lambda tx_func: tx_func(mock_tx)

    # Mock retry_operation to execute the function passed
    mock_neo4j_adapter._retry_operation = MagicMock(
        side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)
    )

    # Mock session.execute_write
    mock_session.execute_write = mock_execute_write

    mock_neo4j_adapter._update_project_status_sync(
        project_id="PROJ-456",
        status="archived",
        updated_at="2025-01-28T12:00:00Z",
    )

    # Verify query was executed
    assert mock_tx.run.called
    call_args = mock_tx.run.call_args
    assert call_args[0][0] == Neo4jQuery.UPDATE_PROJECT_STATUS.value
    assert call_args[1]["project_id"] == "PROJ-456"
    assert call_args[1]["status"] == "archived"
    assert call_args[1]["updated_at"] == "2025-01-28T12:00:00Z"


def test_update_project_status_sync_node_not_found_raises_error(mock_neo4j_adapter, mock_session):
    """Test _update_project_status_sync raises ValueError when node not found."""
    mock_neo4j_adapter._session = MagicMock(return_value=mock_session)

    # Create mock transaction with result indicating node not found
    mock_tx = MagicMock()
    mock_result = MagicMock()
    mock_result.single.return_value = None  # Node not found
    mock_tx.run.return_value = mock_result

    # Mock execute_write to call the transaction function with mock_tx
    mock_execute_write = MagicMock()
    mock_execute_write.side_effect = lambda tx_func: tx_func(mock_tx)

    # Mock retry_operation to execute the function passed
    mock_neo4j_adapter._retry_operation = MagicMock(
        side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)
    )

    # Mock session.execute_write
    mock_session.execute_write = mock_execute_write

    with pytest.raises(ValueError, match="Project node not found in graph: PROJ-NOT-FOUND"):
        mock_neo4j_adapter._update_project_status_sync(
            project_id="PROJ-NOT-FOUND",
            status="active",
            updated_at="2025-01-28T10:00:00Z",
        )


@pytest.mark.asyncio
async def test_get_project_ids_by_status_async_wrapper(mock_neo4j_adapter):
    """Test get_project_ids_by_status async wrapper delegates to sync method."""
    mock_neo4j_adapter._get_project_ids_by_status_sync = MagicMock(
        return_value=["PROJ-001", "PROJ-002"]
    )

    result = await mock_neo4j_adapter.get_project_ids_by_status("active")

    assert result == ["PROJ-001", "PROJ-002"]
    mock_neo4j_adapter._get_project_ids_by_status_sync.assert_called_once_with("active")


def test_get_project_ids_by_status_sync_executes_query(mock_neo4j_adapter, mock_session):
    """Test _get_project_ids_by_status_sync executes correct Cypher query."""
    mock_neo4j_adapter._session = MagicMock(return_value=mock_session)

    # Mock query results
    mock_record1 = {"project_id": "PROJ-001"}
    mock_record2 = {"project_id": "PROJ-002"}

    mock_result = MagicMock()
    mock_result.__iter__.return_value = iter([mock_record1, mock_record2])

    mock_tx = MagicMock()
    mock_tx.run.return_value = mock_result

    # Mock execute_read to call the transaction function with mock_tx
    mock_execute_read = MagicMock()
    mock_execute_read.side_effect = lambda tx_func: tx_func(mock_tx)

    # Mock retry_operation to execute the function passed
    mock_neo4j_adapter._retry_operation = MagicMock(
        side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)
    )

    # Mock session.execute_read
    mock_session.execute_read = mock_execute_read

    result = mock_neo4j_adapter._get_project_ids_by_status_sync("completed")

    # Verify query was executed
    assert mock_tx.run.called
    call_args = mock_tx.run.call_args
    assert call_args[0][0] == Neo4jQuery.GET_PROJECT_IDS_BY_STATUS.value
    assert call_args[1]["status"] == "completed"

    # Verify results are extracted correctly
    assert len(result) == 2
    assert "PROJ-001" in result
    assert "PROJ-002" in result


def test_get_project_ids_by_status_sync_empty_result(mock_neo4j_adapter, mock_session):
    """Test _get_project_ids_by_status_sync returns empty list when no matches."""
    mock_neo4j_adapter._session = MagicMock(return_value=mock_session)

    # Empty result - no records
    mock_result = MagicMock()
    mock_result.__iter__.return_value = iter([])

    mock_tx = MagicMock()
    mock_tx.run.return_value = mock_result

    # Mock execute_read to call the transaction function with mock_tx
    mock_execute_read = MagicMock()
    mock_execute_read.side_effect = lambda tx_func: tx_func(mock_tx)

    # Mock retry_operation to execute the function passed and return its result
    mock_neo4j_adapter._retry_operation = MagicMock(
        side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)
    )

    # Mock session.execute_read
    mock_session.execute_read = mock_execute_read

    result = mock_neo4j_adapter._get_project_ids_by_status_sync("archived")

    # Result should be an empty list (not MagicMock)
    assert isinstance(result, list)
    assert result == []


def test_get_project_ids_by_status_sync_uses_read_transaction(mock_neo4j_adapter, mock_session):
    """Test _get_project_ids_by_status_sync uses read transaction."""
    mock_neo4j_adapter._session = MagicMock(return_value=mock_session)
    mock_result = MagicMock()
    mock_result.__iter__.return_value = iter([])

    mock_tx = MagicMock()
    mock_tx.run.return_value = mock_result

    mock_neo4j_adapter._retry_operation = MagicMock(
        side_effect=lambda fn, *args, **kwargs: fn(mock_tx)
    )

    mock_neo4j_adapter._get_project_ids_by_status_sync("active")

    # Verify retry_operation was called with execute_read (not execute_write)
    assert mock_neo4j_adapter._retry_operation.called
    call_args = mock_neo4j_adapter._retry_operation.call_args
    assert call_args[0][0] == mock_session.execute_read

