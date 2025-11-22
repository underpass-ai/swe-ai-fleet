"""Integration tests for StorageAdapter with real Neo4j + Valkey."""

from datetime import UTC, datetime

import pytest
from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum
from planning.infrastructure.adapters import Neo4jConfig, StorageAdapter, ValkeyConfig


@pytest.fixture
async def storage_adapter():
    """Create StorageAdapter with real Neo4j + Valkey."""
    neo4j_config = Neo4jConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="test",
    )

    valkey_config = ValkeyConfig(
        host="localhost",
        port=6379,
        db=0,
    )

    adapter = StorageAdapter(
        neo4j_config=neo4j_config,
        valkey_config=valkey_config,
    )

    yield adapter

    # Cleanup
    adapter.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_get_story(storage_adapter):
    """Test saving and retrieving a story."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-integration-001"),
        title="Integration test story",
        brief="Testing dual persistence",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="test-po",
        created_at=now,
        updated_at=now,
    )

    # Save to both Neo4j and Valkey
    await storage_adapter.save_story(story)

    # Retrieve (should hit cache first)
    retrieved = await storage_adapter.get_story(StoryId("s-integration-001"))

    assert retrieved is not None
    assert retrieved.story_id.value == "s-integration-001"
    assert retrieved.title == "Integration test story"
    assert retrieved.state.value == StoryStateEnum.DRAFT


@pytest.mark.integration
@pytest.mark.asyncio
async def test_story_graph_node_created(storage_adapter):
    """Test that Neo4j graph node is created with minimal properties."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-integration-002"),
        title="Graph test",
        brief="Testing Neo4j graph structure",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="test-po",
        created_at=now,
        updated_at=now,
    )

    # Save to both stores
    await storage_adapter.save_story(story)

    # Verify graph node exists (Neo4j has structure, Valkey has details)
    story_ids_in_draft = await storage_adapter.neo4j.get_story_ids_by_state(
        StoryState(StoryStateEnum.DRAFT)
    )

    assert "s-integration-002" in story_ids_in_draft


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_story(storage_adapter):
    """Test updating a story."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-integration-003"),
        title="Original title",
        brief="Original brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="test-po",
        created_at=now,
        updated_at=now,
    )

    await storage_adapter.save_story(story)

    # Update story
    updated = story.update_content(title="Updated title", brief="Updated brief")
    await storage_adapter.update_story(updated)

    # Retrieve and verify
    retrieved = await storage_adapter.get_story(StoryId("s-integration-003"))
    assert retrieved.title == "Updated title"
    assert retrieved.brief == "Updated brief"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_stories(storage_adapter):
    """Test listing stories."""
    now = datetime.now(UTC)

    # Create multiple stories
    for i in range(5):
        story = Story(
            story_id=StoryId(f"s-integration-list-{i}"),
            title=f"Story {i}",
            brief=f"Brief {i}",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(i * 20),
            created_by="test-po",
            created_at=now,
            updated_at=now,
        )
        await storage_adapter.save_story(story)

    # List all stories
    stories = await storage_adapter.list_stories(limit=10)

    # Should include our test stories (plus potentially others)
    story_ids = [s.story_id.value for s in stories]
    assert "s-integration-list-0" in story_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_story(storage_adapter):
    """Test deleting a story from both stores."""
    now = datetime.now(UTC)
    story = Story(
        story_id=StoryId("s-integration-delete"),
        title="To be deleted",
        brief="Will be removed",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="test-po",
        created_at=now,
        updated_at=now,
    )

    await storage_adapter.save_story(story)

    # Verify it exists
    retrieved = await storage_adapter.get_story(StoryId("s-integration-delete"))
    assert retrieved is not None

    # Delete
    await storage_adapter.delete_story(StoryId("s-integration-delete"))

    # Verify it's gone
    deleted = await storage_adapter.get_story(StoryId("s-integration-delete"))
    assert deleted is None

