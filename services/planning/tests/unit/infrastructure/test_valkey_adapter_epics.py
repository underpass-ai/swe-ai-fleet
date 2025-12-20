"""Unit tests for ValkeyStorageAdapter Epic methods - New functionality."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.epic_status import EpicStatus
from planning.infrastructure.adapters.valkey_adapter import ValkeyStorageAdapter
from planning.infrastructure.adapters.valkey_config import ValkeyConfig
from planning.infrastructure.adapters.valkey_keys import ValkeyKeys


@pytest.fixture
def mock_redis_client():
    """Create mock Valkey client."""
    client = MagicMock()
    client.ping.return_value = True
    return client


@pytest.fixture
def valkey_adapter(mock_redis_client):
    """Create ValkeyStorageAdapter with mocked Valkey client."""
    with patch('planning.infrastructure.adapters.valkey_adapter.valkey.Valkey', return_value=mock_redis_client):
        adapter = ValkeyStorageAdapter(ValkeyConfig())
        adapter.client = mock_redis_client
        return adapter


@pytest.fixture
def sample_epic():
    """Create sample epic for testing."""
    return Epic(
        epic_id=EpicId("E-123"),
        project_id=ProjectId("PROJ-456"),
        title="Test Epic",
        description="Test description",
        status=EpicStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_delete_epic_with_project_id(valkey_adapter):
    """Test delete_epic removes epic from hash, all_epics set, and project set."""
    epic_id = EpicId("E-123")

    # Mock: epic has project_id
    valkey_adapter.client.hget.return_value = "PROJ-456"

    # Execute
    await valkey_adapter.delete_epic(epic_id)

    # Verify hash deleted
    hash_key = valkey_adapter._epic_hash_key(epic_id)
    valkey_adapter.client.delete.assert_called_with(hash_key)

    # Verify removed from all_epics set
    all_epics_key = valkey_adapter._all_epics_set_key()
    valkey_adapter.client.srem.assert_any_call(all_epics_key, epic_id.value)

    # Verify removed from project set
    project_key = valkey_adapter._epics_by_project_key(ProjectId("PROJ-456"))
    valkey_adapter.client.srem.assert_any_call(project_key, epic_id.value)


@pytest.mark.asyncio
async def test_delete_epic_without_project_id(valkey_adapter):
    """Test delete_epic handles epic without project_id (no project set removal)."""
    epic_id = EpicId("E-456")

    # Mock: epic has no project_id (None)
    valkey_adapter.client.hget.return_value = None

    # Execute
    await valkey_adapter.delete_epic(epic_id)

    # Verify hash deleted
    hash_key = valkey_adapter._epic_hash_key(epic_id)
    valkey_adapter.client.delete.assert_called_with(hash_key)

    # Verify removed from all_epics set
    all_epics_key = valkey_adapter._all_epics_set_key()
    valkey_adapter.client.srem.assert_any_call(all_epics_key, epic_id.value)

    # Verify no project set removal (project_id_str was None)
    srem_calls = [call[0][0] for call in valkey_adapter.client.srem.call_args_list]
    project_keys = [key for key in srem_calls if "project" in key]
    assert len(project_keys) == 0  # No project set removal
