# E2E Test Data Cleanup

This job cleans up test data created by the `02-create-test-data` job.

## Cleaned Data

The job removes the following test data:

### Project
- **Name**: "Test de swe fleet"
- All related epics and stories

### Epic
- **Title**: "Autenticacion"
- All related stories

### Stories
1. **RBAC**
2. **AUTH0**
3. **Autenticacion en cliente con conexion a google verificacion mail**
4. **Rol Admin y Rol User**

## Usage

### Build and Push Image

```bash
cd e2e/tests/03-cleanup-test-data
make build-push
```

### Deploy Job

```bash
make deploy
```

### Check Status

```bash
make status
```

### View Logs

```bash
make logs
```

### Delete Job

```bash
make delete
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLANNING_SERVICE_URL` | Planning Service gRPC endpoint | `planning.swe-ai-fleet.svc.cluster.local:50054` |
| `NEO4J_URI` | Neo4j connection URI | `bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687` |
| `NEO4J_USERNAME` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password (from secret) | - |
| `VALKEY_HOST` | Valkey host | `valkey.swe-ai-fleet.svc.cluster.local` |
| `VALKEY_PORT` | Valkey port | `6379` |
| `CLEANUP_PROJECT_ID` | Specific project ID to delete | (empty - will search by name) |
| `CLEANUP_PROJECT_NAME` | Project name to search for | `Test de swe fleet` |

## Cleanup Process

The cleanup job performs the following steps:

1. **Find Project**: Searches for the project by name (or uses provided ID)
2. **Discover Entities**: Finds all related epics and stories in Neo4j
3. **Delete Stories**: Removes all stories from Neo4j and Valkey
4. **Delete Epics**: Removes all epics from Neo4j and Valkey
5. **Delete Project**: Removes the project from Neo4j and Valkey

## Output

The job will output the cleanup progress:

```
🧹 E2E Test Data Cleanup
================================================================================

Step 1: Cleanup Stories
  Deleting story: s-xxx...
  ✓ Deleted Story from Neo4j: s-xxx
  ✓ Deleted key from Valkey: story:s-xxx

Step 2: Cleanup Epics
  Deleting epic: E-xxx...
  ✓ Deleted Epic from Neo4j: E-xxx
  ✓ Deleted key from Valkey: epic:E-xxx

Step 3: Cleanup Project
  Deleting project: PROJ-xxx...
  ✓ Deleted Project from Neo4j: PROJ-xxx
  ✓ Deleted key from Valkey: project:PROJ-xxx

✅ Cleanup completed successfully
```

## Notes

- **Idempotent**: Running the job multiple times is safe - it will handle already-deleted entities gracefully
- **Complete cleanup**: Removes data from both Neo4j (graph) and Valkey (cache/storage)
- **Safe**: Only deletes entities related to the specified project

## Integration with Test Data Creation

This job is designed to clean up data created by `02-create-test-data`:

1. Run `02-create-test-data` to create test data
2. Run E2E tests that use the test data
3. Run `03-cleanup-test-data` to clean up after tests

Example workflow:
```bash
# Create test data
cd e2e/tests/02-create-test-data
make deploy

# Wait for completion, then run tests...

# Clean up test data
cd ../03-cleanup-test-data
make deploy
```
