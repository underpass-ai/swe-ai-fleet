from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.epic_status import EpicStatus
from planning.infrastructure.adapters.storage_adapter import StorageAdapter


@pytest.fixture
def mock_neo4j():
    return AsyncMock()

@pytest.fixture
def mock_valkey():
    return AsyncMock()

@pytest.fixture
def storage_adapter(mock_neo4j, mock_valkey):
    with patch("planning.infrastructure.adapters.storage_adapter.Neo4jAdapter", return_value=mock_neo4j), \
         patch("planning.infrastructure.adapters.storage_adapter.ValkeyStorageAdapter", return_value=mock_valkey):
        return StorageAdapter()

@pytest.fixture
def sample_epic():
    return Epic(
        epic_id=EpicId("epic-123"),
        project_id=ProjectId("proj-456"),
        title="Sample Epic",
        description="Desc",
        status=EpicStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

@pytest.mark.asyncio
async def test_save_epic_delegates_to_both_adapters(storage_adapter, mock_neo4j, mock_valkey, sample_epic):
    """Test that save_epic calls both Valkey and Neo4j adapters."""

    await storage_adapter.save_epic(sample_epic)

    # Check Valkey call
    mock_valkey.save_epic.assert_awaited_once_with(sample_epic)

    # Check Neo4j call with flattened properties
    mock_neo4j.create_epic_node.assert_awaited_once()
    call_kwargs = mock_neo4j.create_epic_node.call_args.kwargs
    assert call_kwargs["epic_id"] == "epic-123"
    assert call_kwargs["project_id"] == "proj-456"
    assert call_kwargs["name"] == "Sample Epic"
    assert call_kwargs["status"] == "active"

@pytest.mark.asyncio
async def test_get_epic_delegates_to_valkey(storage_adapter, mock_valkey):
    """Test that get_epic delegates to Valkey only."""
    epic_id = EpicId("epic-123")
    expected_epic = MagicMock(spec=Epic)
    mock_valkey.get_epic.return_value = expected_epic

    result = await storage_adapter.get_epic(epic_id)

    assert result == expected_epic
    mock_valkey.get_epic.assert_awaited_once_with(epic_id)

@pytest.mark.asyncio
async def test_list_epics_delegates_to_valkey(storage_adapter, mock_valkey):
    """Test that list_epics delegates to Valkey."""
    project_id = ProjectId("proj-123")
    expected_epics = [MagicMock(spec=Epic)]
    mock_valkey.list_epics.return_value = expected_epics

    result = await storage_adapter.list_epics(project_id=project_id, limit=10, offset=5)

    assert result == expected_epics
    mock_valkey.list_epics.assert_awaited_once_with(project_id=project_id, limit=10, offset=5)


@pytest.mark.asyncio
async def test_delete_epic_delegates_to_both_adapters(storage_adapter, mock_neo4j, mock_valkey):
    """Test that delete_epic calls both Valkey and Neo4j adapters."""
    epic_id = EpicId("epic-123")

    await storage_adapter.delete_epic(epic_id)

    # Check Valkey call
    mock_valkey.delete_epic.assert_awaited_once_with(epic_id)

    # Check Neo4j call with string ID
    mock_neo4j.delete_epic_node.assert_awaited_once_with(epic_id.value)

