"""Unit tests for Neo4jAdapter - Backlog Review Ceremony methods."""

from unittest.mock import MagicMock

import pytest
from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter
from planning.infrastructure.adapters.neo4j_queries import Neo4jQuery


@pytest.fixture
def mock_driver():
    """Create mock Neo4j driver."""
    return MagicMock()


@pytest.fixture
def adapter(mock_driver):
    """Create Neo4jAdapter with mocked driver."""
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "planning.infrastructure.adapters.neo4j_adapter.GraphDatabase.driver",
            MagicMock(return_value=mock_driver),
        )
        m.setattr(
            "planning.infrastructure.adapters.neo4j_adapter.Neo4jAdapter._init_constraints",
            MagicMock(),
        )
        return Neo4jAdapter()


@pytest.mark.asyncio
async def test_save_backlog_review_ceremony_node_creates_all_relationships(
    adapter, mock_driver
):
    """Test that save_backlog_review_ceremony_node creates all REVIEWS relationships successfully."""
    # Setup mock session and transaction
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = None

    # Mock retry_operation to call execute_write directly
    adapter._retry_operation = lambda fn, *args, **kwargs: fn(*args, **kwargs)

    # Call method
    ceremony_id = "BRC-TEST-001"
    properties = {
        "created_by": "user-1",
        "status": "DRAFT",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "story_count": 3,
    }
    story_ids = ["story-1", "story-2", "story-3"]
    project_id = "proj-1"

    await adapter.save_backlog_review_ceremony_node(
        ceremony_id=ceremony_id,
        properties=properties,
        story_ids=story_ids,
        project_id=project_id,
    )

    # Verify execute_write was called
    mock_session.execute_write.assert_called_once()
    tx_fn = mock_session.execute_write.call_args[0][0]

    # Mock transaction
    mock_tx = MagicMock()

    # Mock result for ceremony node creation
    mock_ceremony_result = MagicMock()
    mock_tx.run.return_value = mock_ceremony_result

    # Mock result for each story relationship (all successful)
    mock_story_results = []
    for _ in story_ids:
        mock_result = MagicMock()
        mock_record = MagicMock()
        mock_result.single.return_value = mock_record  # Success: record exists
        mock_story_results.append(mock_result)

    # Configure tx.run to return different results for different calls
    call_count = 0

    def mock_tx_run(query, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: CREATE_CEREMONY_NODE
            return mock_ceremony_result
        elif call_count == 2:
            # Second call: CREATE_CEREMONY_PROJECT_RELATIONSHIP
            return mock_ceremony_result
        else:
            # Subsequent calls: CREATE_CEREMONY_STORY_RELATIONSHIP
            story_index = call_count - 3
            if story_index < len(mock_story_results):
                return mock_story_results[story_index]
            return mock_ceremony_result

    mock_tx.run.side_effect = mock_tx_run

    # Execute transaction function
    tx_fn(mock_tx)

    # Verify all relationships were attempted
    assert mock_tx.run.call_count == 2 + len(story_ids)  # ceremony + project + stories

    # Verify CREATE_CEREMONY_STORY_RELATIONSHIP was called for each story
    story_calls = [
        call
        for call in mock_tx.run.call_args_list
        if len(call[0]) > 0
        and call[0][0] == Neo4jQuery.CREATE_CEREMONY_STORY_RELATIONSHIP.value
    ]
    assert len(story_calls) == len(story_ids)

    # Verify each call has correct parameters
    for i, call in enumerate(story_calls):
        _, kwargs = call
        assert kwargs["ceremony_id"] == ceremony_id
        assert kwargs["story_id"] == story_ids[i]


@pytest.mark.asyncio
async def test_save_backlog_review_ceremony_node_handles_missing_record(
    adapter, mock_driver
):
    """Test that save_backlog_review_ceremony_node handles case where result.single() returns None."""
    # Setup mock session
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = None

    ceremony_id = "BRC-TEST-002"
    properties = {
        "created_by": "user-1",
        "status": "DRAFT",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "story_count": 2,
    }
    story_ids = ["story-1", "story-2"]
    # story-1 will succeed, story-2 will return None

    # Mock transaction
    mock_tx = MagicMock()
    call_count = 0

    def mock_tx_run(query, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_result = MagicMock()
        if call_count == 1:
            # Ceremony node creation - always succeeds
            mock_result.single.return_value = MagicMock()
        elif call_count >= 2:
            # Story relationships
            story_index = call_count - 2
            if story_index == 0:
                # story-1: succeeds
                mock_result.single.return_value = MagicMock()
            else:
                # story-2: returns None (warning case)
                mock_result.single.return_value = None
        return mock_result

    mock_tx.run.side_effect = mock_tx_run

    # Mock execute_write to call the transaction function directly
    def mock_execute_write(tx_fn):
        return tx_fn(mock_tx)

    mock_session.execute_write = mock_execute_write

    # Mock retry_operation to call execute_write directly
    adapter._retry_operation = lambda fn, *args, **kwargs: fn(*args, **kwargs)

    # Call method - should raise RuntimeError
    with pytest.raises(RuntimeError, match="Only 1/2 REVIEWS relationships created"):
        await adapter.save_backlog_review_ceremony_node(
            ceremony_id=ceremony_id,
            properties=properties,
            story_ids=story_ids,
            project_id=None,
        )


@pytest.mark.asyncio
async def test_save_backlog_review_ceremony_node_handles_exception(
    adapter, mock_driver
):
    """Test that save_backlog_review_ceremony_node handles exceptions during relationship creation."""
    # Setup mock session
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = None

    ceremony_id = "BRC-TEST-003"
    properties = {
        "created_by": "user-1",
        "status": "DRAFT",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "story_count": 2,
    }
    story_ids = ["story-1", "story-2"]

    # Mock transaction
    mock_tx = MagicMock()
    call_count = 0

    def create_successful_mock_result():
        """Helper to create a successful mock result."""
        mock_result = MagicMock()
        mock_result.single.return_value = MagicMock()
        return mock_result

    def mock_tx_run(query, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Ceremony node creation - succeeds
            return create_successful_mock_result()
        elif call_count == 2:
            # story-1: succeeds
            return create_successful_mock_result()
        else:
            # story-2: raises exception
            raise ValueError("Database error")

    mock_tx.run.side_effect = mock_tx_run

    # Mock execute_write to call the transaction function directly
    def mock_execute_write(tx_fn):
        return tx_fn(mock_tx)

    mock_session.execute_write = mock_execute_write

    # Mock retry_operation to call execute_write directly
    adapter._retry_operation = lambda fn, *args, **kwargs: fn(*args, **kwargs)

    # Call method - should raise ValueError
    with pytest.raises(ValueError, match="Database error"):
        await adapter.save_backlog_review_ceremony_node(
            ceremony_id=ceremony_id,
            properties=properties,
            story_ids=story_ids,
            project_id=None,
        )


@pytest.mark.asyncio
async def test_save_backlog_review_ceremony_node_without_project(
    adapter, mock_driver
):
    """Test that save_backlog_review_ceremony_node works without project_id."""
    # Setup mock session
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = None

    # Mock retry_operation
    adapter._retry_operation = lambda fn, *args, **kwargs: fn(*args, **kwargs)

    ceremony_id = "BRC-TEST-004"
    properties = {
        "created_by": "user-1",
        "status": "DRAFT",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    story_ids = ["story-1"]
    project_id = None  # No project

    await adapter.save_backlog_review_ceremony_node(
        ceremony_id=ceremony_id,
        properties=properties,
        story_ids=story_ids,
        project_id=project_id,
    )

    # Verify execute_write was called
    mock_session.execute_write.assert_called_once()
    tx_fn = mock_session.execute_write.call_args[0][0]

    # Mock transaction
    mock_tx = MagicMock()
    call_count = 0

    def mock_tx_run(query, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_result = MagicMock()
        mock_result.single.return_value = MagicMock()
        return mock_result

    mock_tx.run.side_effect = mock_tx_run

    # Execute transaction function
    tx_fn(mock_tx)

    # Verify CREATE_CEREMONY_PROJECT_RELATIONSHIP was NOT called
    project_calls = [
        call
        for call in mock_tx.run.call_args_list
        if len(call[0]) > 0
        and call[0][0] == Neo4jQuery.CREATE_CEREMONY_PROJECT_RELATIONSHIP.value
    ]
    assert len(project_calls) == 0

    # Verify CREATE_CEREMONY_STORY_RELATIONSHIP was called
    story_calls = [
        call
        for call in mock_tx.run.call_args_list
        if len(call[0]) > 0
        and call[0][0] == Neo4jQuery.CREATE_CEREMONY_STORY_RELATIONSHIP.value
    ]
    assert len(story_calls) == 1


@pytest.mark.asyncio
async def test_save_backlog_review_ceremony_node_empty_stories(
    adapter, mock_driver
):
    """Test that save_backlog_review_ceremony_node handles empty story_ids list."""
    # Setup mock session
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = None

    # Mock retry_operation
    adapter._retry_operation = lambda fn, *args, **kwargs: fn(*args, **kwargs)

    ceremony_id = "BRC-TEST-005"
    properties = {
        "created_by": "user-1",
        "status": "DRAFT",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    story_ids = []  # Empty list

    await adapter.save_backlog_review_ceremony_node(
        ceremony_id=ceremony_id,
        properties=properties,
        story_ids=story_ids,
        project_id=None,
    )

    # Verify execute_write was called
    mock_session.execute_write.assert_called_once()
    tx_fn = mock_session.execute_write.call_args[0][0]

    # Mock transaction
    mock_tx = MagicMock()
    mock_result = MagicMock()
    mock_result.single.return_value = MagicMock()
    mock_tx.run.return_value = mock_result

    # Execute transaction function
    tx_fn(mock_tx)

    # Verify CREATE_CEREMONY_STORY_RELATIONSHIP was NOT called
    story_calls = [
        call
        for call in mock_tx.run.call_args_list
        if len(call[0]) > 0
        and call[0][0] == Neo4jQuery.CREATE_CEREMONY_STORY_RELATIONSHIP.value
    ]
    assert len(story_calls) == 0

    # Verify only ceremony node was created
    assert mock_tx.run.call_count == 1
