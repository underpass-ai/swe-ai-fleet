# PR: Implement Epic Persistence and Story Filtering by Epic

## Summary
This PR implements full persistence for Epics in the Planning Service (using the dual-storage pattern: Neo4j + Valkey) and adds the ability to filter Stories by their parent Epic. This is a foundational step for the upcoming hierarchy refactor (Story -> Task).

## Changes

### 1. Epic Persistence (Dual Storage)
- **Infrastructure**: Implemented `save_epic` in `StorageAdapter` to persist data to both:
  - **Valkey**: Stores full Epic details (title, description, status, timestamps) for fast access.
  - **Neo4j**: Stores the Epic node and its relationship to the Project (`BELONGS_TO`).
- **Mappers**: Added `EpicNeo4jMapper` to handle domain-to-graph property conversion.
- **Neo4j Adapter**: Added methods `create_epic_node`, `update_epic_status`, and queries for Epic management.

### 2. Story Filtering by Epic
- **Valkey Adapter**: Added indexing for Stories by Epic ID (`planning:stories:epic:{epic_id}`).
- **Use Case**: Updated `ListStoriesUseCase` to accept an optional `epic_id` filter.
- **gRPC API**: Updated `planning.proto` to include `epic_id` in `ListStoriesRequest` and regenerated stubs.
- **Handler**: Updated `list_stories_handler` to pass the `epic_id` from the request to the use case.

### 3. Testing & Verification
- **Unit Tests**: Added comprehensive unit tests for:
  - `EpicNeo4jMapper` (covering property mapping and validation).
  - `Neo4jAdapter` (covering Epic node creation and queries).
  - `StorageAdapter` (covering the delegation to both persistence layers).
- **Manual Verification**:
  - Verified in live cluster that creating an Epic persists it to both Valkey and Neo4j.
  - Verified that `ListStories` can now filter by Epic.
  - Performed data cleanup (deleted old Epics) to ensure a clean state for the refactor.

## Files Modified
- `services/planning/application/ports/storage_port.py`
- `services/planning/application/usecases/list_stories_usecase.py`
- `services/planning/infrastructure/adapters/neo4j_adapter.py`
- `services/planning/infrastructure/adapters/neo4j_queries.py`
- `services/planning/infrastructure/adapters/storage_adapter.py`
- `services/planning/infrastructure/adapters/valkey_adapter.py`
- `services/planning/infrastructure/adapters/valkey_keys.py`
- `services/planning/infrastructure/grpc/handlers/list_stories_handler.py`
- `services/planning/infrastructure/mappers/epic_neo4j_mapper.py` (New)
- `specs/fleet/planning/v2/planning.proto`

## Impact Analysis
- **API Changes**: `ListStoriesRequest` now has an optional `epic_id` field. This is backward compatible (optional field).
- **Data Model**: New Redis keys for Epic-Story indexing (`planning:stories:epic:{epic_id}`). Existing stories will need re-indexing if we wanted to support them, but we performed a clean slate wipe for this environment.
- **Dependencies**: No new external dependencies.

## Next Steps
- Proceed with Phase 1 of the Hierarchy Refactor: Modifying the `Task` entity to belong directly to `Story`.

## Git Diff (origin/main...HEAD)

