"""Unit tests for ValkeyStorageAdapter Project methods - New functionality."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus
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
def sample_project():
    """Create sample project for testing."""
    return Project(
        project_id=ProjectId("PROJ-123"),
        name="Test Project",
        description="Test description",
        status=ProjectStatus.ACTIVE,
        owner="test-owner",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_projects_by_status_key(valkey_adapter):
    """Test _projects_by_status_key generates correct key."""
    key = valkey_adapter._projects_by_status_key("active")
    assert key == "planning:projects:status:active"
    assert key == ValkeyKeys.projects_by_status("active")


@pytest.mark.asyncio
async def test_save_project_first_time(valkey_adapter, sample_project):
    """Test save_project when project doesn't exist (first time)."""
    # Mock: project doesn't exist (HGET returns None)
    valkey_adapter.client.hget.return_value = None

    # Execute
    await valkey_adapter.save_project(sample_project)

    # Verify hash saved
    hash_key = valkey_adapter._project_hash_key(sample_project.project_id)
    assert valkey_adapter.client.hset.called
    hset_call = valkey_adapter.client.hset.call_args
    assert hset_call[0][0] == hash_key

    # Verify added to all_projects set
    assert valkey_adapter.client.sadd.called
    all_projects_key = valkey_adapter._all_projects_set_key()
    assert any(call[0][0] == all_projects_key for call in valkey_adapter.client.sadd.call_args_list)

    # Verify added to status set
    status_key = valkey_adapter._projects_by_status_key("active")
    assert any(call[0][0] == status_key for call in valkey_adapter.client.sadd.call_args_list)


@pytest.mark.asyncio
async def test_save_project_with_status_change(valkey_adapter, sample_project):
    """Test save_project when status changes (removes from old set, adds to new)."""
    # Mock: project exists with old status
    valkey_adapter.client.hget.return_value = "planning"  # Old status

    # Create project with new status
    updated_project = Project(
        project_id=sample_project.project_id,
        name=sample_project.name,
        description=sample_project.description,
        status=ProjectStatus.COMPLETED,  # Changed from PLANNING
        owner=sample_project.owner,
        created_at=sample_project.created_at,
        updated_at=datetime.now(UTC),
    )

    # Execute
    await valkey_adapter.save_project(updated_project)

    # Verify old status removed
    assert valkey_adapter.client.srem.called
    old_status_key = valkey_adapter._projects_by_status_key("planning")
    srem_calls = [call[0][0] for call in valkey_adapter.client.srem.call_args_list]
    assert old_status_key in srem_calls

    # Verify new status added
    new_status_key = valkey_adapter._projects_by_status_key("completed")
    sadd_calls = [call[0][0] for call in valkey_adapter.client.sadd.call_args_list]
    assert new_status_key in sadd_calls


@pytest.mark.asyncio
async def test_save_project_no_status_change(valkey_adapter, sample_project):
    """Test save_project when status doesn't change (no set operations)."""
    # Mock: project exists with same status
    valkey_adapter.client.hget.return_value = "active"  # Same status

    # Execute
    await valkey_adapter.save_project(sample_project)

    # Verify no SREM called (status didn't change)
    assert not valkey_adapter.client.srem.called

    # Verify SADD still called (idempotent operation)
    assert valkey_adapter.client.sadd.called


