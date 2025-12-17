# E2E Test Data Creation

This job creates valuable test data for E2E tests in the system.

## Created Data

The job creates the following test data:

### Project
- **Name**: "Test de swe fleet"
- **Description**: "Proyecto de prueba para tests E2E del sistema SWE Fleet"

### Epic
- **Title**: "Autenticacion"
- **Description**: "Épica de autenticación y autorización para el sistema"

### Stories
1. **RBAC** - Implementar sistema de control de acceso basado en roles (Role-Based Access Control)
2. **AUTH0** - Integración con Auth0 para autenticación y gestión de usuarios
3. **Autenticacion en cliente con conexion a google verificacion mail** - Implementar autenticación en el cliente con conexión a Google y verificación de email
4. **Rol Admin y Rol User** - Definir e implementar roles de administrador y usuario en el sistema

## Usage

### Build and Push Image

```bash
cd e2e/tests/02-create-test-data
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
| `TEST_CREATED_BY` | User creating the entities | `e2e-test@system.local` |

## Output

The job will output the IDs of all created entities:

```
📊 Created Test Data Summary
================================================================================

Created entities (preserved for E2E tests):
  Project: PROJ-xxx - 'Test de swe fleet'
  Epic: E-xxx - 'Autenticacion'
  Stories (4):
    - s-xxx
    - s-xxx
    - s-xxx
    - s-xxx

✓ Test data created successfully and preserved
```

## Notes

- **Data is preserved**: The created entities remain in Neo4j and Valkey for use in other E2E tests
- **Idempotent**: Running the job multiple times will create duplicate entities (each with unique IDs)
- **No cleanup**: This job does not delete any data - entities persist for other tests

## Integration with Other E2E Tests

Other E2E tests can use the created entities by:
1. Querying Neo4j to find the project/epic/story IDs
2. Using the project name "Test de swe fleet" to identify the test data
3. Using the epic title "Autenticacion" to find related stories

Example Neo4j query:
```cypher
MATCH (p:Project {name: "Test de swe fleet"})
MATCH (e:Epic {title: "Autenticacion"})-[:BELONGS_TO]->(p)
MATCH (s:Story)-[:BELONGS_TO]->(e)
RETURN p.id as project_id, e.id as epic_id, collect(s.id) as story_ids
```
