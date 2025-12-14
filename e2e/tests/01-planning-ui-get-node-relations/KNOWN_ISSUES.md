# Known Issues in E2E Test

## ~~Issue: Story nodes missing `title` property in Neo4j~~ ✅ FIXED

### Problem (RESOLVED)
~~The E2E test fails at Step 4 (`GetGraphRelationships`) with:~~
```
StatusCode.INVALID_ARGUMENT - Node title is required but missing for node: {story_id}
```

**Status: FIXED** - Planning Service now saves `title` in Neo4j when creating Story nodes.

### Root Cause
1. **Planning Service** saves Story nodes to Neo4j without the `title` property:
   - Query `CREATE_STORY_NODE` (in `services/planning/infrastructure/adapters/neo4j_queries.py`) only saves:
     - `s.id = $story_id`
     - `s.state = $state`
   - Does NOT save `s.title`

2. **Context Service** requires `title` for all nodes in `GetGraphRelationships`:
   - Query expects `title: n.title` (line 83 in `services/context/infrastructure/neo4j_graph_queries.py`)
   - Domain service `GraphRelationshipsBuilder._build_main_node` validates `title` exists (line 83-84)
   - Raises `ValueError` if `title` is missing

3. **Same issue for neighbors**: Query expects `title: neighbor.title` (line 69) and validates in `_build_neighbor_node` (line 170-172)

### Impact
- `GetGraphRelationships` fails for any Story node created by Planning Service
- Planning UI cannot display graph relationships for Stories
- Affects all Stories created via `CreateStory` gRPC endpoint

### Solution (IMPLEMENTED)
Planning Service has been modified to save `title` in Neo4j when creating Story nodes:

1. ✅ **Updated `CREATE_STORY_NODE` query** to include `title`:
   ```cypher
   MERGE (s:Story {id: $story_id})
   SET s.state = $state,
       s.title = $title
   ```

2. ✅ **Updated `create_story_node` method signature** to accept `title`:
   ```python
   async def create_story_node(
       self,
       story_id: StoryId,
       title: Title,  # Added
       created_by: str,
       initial_state: StoryState,
   ) -> None:
   ```

3. ✅ **Updated `save_story` in `StorageAdapter`** to pass `title`:
   ```python
   await self.neo4j.create_story_node(
       story_id=story.story_id,
       title=story.title,  # Added
       created_by=story.created_by.value,
       initial_state=story.state,
   )
   ```

4. ✅ **Updated query execution** to pass `title` parameter:
   ```python
   tx.run(
       Neo4jQuery.CREATE_STORY_NODE.value,
       story_id=story_id.value,
       title=title.value,  # Added
       state=initial_state.to_string(),
       created_by=created_by,
   )
   ```

5. ✅ **Updated all unit tests** to include `title` parameter in test cases.

**Implementation Date:** 2025-01-XX
**Files Modified:**
- `services/planning/infrastructure/adapters/neo4j_queries.py`
- `services/planning/infrastructure/adapters/neo4j_adapter.py`
- `services/planning/infrastructure/adapters/storage_adapter.py`
- `services/planning/tests/unit/infrastructure/test_neo4j_adapter_unit.py`
- `services/planning/tests/unit/infrastructure/test_storage_adapter.py`
- `services/planning/tests/unit/infrastructure/test_neo4j_queries.py`

### Related Files
- `services/planning/infrastructure/adapters/neo4j_queries.py` - `CREATE_STORY_NODE` query
- `services/planning/infrastructure/adapters/neo4j_adapter.py` - `create_story_node` method
- `services/planning/infrastructure/adapters/storage_adapter.py` - `save_story` method
- `services/context/infrastructure/neo4j_graph_queries.py` - `GetGraphRelationships` query
- `core/context/domain/services/graph_relationships_builder.py` - Domain validation

### Test Status
- ✅ Test correctly creates Project → Epic → Story hierarchy
- ✅ Test correctly creates and starts Backlog Review Ceremony
- ✅ Test correctly waits for async processing
- ✅ Test should now pass at `GetGraphRelationships` (bug fixed)

The test itself is **functionally correct** - it properly exercises the E2E flow using gRPC endpoints. The bug has been fixed in Planning Service.
