from unittest.mock import MagicMock

import pytest
from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter
from planning.infrastructure.adapters.neo4j_queries import Neo4jQuery


@pytest.fixture
def mock_driver():
    return MagicMock()

@pytest.fixture
def adapter(mock_driver):
    with pytest.MonkeyPatch.context() as m:
        m.setattr("planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver", MagicMock(return_value=mock_driver))
        return Neo4jAdapter()

@pytest.mark.asyncio
async def test_create_epic_node(adapter, mock_driver):
    """Test create_epic_node executes correct Cypher query."""
    # Setup mock session and transaction
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session

    # Call method
    await adapter.create_epic_node(
        epic_id="epic-1",
        project_id="proj-1",
        name="Epic One",
        status="TODO",
        created_at="2023-01-01",
        updated_at="2023-01-02"
    )

    # Verify execution
    mock_session.execute_write.assert_called_once()
    tx_fn = mock_session.execute_write.call_args[0][0]

    # Mock tx and run the internal function
    mock_tx = MagicMock()
    tx_fn(mock_tx)

    mock_tx.run.assert_called_once()
    args, kwargs = mock_tx.run.call_args
    assert args[0] == Neo4jQuery.CREATE_EPIC_NODE.value
    assert kwargs["epic_id"] == "epic-1"
    assert kwargs["project_id"] == "proj-1"
    assert kwargs["name"] == "Epic One"

@pytest.mark.asyncio
async def test_update_epic_status(adapter, mock_driver):
    """Test update_epic_status executes correct Cypher query."""
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session

    await adapter.update_epic_status(
        epic_id="epic-1",
        status="DONE",
        updated_at="2023-01-03"
    )

    mock_session.execute_write.assert_called_once()
    tx_fn = mock_session.execute_write.call_args[0][0]

    mock_tx = MagicMock()
    mock_result = MagicMock()
    mock_result.single.return_value = {"e": "node"} # Found
    mock_tx.run.return_value = mock_result

    tx_fn(mock_tx)

    mock_tx.run.assert_called_once()
    args, kwargs = mock_tx.run.call_args
    assert args[0] == Neo4jQuery.UPDATE_EPIC_STATUS.value
    assert kwargs["epic_id"] == "epic-1"
    assert kwargs["status"] == "DONE"

@pytest.mark.asyncio
async def test_get_epic_ids_by_project(adapter, mock_driver):
    """Test get_epic_ids_by_project executes correct Cypher query."""
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session

    await adapter.get_epic_ids_by_project("proj-1")

    mock_session.execute_read.assert_called_once()
    tx_fn = mock_session.execute_read.call_args[0][0]

    mock_tx = MagicMock()
    mock_tx.run.return_value = [{"epic_id": "e1"}, {"epic_id": "e2"}]

    result = tx_fn(mock_tx)

    assert result == ["e1", "e2"]
    mock_tx.run.assert_called_once()
    args, _ = mock_tx.run.call_args
    assert args[0] == Neo4jQuery.GET_EPIC_IDS_BY_PROJECT.value


@pytest.mark.asyncio
async def test_delete_epic_node(adapter, mock_driver):
    """Test delete_epic_node executes correct Cypher query."""
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session

    await adapter.delete_epic_node("epic-123")

    mock_session.execute_write.assert_called_once()
    tx_fn = mock_session.execute_write.call_args[0][0]

    mock_tx = MagicMock()
    tx_fn(mock_tx)

    mock_tx.run.assert_called_once()
    args, kwargs = mock_tx.run.call_args
    assert args[0] == Neo4jQuery.DELETE_EPIC_NODE.value
    assert kwargs["epic_id"] == "epic-123"