def test_list_projects_sync_no_filter(valkey_adapter):
    """Test _list_projects_sync without status filter."""
    # Mock: all projects set returns IDs
    valkey_adapter.client.smembers.return_value = {"PROJ-001", "PROJ-002", "PROJ-003"}

    # Mock: get_project_sync returns projects
    project1 = Project(
        project_id=ProjectId("PROJ-001"),
        name="Project 1",
        status=ProjectStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    project2 = Project(
        project_id=ProjectId("PROJ-002"),
        name="Project 2",
        status=ProjectStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    project3 = Project(
        project_id=ProjectId("PROJ-003"),
        name="Project 3",
        status=ProjectStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    valkey_adapter._get_project_sync = MagicMock(side_effect=[project1, project2, project3])

    # Execute
    result = valkey_adapter._list_projects_sync(None, limit=10, offset=0)

    # Verify used all_projects set
    assert valkey_adapter.client.smembers.called
    smembers_call = valkey_adapter.client.smembers.call_args
    assert smembers_call[0][0] == valkey_adapter._all_projects_set_key()

    # Verify results
    assert len(result) == 3
    assert result[0].project_id.value == "PROJ-001"
    assert result[1].project_id.value == "PROJ-002"
    assert result[2].project_id.value == "PROJ-003"


def test_list_projects_sync_with_status_filter(valkey_adapter):
    """Test _list_projects_sync with status filter."""
    # Mock: filtered set returns only matching IDs
    valkey_adapter.client.smembers.return_value = {"PROJ-002", "PROJ-004"}

    project2 = Project(
        project_id=ProjectId("PROJ-002"),
        name="Project 2",
        status=ProjectStatus.COMPLETED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    project4 = Project(
        project_id=ProjectId("PROJ-004"),
        name="Project 4",
        status=ProjectStatus.COMPLETED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    valkey_adapter._get_project_sync = MagicMock(side_effect=[project2, project4])

    # Execute with status filter
    result = valkey_adapter._list_projects_sync(ProjectStatus.COMPLETED, limit=10, offset=0)

    # Verify used status-filtered set
    smembers_call = valkey_adapter.client.smembers.call_args
    expected_key = valkey_adapter._projects_by_status_key("completed")
    assert smembers_call[0][0] == expected_key

    # Verify results
    assert len(result) == 2
    assert all(p.status == ProjectStatus.COMPLETED for p in result)


def test_list_projects_sync_with_pagination(valkey_adapter):
    """Test _list_projects_sync applies pagination correctly."""
    # Mock: 5 projects in set
    valkey_adapter.client.smembers.return_value = {
        "PROJ-001", "PROJ-002", "PROJ-003", "PROJ-004", "PROJ-005"
    }

    # Mock: return projects for paginated IDs
    def mock_get_project(project_id):
        return Project(
            project_id=project_id,
            name=f"Project {project_id.value}",
            status=ProjectStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    valkey_adapter._get_project_sync = MagicMock(side_effect=mock_get_project)

    # Execute with pagination: limit=2, offset=1
    result = valkey_adapter._list_projects_sync(None, limit=2, offset=1)

    # Verify only 2 projects returned (after offset 1)
    assert len(result) == 2
    # Verify sorted IDs (sorted list means PROJ-002, PROJ-003 should be returned)
    assert result[0].project_id.value in ["PROJ-002", "PROJ-003"]


def test_list_projects_sync_sorts_ids(valkey_adapter):
    """Test _list_projects_sync sorts project IDs."""
    # Mock: unsorted set
    valkey_adapter.client.smembers.return_value = {"PROJ-003", "PROJ-001", "PROJ-002"}

    def mock_get_project(project_id):
        return Project(
            project_id=project_id,
            name=f"Project {project_id.value}",
            status=ProjectStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    valkey_adapter._get_project_sync = MagicMock(side_effect=mock_get_project)

    # Execute
    result = valkey_adapter._list_projects_sync(None, limit=10, offset=0)

    # Verify results are sorted by ID
    ids = [p.project_id.value for p in result]
    assert ids == sorted(ids)


def test_list_projects_sync_filters_none_projects(valkey_adapter):
    """Test _list_projects_sync filters out None results (defensive)."""
    # Mock: set returns IDs
    valkey_adapter.client.smembers.return_value = {"PROJ-001", "PROJ-002", "PROJ-003"}

    # Mock: one project not found (returns None)
    project1 = Project(
        project_id=ProjectId("PROJ-001"),
        name="Project 1",
        status=ProjectStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    valkey_adapter._get_project_sync = MagicMock(side_effect=[project1, None, project1])

    # Execute
    result = valkey_adapter._list_projects_sync(None, limit=10, offset=0)

    # Verify None filtered out
    assert len(result) == 2
    assert all(p is not None for p in result)


@pytest.mark.asyncio
async def test_list_projects_async_delegates_to_sync(valkey_adapter):
    """Test list_projects async method delegates to sync version."""
    valkey_adapter._list_projects_sync = MagicMock(return_value=[])

    result = await valkey_adapter.list_projects(
        status_filter=None,
        limit=10,
        offset=0,
    )

    assert valkey_adapter._list_projects_sync.called
    valkey_adapter._list_projects_sync.assert_called_once_with(None, 10, 0)
    assert result == []


@pytest.mark.asyncio
async def test_list_projects_with_status_filter(valkey_adapter):
    """Test list_projects with status filter passes filter to sync method."""
    valkey_adapter._list_projects_sync = MagicMock(return_value=[])

    await valkey_adapter.list_projects(
        status_filter=ProjectStatus.COMPLETED,
        limit=20,
        offset=5,
    )

    valkey_adapter._list_projects_sync.assert_called_once_with(
        ProjectStatus.COMPLETED,
        20,
        5,
    )


@pytest.mark.asyncio
async def test_delete_project_with_status(valkey_adapter):
    """Test delete_project removes project from hash, all_projects set, and status set."""
    project_id = ProjectId("PROJ-123")

    # Mock: project has status
    valkey_adapter.client.hget.return_value = "active"

    # Execute
    await valkey_adapter.delete_project(project_id)

    # Verify hash deleted
    hash_key = valkey_adapter._project_hash_key(project_id)
    valkey_adapter.client.delete.assert_called_with(hash_key)

    # Verify removed from all_projects set
    all_projects_key = valkey_adapter._all_projects_set_key()
    valkey_adapter.client.srem.assert_any_call(all_projects_key, project_id.value)

    # Verify removed from status set
    status_key = valkey_adapter._projects_by_status_key("active")
    valkey_adapter.client.srem.assert_any_call(status_key, project_id.value)


@pytest.mark.asyncio
async def test_delete_project_without_status(valkey_adapter):
    """Test delete_project handles project without status (no status set removal)."""
    project_id = ProjectId("PROJ-456")

    # Mock: project has no status (None)
    valkey_adapter.client.hget.return_value = None

    # Execute
    await valkey_adapter.delete_project(project_id)

    # Verify hash deleted
    hash_key = valkey_adapter._project_hash_key(project_id)
    valkey_adapter.client.delete.assert_called_with(hash_key)

    # Verify removed from all_projects set
    all_projects_key = valkey_adapter._all_projects_set_key()
    valkey_adapter.client.srem.assert_any_call(all_projects_key, project_id.value)

    # Verify no status set removal (status_str was None)
    srem_calls = [call[0][0] for call in valkey_adapter.client.srem.call_args_list]
    status_keys = [key for key in srem_calls if "status" in key]
    assert len(status_keys) == 0  # No status set removal