```
 coverage.json                                      |    2 +-
 deploy/k8s/00-foundation/planning-ui.yaml          |    2 +-
 scripts/infra/fresh-redeploy.sh                    |    2 +-
 services/planning-ui/Dockerfile                    |   24 +-
 services/planning-ui/GRPC_INTEGRATION.md           |  142 -
 services/planning-ui/Makefile                      |    2 +-
 services/planning-ui/README.md                     |   12 +-
 services/planning-ui/package-lock.json             | 3195 +++++++++++++++++++-
 services/planning-ui/package.json                  |   17 +-
 services/planning-ui/scripts/generate-grpc.js      |   90 +
 .../planning-ui/src/lib/__tests__/config.test.ts   |  106 +
 .../src/lib/__tests__/grpc-client.test.ts          |  578 ++++
 services/planning-ui/src/lib/config.ts             |   19 +-
 services/planning-ui/src/lib/grpc-client.ts        |  323 ++
 .../planning-ui/src/lib/grpc-request-builders.ts   |  334 ++
 .../src/pages/api/__tests__/epics.test.ts          |  365 +++
 .../src/pages/api/__tests__/projects.test.ts       |  519 ++++
 .../src/pages/api/__tests__/stories.test.ts        |  663 ++++
 .../src/pages/api/__tests__/tasks.test.ts          |  245 ++
 services/planning-ui/src/pages/api/epics/index.ts  |   96 +-
 .../planning-ui/src/pages/api/projects/[id].ts     |   51 +-
 .../planning-ui/src/pages/api/projects/index.ts    |   97 +-
 services/planning-ui/src/pages/api/stories/[id].ts |   52 +-
 .../src/pages/api/stories/[id]/transition.ts       |   53 +-
 .../planning-ui/src/pages/api/stories/index.ts     |   98 +-
 services/planning-ui/src/pages/api/tasks/index.ts  |   41 +-
 services/planning-ui/src/pages/epics/index.astro   |    5 +-
 services/planning-ui/src/pages/projects/[id].astro |    3 +-
 .../planning-ui/src/pages/projects/index.astro     |    3 +-
 services/planning-ui/src/pages/stories/[id].astro  |    3 +-
 services/planning-ui/src/pages/stories/index.astro |    5 +-
 services/planning-ui/vitest.config.ts              |   38 +
 .../planning/application/ports/storage_port.py     |   13 +-
 .../services/task_derivation_result_service.py     |    4 +-
 .../application/usecases/create_epic_usecase.py    |    2 +-
 .../application/usecases/create_project_usecase.py |    2 +-
 .../application/usecases/create_task_usecase.py    |    2 +-
 .../usecases/derive_tasks_from_plan_usecase.py     |    2 +-
 .../application/usecases/list_epics_usecase.py     |   19 +-
 .../application/usecases/list_projects_usecase.py  |   31 +-
 .../application/usecases/list_stories_usecase.py   |    5 +
 .../infrastructure/adapters/neo4j_adapter.py       |  251 ++
 .../infrastructure/adapters/neo4j_queries.py       |   56 +
 .../infrastructure/adapters/storage_adapter.py     |  155 +
 .../infrastructure/adapters/valkey_adapter.py      |  374 ++-
 .../infrastructure/adapters/valkey_keys.py         |   89 +
 .../grpc/handlers/get_project_handler.py           |    6 +-
 .../grpc/handlers/list_projects_handler.py         |   25 +-
 .../grpc/handlers/list_stories_handler.py          |    5 +-
 .../infrastructure/grpc/mappers/response_mapper.py |   20 +-
 .../infrastructure/mappers/datetime_formatter.py   |   31 +
 .../infrastructure/mappers/epic_neo4j_mapper.py    |  103 +
 .../infrastructure/mappers/epic_valkey_mapper.py   |   87 +
 .../infrastructure/mappers/project_neo4j_mapper.py |   98 +
 .../mappers/project_valkey_mapper.py               |   86 +
 .../mappers/story_protobuf_mapper.py               |    5 +-
 .../unit/application/test_create_epic_usecase.py   |    2 +-
 .../application/test_create_project_usecase.py     |    5 +-
 .../unit/application/test_create_task_usecase.py   |    2 +-
 .../test_derive_tasks_from_plan_usecase.py         |    6 +-
 .../unit/application/test_get_project_usecase.py   |   99 +
 .../unit/application/test_list_epics_usecase.py    |   64 +
 .../unit/application/test_list_projects_usecase.py |  249 ++
 .../test_task_derivation_result_service.py         |    9 +-
 .../grpc/handlers/test_list_projects_handler.py    |  208 +-
 .../mappers/test_epic_neo4j_mapper.py              |  108 +
 .../mappers/test_project_neo4j_mapper.py           |  293 ++
 .../unit/infrastructure/test_datetime_formatter.py |  101 +
 .../unit/infrastructure/test_epic_valkey_mapper.py |  213 ++
 .../unit/infrastructure/test_neo4j_adapter.py      |   10 +-
 .../infrastructure/test_neo4j_adapter_epics.py     |  101 +
 .../infrastructure/test_neo4j_adapter_projects.py  |  312 ++
 .../unit/infrastructure/test_neo4j_queries.py      |    4 +-
 .../infrastructure/test_project_valkey_mapper.py   |  212 ++
 .../unit/infrastructure/test_storage_adapter.py    |  425 ++-
 .../infrastructure/test_storage_adapter_epics.py   |   77 +
 .../unit/infrastructure/test_valkey_adapter.py     |   16 +-
 .../infrastructure/test_valkey_adapter_projects.py |  313 ++
 .../tests/unit/infrastructure/test_valkey_keys.py  |   64 +
 specs/fleet/planning/v2/planning.proto             |    1 +
 tmp_docs/ARQUITECTURA_EVENTOS.md                   |  151 +
 tmp_docs/COVERAGE_INVESTIGATION_RESULTS.md         |  113 +
 tmp_docs/GRPC_INTEGRATION.md                       |   83 +
 tmp_docs/HIERARQUIA_ACTUAL.md                      |  225 ++
 tmp_docs/IMPLEMENTATION_LIST_PROJECTS.md           | 1075 +++++++
 tmp_docs/REFACTOR_PLAN_STORY_TASK.md               |  212 ++
 tmp_docs/TESTS_LIST_PROJECTS_IMPLEMENTATION.md     |  233 ++
 tmp_docs/TODO.md                                   |  457 +++
 tmp_docs/TODO_REFACTOR_STORY_TASK_HIERARCHY.md     |  159 +
 tmp_docs/VALIDACION_STORIES.md                     |  272 ++
 tmp_docs/planning-ui-grpc-investigation.md         |   86 +
 tmp_docs/test-result-log.txt                       | 1068 +++++++
 92 files changed, 15233 insertions(+), 451 deletions(-)
```
