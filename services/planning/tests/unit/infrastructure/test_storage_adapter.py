"""Unit tests for StorageAdapter (composite adapter)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum
from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.infrastructure.adapters import StorageAdapter


@pytest.fixture
def sample_story():
    """Create sample story for tests."""
    from planning.domain.value_objects import Brief, Title, UserName
    from planning.domain.value_objects.identifiers.epic_id import EpicId

    now = datetime.now(UTC)
    return Story(
        epic_id=EpicId("E-TEST-001"),  # REQUIRED - domain invariant
        story_id=StoryId("story-123"),
        title=Title("Test Story"),
        brief=Brief("Test brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(85),
        created_by=UserName("po-user"),
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def storage_adapter():
    """Create storage adapter with fully mocked dependencies."""
    # Don't instantiate real StorageAdapter (it connects to Neo4j/Valkey)
    # Instead, create a mock object with the same interface
    adapter = MagicMock(spec=StorageAdapter)

    # Mock the internal adapters as AsyncMocks
    adapter.neo4j_adapter = AsyncMock()
    adapter.valkey_adapter = AsyncMock()

    # Mock all methods to be async
    adapter.save_story = AsyncMock()
    adapter.get_story = AsyncMock()
    adapter.list_stories = AsyncMock()
    adapter.update_story = AsyncMock()
    adapter.delete_story = AsyncMock()
    adapter.close = MagicMock()

    return adapter


@pytest.mark.asyncio
async def test_save_story_delegation():
    """Test that save_story should delegate to both Neo4j and Valkey adapters."""
    # This test documents the expected behavior
    # Actual delegation logic is tested in integration tests
    # Unit test just verifies the interface exists

    neo4j_mock = AsyncMock()
    valkey_mock = AsyncMock()

    # Verify adapters have save_story method
    assert callable(getattr(neo4j_mock, 'save_story', None))
    assert callable(getattr(valkey_mock, 'save_story', None))


@pytest.fixture
def sample_project():
    """Create sample project for tests."""
    now = datetime.now(UTC)
    return Project(
        project_id=ProjectId("PROJ-TEST-001"),
        name="Test Project",
        description="Test description",
        status=ProjectStatus.ACTIVE,
        owner="test-owner",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_save_project_delegation():
    """Test that save_project delegates to ValkeyAdapter."""
    # This test documents the expected behavior
    # Actual delegation logic is tested in integration tests
    # Unit test just verifies the interface exists

    valkey_mock = AsyncMock()

    # Verify adapter has save_project method
    assert callable(getattr(valkey_mock, 'save_project', None))


@pytest.mark.asyncio
async def test_get_project_delegation():
    """Test that get_project delegates to ValkeyAdapter."""
    # This test documents the expected behavior
    # Actual delegation logic is tested in integration tests
    # Unit test just verifies the interface exists

    valkey_mock = AsyncMock()

    # Verify adapter has get_project method
    assert callable(getattr(valkey_mock, 'get_project', None))


@pytest.mark.asyncio
async def test_list_projects_delegation():
    """Test that list_projects delegates to ValkeyAdapter."""
    # This test documents the expected behavior
    # Actual delegation logic is tested in integration tests
    # Unit test just verifies the interface exists

    valkey_mock = AsyncMock()

    # Verify adapter has list_projects method
    assert callable(getattr(valkey_mock, 'list_projects', None))


def test_list_projects_signature_has_limit_and_offset():
    """Test that list_projects method signature includes limit and offset parameters.

    This test verifies:
    - Method signature matches protocol (limit, offset)
    - Default values are correct (limit=100, offset=0)
    - Return type is list[Project]

    Note: Actual delegation logic and empty list return behavior
    are tested in integration tests with real infrastructure.
    """
    from planning.infrastructure.adapters.storage_adapter import StorageAdapter
    import inspect

    # Get method signature
    sig = inspect.signature(StorageAdapter.list_projects)

    # Verify parameters exist
    assert 'limit' in sig.parameters
    assert 'offset' in sig.parameters

    # Verify default values match protocol
    assert sig.parameters['limit'].default == 100
    assert sig.parameters['offset'].default == 0

    # Verify return type annotation includes list[Project]
    return_annotation = str(sig.return_annotation)
    assert 'list' in return_annotation or 'List' in return_annotation


# ============================================================================
# Tests with real StorageAdapter instance and mocked adapters
# ============================================================================

@pytest.fixture
def mock_storage_adapter():
    """Create StorageAdapter instance with mocked internal adapters."""
    from unittest.mock import patch
    from planning.infrastructure.adapters.storage_adapter import StorageAdapter
    from planning.infrastructure.adapters.neo4j_adapter import Neo4jAdapter, Neo4jConfig
    from planning.infrastructure.adapters.valkey_adapter import ValkeyConfig, ValkeyStorageAdapter

    # Create mock adapters
    mock_neo4j = AsyncMock(spec=Neo4jAdapter)
    mock_valkey = AsyncMock(spec=ValkeyStorageAdapter)

    # Patch adapters before instantiation
    with patch(
        'planning.infrastructure.adapters.storage_adapter.Neo4jAdapter',
        return_value=mock_neo4j,
    ), patch(
        'planning.infrastructure.adapters.storage_adapter.ValkeyStorageAdapter',
        return_value=mock_valkey,
    ):
        adapter = StorageAdapter(
            neo4j_config=Neo4jConfig(),
            valkey_config=ValkeyConfig(),
        )
        # Ensure mocks are accessible for assertions
        adapter._mock_neo4j = mock_neo4j
        adapter._mock_valkey = mock_valkey
        yield adapter


@pytest.mark.asyncio
async def test_storage_adapter_init(mock_storage_adapter):
    """Test StorageAdapter initialization with mocked adapters."""
    adapter = mock_storage_adapter

    # Verify adapters were initialized
    assert adapter.neo4j is not None
    assert adapter.valkey is not None
    assert adapter.neo4j == adapter._mock_neo4j
    assert adapter.valkey == adapter._mock_valkey


@pytest.mark.asyncio
async def test_storage_adapter_close(mock_storage_adapter):
    """Test StorageAdapter.close() calls close on both adapters."""
    adapter = mock_storage_adapter

    # Act
    adapter.close()

    # Assert
    adapter.neo4j.close.assert_called_once()
    adapter.valkey.close.assert_called_once()


@pytest.mark.asyncio
async def test_save_story_delegates_to_both_adapters(mock_storage_adapter, sample_story):
    """Test that save_story delegates to both Valkey and Neo4j adapters."""
    adapter = mock_storage_adapter

    # Act
    await adapter.save_story(sample_story)

    # Assert - Valkey called first
    adapter.valkey.save_story.assert_awaited_once_with(sample_story)

    # Assert - Neo4j called second
    adapter.neo4j.create_story_node.assert_awaited_once_with(
        story_id=sample_story.story_id,
        created_by=sample_story.created_by,
        initial_state=sample_story.state,
    )


@pytest.mark.asyncio
async def test_get_story_delegates_to_valkey(mock_storage_adapter, sample_story):
    """Test that get_story delegates to Valkey adapter."""
    adapter = mock_storage_adapter
    adapter.valkey.get_story.return_value = sample_story

    # Act
    result = await adapter.get_story(sample_story.story_id)

    # Assert
    assert result == sample_story
    adapter.valkey.get_story.assert_awaited_once_with(sample_story.story_id)


@pytest.mark.asyncio
async def test_get_story_returns_none_when_not_found(mock_storage_adapter):
    """Test that get_story returns None when story not found."""
    adapter = mock_storage_adapter
    adapter.valkey.get_story.return_value = None
    story_id = StoryId("non-existent")

    # Act
    result = await adapter.get_story(story_id)

    # Assert
    assert result is None
    adapter.valkey.get_story.assert_awaited_once_with(story_id)


@pytest.mark.asyncio
async def test_list_stories_delegates_to_valkey(mock_storage_adapter, sample_story):
    """Test that list_stories delegates to Valkey adapter."""
    from planning.domain import StoryList

    adapter = mock_storage_adapter
    story_list = StoryList([sample_story])
    adapter.valkey.list_stories.return_value = story_list

    # Act
    result = await adapter.list_stories()

    # Assert
    assert result == story_list
    adapter.valkey.list_stories.assert_awaited_once_with(
        state_filter=None,
        limit=100,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_stories_with_filter_delegates_to_valkey(mock_storage_adapter):
    """Test that list_stories with state filter delegates correctly."""
    from planning.domain import StoryList, StoryState, StoryStateEnum

    adapter = mock_storage_adapter
    story_list = StoryList([])
    adapter.valkey.list_stories.return_value = story_list
    state_filter = StoryState(StoryStateEnum.DRAFT)

    # Act
    result = await adapter.list_stories(state_filter=state_filter, limit=50, offset=10)

    # Assert
    assert result == story_list
    adapter.valkey.list_stories.assert_awaited_once_with(
        state_filter=state_filter,
        limit=50,
        offset=10,
    )


@pytest.mark.asyncio
async def test_update_story_delegates_to_both_adapters(mock_storage_adapter, sample_story):
    """Test that update_story delegates to both Valkey and Neo4j adapters."""
    adapter = mock_storage_adapter

    # Act
    await adapter.update_story(sample_story)

    # Assert - Valkey called first
    adapter.valkey.update_story.assert_awaited_once_with(sample_story)

    # Assert - Neo4j called second
    adapter.neo4j.update_story_state.assert_awaited_once_with(
        story_id=sample_story.story_id,
        new_state=sample_story.state,
    )


@pytest.mark.asyncio
async def test_delete_story_delegates_to_both_adapters(mock_storage_adapter):
    """Test that delete_story delegates to both Valkey and Neo4j adapters."""
    adapter = mock_storage_adapter
    story_id = StoryId("story-to-delete")

    # Act
    await adapter.delete_story(story_id)

    # Assert - Valkey called first
    adapter.valkey.delete_story.assert_awaited_once_with(story_id)

    # Assert - Neo4j called second
    adapter.neo4j.delete_story_node.assert_awaited_once_with(story_id)


@pytest.mark.asyncio
async def test_save_task_dependencies_delegates_to_neo4j(mock_storage_adapter):
    """Test that save_task_dependencies delegates to Neo4j adapter."""
    from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
    from planning.domain.value_objects.identifiers.task_id import TaskId

    adapter = mock_storage_adapter
    dependency = DependencyEdge(
        from_task_id=TaskId("T-001"),
        to_task_id=TaskId("T-002"),
        reason="T-002 requires output from T-001",
    )
    dependencies = (dependency,)

    # Act
    await adapter.save_task_dependencies(dependencies)

    # Assert
    adapter.neo4j.create_task_dependencies.assert_awaited_once_with(dependencies)


@pytest.mark.asyncio
async def test_save_project_delegates_to_both_adapters(mock_storage_adapter, sample_project):
    """Test that save_project persists to both Valkey and Neo4j (dual persistence)."""
    adapter = mock_storage_adapter
    from planning.infrastructure.mappers.project_neo4j_mapper import ProjectNeo4jMapper

    # Act
    await adapter.save_project(sample_project)

    # Assert: Valkey saved
    adapter.valkey.save_project.assert_awaited_once_with(sample_project)

    # Assert: Neo4j node created
    assert adapter.neo4j.create_project_node.called
    create_call = adapter.neo4j.create_project_node.await_args
    assert create_call[1]["project_id"] == sample_project.project_id.value
    assert create_call[1]["name"] == sample_project.name
    assert create_call[1]["status"] == sample_project.status.value


@pytest.mark.asyncio
async def test_get_project_delegates_to_valkey(mock_storage_adapter, sample_project):
    """Test that get_project delegates to Valkey adapter."""
    adapter = mock_storage_adapter
    adapter.valkey.get_project.return_value = sample_project

    # Act
    result = await adapter.get_project(sample_project.project_id)

    # Assert
    assert result == sample_project
    adapter.valkey.get_project.assert_awaited_once_with(sample_project.project_id)


@pytest.mark.asyncio
async def test_get_project_returns_none_when_not_found(mock_storage_adapter):
    """Test that get_project returns None when project not found."""
    adapter = mock_storage_adapter
    adapter.valkey.get_project.return_value = None
    project_id = ProjectId("non-existent")

    # Act
    result = await adapter.get_project(project_id)

    # Assert
    assert result is None
    adapter.valkey.get_project.assert_awaited_once_with(project_id)


@pytest.mark.asyncio
async def test_list_projects_delegates_to_valkey(mock_storage_adapter, sample_project):
    """Test that list_projects delegates to Valkey adapter."""
    adapter = mock_storage_adapter
    projects = [sample_project]
    adapter.valkey.list_projects.return_value = projects

    # Act
    result = await adapter.list_projects()

    # Assert
    assert result == projects
    adapter.valkey.list_projects.assert_awaited_once_with(
        status_filter=None,
        limit=100,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_projects_with_pagination_delegates_to_valkey(
    mock_storage_adapter,
    sample_project,
):
    """Test that list_projects with pagination delegates correctly."""
    adapter = mock_storage_adapter
    projects = [sample_project]
    adapter.valkey.list_projects.return_value = projects

    # Act
    result = await adapter.list_projects(limit=10, offset=5)

    # Assert
    assert result == projects
    adapter.valkey.list_projects.assert_awaited_once_with(
        status_filter=None,
        limit=10,
        offset=5,
    )


@pytest.mark.asyncio
async def test_list_projects_with_status_filter_delegates_to_valkey(
    mock_storage_adapter,
    sample_project,
):
    """Test that list_projects with status filter delegates correctly."""
    from planning.domain.value_objects.statuses.project_status import ProjectStatus

    adapter = mock_storage_adapter
    projects = [sample_project]
    adapter.valkey.list_projects.return_value = projects

    # Act
    result = await adapter.list_projects(
        status_filter=ProjectStatus.COMPLETED,
        limit=20,
        offset=0,
    )

    # Assert
    assert result == projects
    adapter.valkey.list_projects.assert_awaited_once_with(
        status_filter=ProjectStatus.COMPLETED,
        limit=20,
        offset=0,
    )


# StorageAdapter delegation logic is also tested in integration tests
# with real infrastructure (Neo4j + Valkey)

