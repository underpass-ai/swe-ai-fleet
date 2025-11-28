# Implementación Detallada: `list_projects` con Persistencia Dual

## 📋 Índice

1. [Contexto y Problema Original](#contexto-y-problema-original)
2. [Arquitectura General: Persistencia Dual](#arquitectura-general-persistencia-dual)
3. [Componentes Implementados](#componentes-implementados)
4. [Flujos de Datos Detallados](#flujos-de-datos-detallados)
5. [Decisiones de Diseño](#decisiones-de-diseño)
6. [Análisis de Complejidad](#análisis-de-complejidad)

---

## Contexto y Problema Original

### Estado Anterior

El método `list_projects()` en `StorageAdapter` era un **stub** que simplemente retornaba una lista vacía:

```python
async def list_projects(self, limit: int = 100, offset: int = 0) -> list[Project]:
    logger.warning("list_projects not fully implemented - returning empty list")
    return []
```

### Requerimientos del TODO

- ✅ **Persistencia de Projects en Neo4j** (nodos y relaciones)
- ✅ **Persistencia de Projects en Valkey** (detalles completos)
- ✅ **Query real** que retorna proyectos almacenados
- ✅ **Soporte para filtros por status**
- ✅ **Paginación funcional** (limit, offset)

---

## Arquitectura General: Persistencia Dual

### Filosofía del Diseño

El Planning Service usa un patrón de **persistencia dual** donde cada storage tiene responsabilidades específicas:

```
┌─────────────────────────────────────────────────────────────┐
│                  StorageAdapter (Orquestador)                │
│  Coordina la persistencia en ambos stores                    │
└───────────────┬───────────────────────────────┬─────────────┘
                │                               │
                ▼                               ▼
    ┌─────────────────────┐       ┌─────────────────────┐
    │   Neo4j (Graph)     │       │   Valkey (Cache)    │
    ├─────────────────────┤       ├─────────────────────┤
    │ • Estructura        │       │ • Detalles          │
    │ • Relaciones        │       │ • Índices           │
    │ • Queries complejas │       │ • Lecturas rápidas  │
    │ • Observabilidad    │       │ • Persistencia AOF  │
    └─────────────────────┘       └─────────────────────┘
```

### Responsabilidades por Store

#### Neo4j (Graph Structure)

**Propósito**: Mantener la estructura del grafo para:
- Navegación entre entidades (Project → Epic → Story → Task)
- Queries complejas basadas en relaciones
- Observabilidad y análisis de dependencias
- Rehydration de entidades desde el grafo

**Datos almacenados** (mínimos):
```cypher
(:Project {
  id: "PROJ-xxx",
  project_id: "PROJ-xxx",
  name: "Project Name",
  status: "active",
  created_at: "2025-01-28T10:00:00Z",
  updated_at: "2025-01-28T10:00:00Z"
})
```

**Características**:
- Properties mínimas (solo estructura)
- Constraint: `id IS UNIQUE`
- MERGE para crear/actualizar idempotentemente

#### Valkey (Details + Indexes)

**Propósito**: Almacenar detalles completos y proveer índices eficientes para:
- Lecturas ultra-rápidas (O(1) para hash lookups)
- Filtrado eficiente usando Sets
- Persistencia permanente (AOF + RDB)

**Estructuras de datos**:

1. **Hash** (detalles completos):
   ```
   Key: planning:project:{project_id}
   Value: {
     "project_id": "PROJ-xxx",
     "name": "Project Name",
     "description": "...",
     "status": "active",
     "owner": "user@example.com",
     "created_at": "2025-01-28T10:00:00Z",
     "updated_at": "2025-01-28T10:00:00Z"
   }
   ```

2. **Set** (índice global):
   ```
   Key: planning:projects:all
   Value: Set["PROJ-001", "PROJ-002", "PROJ-003", ...]
   ```

3. **Sets** (índices por status):
   ```
   Key: planning:projects:status:active
   Value: Set["PROJ-001", "PROJ-003", ...]

   Key: planning:projects:status:completed
   Value: Set["PROJ-002", ...]
   ```

---

## Componentes Implementados

### 1. ProjectNeo4jMapper

**Ubicación**: `services/planning/infrastructure/mappers/project_neo4j_mapper.py`

**Responsabilidad**: Convertir entre entidades de dominio (`Project`) y formato Neo4j.

#### Método: `to_graph_properties()`

```python
@staticmethod
def to_graph_properties(project: Project) -> dict[str, Any]:
    return {
        "id": project.project_id.value,           # Para constraint UNIQUE
        "project_id": project.project_id.value,   # Para claridad/consulta
        "name": project.name,
        "status": project.status.value,           # Enum → string
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }
```

**Decisiones de diseño**:
- **Doble campo `id` y `project_id`**: `id` se usa para el constraint UNIQUE en Neo4j, `project_id` para claridad en queries
- **Solo propiedades mínimas**: No almacena `description` ni `owner` en Neo4j (están en Valkey)
- **ISO format timestamps**: Estándar para almacenamiento en Neo4j
- **Enum → string**: Los enums se convierten a su valor string

#### Método: `from_node_data()`

**Proceso de conversión**:
1. Extrae propiedades del nodo (maneja formato Neo4j raw o dict simple)
2. Valida campos requeridos (fail-fast)
3. Parsea timestamps ISO a `datetime`
4. Maneja campos opcionales con defaults
5. Crea entidad de dominio inmutable

**Manejo de errores**:
- `ValueError` si falta `project_id` o `name`
- `ValueError` si faltan timestamps
- Fallback a `ProjectStatus.ACTIVE` si no hay status

---

### 2. Neo4j Queries y Constraints

**Ubicación**: `services/planning/infrastructure/adapters/neo4j_queries.py`

#### Constraint: `PROJECT_ID_UNIQUE`

```cypher
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE
```

**Propósito**: Garantizar que no haya duplicados a nivel de base de datos.

**Ejecución**: Se crea en `Neo4jAdapter.__init__()` vía `_init_constraints()`.

#### Query: `CREATE_PROJECT_NODE`

```cypher
MERGE (p:Project {id: $project_id})
SET p.project_id = $project_id,
    p.name = $name,
    p.status = $status,
    p.created_at = $created_at,
    p.updated_at = $updated_at
RETURN p
```

**Análisis**:
- **MERGE**: Crea si no existe, actualiza si existe (idempotente)
- **SET**: Actualiza propiedades en cada ejecución
- **Parámetros**: Previene inyección SQL (Cypher injection)

**Comportamiento**:
- Primera vez: Crea nodo nuevo
- Actualización: Actualiza propiedades del nodo existente

#### Query: `UPDATE_PROJECT_STATUS`

```cypher
MATCH (p:Project {id: $project_id})
SET p.status = $status,
    p.updated_at = $updated_at
RETURN p
```

**Uso**: Optimización para actualizaciones de status (no necesita todos los campos).

**Validación**: Si no encuentra el nodo, lanza `ValueError`.

#### Query: `GET_PROJECT_IDS_BY_STATUS`

```cypher
MATCH (p:Project {status: $status})
RETURN p.id AS project_id
ORDER BY p.created_at DESC
```

**Propósito**: Obtener IDs de proyectos por status desde Neo4j (backup si Valkey falla).

**Nota**: Actualmente no se usa en `list_projects()` (usa Valkey por velocidad), pero está disponible para queries de grafo.

---

### 3. Neo4jAdapter - Métodos para Projects

**Ubicación**: `services/planning/infrastructure/adapters/neo4j_adapter.py`

#### Método: `create_project_node()`

**Signatura**:
```python
async def create_project_node(
    self,
    project_id: str,
    name: str,
    status: str,
    created_at: str,
    updated_at: str,
) -> None
```

**Flujo de ejecución**:

```
create_project_node() [async]
    │
    ▼
asyncio.to_thread() [ejecuta en thread pool]
    │
    ▼
_create_project_node_sync() [síncrono]
    │
    ▼
_session() [crea sesión Neo4j]
    │
    ▼
_retry_operation() [con retry logic]
    │
    ▼
session.execute_write() [transacción de escritura]
    │
    ▼
_tx() [función de transacción]
    │
    ▼
tx.run(CREATE_PROJECT_NODE, params) [ejecuta query]
```

**Características**:
- **Async wrapper**: Permite ejecutar en thread pool sin bloquear event loop
- **Retry logic**: Maneja errores transitorios (ServiceUnavailable, TransientError)
- **Transacción**: Garantiza atomicidad

**Parámetros**:
- Todos son `str` porque Neo4j espera strings (timestamps en ISO format)
- El mapper convierte `datetime` → ISO string antes de llamar

#### Método: `update_project_status()`

Similar a `create_project_node()` pero:
- Usa `UPDATE_PROJECT_STATUS` query
- Valida que el nodo exista (lanza `ValueError` si no)
- Solo actualiza `status` y `updated_at`

#### Método: `get_project_ids_by_status()`

Query de lectura (read transaction):
- Usa `session.execute_read()`
- Retorna lista de IDs
- Ordenados por `created_at DESC`

---

### 4. ValkeyKeys - Schema de Keys

**Ubicación**: `services/planning/infrastructure/adapters/valkey_keys.py`

#### Método: `projects_by_status()`

```python
@staticmethod
def projects_by_status(status: str) -> str:
    return f"{ValkeyKeys.NAMESPACE}:projects:status:{status}"
```

**Ejemplos de keys generadas**:
```
planning:projects:status:active
planning:projects:status:completed
planning:projects:status:archived
```

**Ventajas de centralizar keys**:
- Previene typos
- Consistencia en naming
- Fácil de refactorizar
- Documenta el schema

---

### 5. ValkeyStorageAdapter - Persistencia en Valkey

**Ubicación**: `services/planning/infrastructure/adapters/valkey_adapter.py`

#### Método: `save_project()` - Versión Mejorada

**Algoritmo completo**:

```python
async def save_project(self, project: Project) -> None:
    # PASO 1: Obtener status anterior (si existe)
    hash_key = self._project_hash_key(project.project_id)
    old_status_str = self.client.hget(hash_key, "status")

    # PASO 2: Guardar hash completo (sobrescribe)
    project_data = ProjectValkeyMapper.to_dict(project)
    self.client.hset(hash_key, mapping=project_data)

    # PASO 3: Agregar a índice global (idempotente)
    self.client.sadd(self._all_projects_set_key(), project.project_id.value)

    # PASO 4: Manejar cambio de status
    if old_status_str and old_status_str != project.status.value:
        # Remover de set anterior
        old_status_key = self._projects_by_status_key(old_status_str)
        self.client.srem(old_status_key, project.project_id.value)

    # PASO 5: Agregar a set de status actual
    status_key = self._projects_by_status_key(project.status.value)
    self.client.sadd(status_key, project.project_id.value)
```

**Análisis línea por línea**:

1. **`hget(hash_key, "status")`**:
   - Intenta obtener status anterior
   - Retorna `None` si el proyecto no existe (primera vez)

2. **`hset(hash_key, mapping=project_data)`**:
   - Guarda/actualiza hash completo
   - `mapping=` permite set múltiples campos atómicamente

3. **`sadd(all_projects_set, project_id)`**:
   - Agrega a índice global
   - `SADD` es idempotente (no duplica si ya existe)

4. **Detección de cambio de status**:
   - Solo se ejecuta si hay status anterior Y es diferente
   - Evita operaciones innecesarias en primera creación

5. **Actualización de sets de status**:
   - `SREM`: Remueve de set anterior (si cambió)
   - `SADD`: Agrega a set nuevo (siempre, para mantener consistencia)

**Casos de uso**:

**Caso 1: Creación nueva**
```
old_status_str = None
→ No ejecuta cambio de status
→ Agrega a all_projects y status:active
```

**Caso 2: Actualización sin cambio de status**
```
old_status_str = "active"
project.status = "active"
→ No ejecuta cambio de status
→ Mantiene en sets existentes
```

**Caso 3: Cambio de status**
```
old_status_str = "active"
project.status = "completed"
→ SREM de status:active
→ SADD a status:completed
```

#### Método: `list_projects()` - Con Filtrado

**Implementación sincrónica** (ejecutada en thread pool):

```python
def _list_projects_sync(
    self,
    status_filter: ProjectStatus | None,
    limit: int,
    offset: int,
) -> list[Project]:
    # PASO 1: Seleccionar set fuente
    if status_filter:
        set_key = self._projects_by_status_key(status_filter.value)
    else:
        set_key = self._all_projects_set_key()

    # PASO 2: Obtener todos los IDs del set
    project_ids_set = self.client.smembers(set_key)
    project_ids = list(project_ids_set)

    # PASO 3: Ordenar (aproximación de orden de creación)
    project_ids.sort()

    # PASO 4: Aplicar paginación
    paginated_ids = project_ids[offset : offset + limit]

    # PASO 5: Recuperar proyectos completos
    projects = []
    for project_id_str in paginated_ids:
        project = self._get_project_sync(ProjectId(project_id_str))
        if project:  # Defensivo: por si fue eliminado
            projects.append(project)

    return projects
```

**Análisis de complejidad**:

- **Paso 1**: O(1) - Selección de key
- **Paso 2**: O(N) donde N = tamaño del set (SMEMBERS)
- **Paso 3**: O(N log N) - Sort
- **Paso 4**: O(limit) - Slice
- **Paso 5**: O(limit × M) donde M = costo de HGETALL

**Total**: O(N log N + limit × M)

**Optimizaciones implementadas**:
- Filtrado en Set (O(1) lookup por status)
- Paginación antes de recuperar detalles (evita cargar todos)
- Ordenamiento en memoria (aceptable para ~1000 proyectos)

**Limitaciones**:
- Sort por ID no garantiza orden cronológico exacto (aproximación)
- Para muchos proyectos (>10k), considerar ordenar en Redis (ZSET)

---

### 6. StorageAdapter - Orquestador

**Ubicación**: `services/planning/infrastructure/adapters/storage_adapter.py`

#### Método: `save_project()` - Persistencia Dual

```python
async def save_project(self, project: Project) -> None:
    # 1. Save details to Valkey (permanent storage)
    await self.valkey.save_project(project)

    # 2. Create graph node in Neo4j (structure only)
    props = ProjectNeo4jMapper.to_graph_properties(project)
    await self.neo4j.create_project_node(
        project_id=props["id"],
        name=props["name"],
        status=props["status"],
        created_at=props["created_at"],
        updated_at=props["updated_at"],
    )

    logger.info(f"Project saved (dual): {project.project_id}")
```

**Orden de operaciones**:
1. Primero Valkey (más rápido, tiene todos los detalles)
2. Luego Neo4j (más lento, solo estructura)

**¿Por qué este orden?**
- Si Valkey falla, no tiene sentido escribir en Neo4j
- Valkey es la fuente de verdad para detalles
- Neo4j es complemento para relaciones

**Manejo de errores**:
- Si Valkey falla: No se escribe en Neo4j
- Si Neo4j falla: Valkey ya tiene los datos (consistencia eventual)
- Logs indican éxito/fallo de cada operación

#### Método: `list_projects()` - Delegación

```python
async def list_projects(
    self,
    status_filter: ProjectStatus | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Project]:
    return await self.valkey.list_projects(
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
```

**Decisión**: Solo usa Valkey (no Neo4j) porque:
- Valkey tiene índices eficientes (Sets)
- Valkey tiene todos los detalles (no necesita Neo4j)
- Más rápido que query Neo4j + reconstrucción

**Cuándo usar Neo4j**:
- Queries de relaciones (Project → Epic → Story)
- Análisis de dependencias
- Traversals complejos

---

### 7. StoragePort - Protocolo Actualizado

**Ubicación**: `services/planning/application/ports/storage_port.py`

#### Cambio en Signatura

**Antes**:
```python
async def list_projects(self, limit: int = 100, offset: int = 0) -> list[Project]:
```

**Después**:
```python
async def list_projects(
    self,
    status_filter: ProjectStatus | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Project]:
```

**Impacto**: Todos los implementadores deben aceptar `status_filter` (aunque sea opcional).

---

### 8. ListProjectsUseCase - Use Case Actualizado

**Ubicación**: `services/planning/application/usecases/list_projects_usecase.py`

**Responsabilidades**:
1. Validar parámetros
2. Logging estructurado
3. Delegar a storage
4. Validación defensiva (projects nunca es None)
5. Logging de resultados

**Código clave**:
```python
async def execute(
    self,
    status_filter: ProjectStatus | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Project]:
    logger.info(
        f"Listing projects: status_filter={status_filter}, limit={limit}, offset={offset}",
        extra={
            "status_filter": status_filter.value if status_filter else None,
            "limit": limit,
            "offset": offset,
            "use_case": "ListProjects",
        },
    )

    projects = await self._storage.list_projects(
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )

    # Fail-fast: Ensure projects is never None
    if projects is None:
        logger.warning("Storage returned None for list_projects, returning empty list")
        projects = []

    logger.info(f"✓ Found {len(projects)} projects")
    return projects
```

**Validación defensiva**: Aunque el storage nunca debería retornar `None`, el use case maneja este caso.

---

### 9. list_projects_handler - gRPC Handler

**Ubicación**: `services/planning/infrastructure/grpc/handlers/list_projects_handler.py`

**Flujo completo**:

```python
async def list_projects_handler(
    request: planning_pb2.ListProjectsRequest,
    context,
    use_case: ListProjectsUseCase,
) -> planning_pb2.ListProjectsResponse:
    # PASO 1: Validar y parsear limit/offset
    limit = request.limit if request.limit > 0 else 100
    offset = request.offset if request.offset >= 0 else 0

    # PASO 2: Parsear status_filter (si existe)
    status_filter: ProjectStatus | None = None
    if request.status_filter:
        try:
            status_filter = ProjectStatus(request.status_filter)
        except ValueError:
            # Invalid status → retornar error gRPC
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return ResponseMapper.list_projects_response(
                success=False,
                message=f"Invalid status_filter: {request.status_filter}",
                projects=[],
            )

    # PASO 3: Ejecutar use case
    projects = await use_case.execute(
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )

    # PASO 4: Mapear respuesta
    return ResponseMapper.list_projects_response(
        success=True,
        message=f"Found {len(projects)} projects",
        projects=projects,
    )
```

**Validaciones**:
1. **Limit**: Si ≤ 0, usa default 100
2. **Offset**: Si < 0, usa default 0
3. **Status filter**: Si existe, valida que sea enum válido

**Manejo de errores**:
- `ValueError` en status → `INVALID_ARGUMENT` gRPC status
- Excepciones generales → `INTERNAL` gRPC status

---

## Flujos de Datos Detallados

### Flujo 1: Crear Proyecto (Primera Vez)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CreateProjectUseCase.execute()                          │
│    - Crea entidad Project (inmutable)                      │
│    - Genera ProjectId                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. StorageAdapter.save_project(project)                    │
└───────────────┬───────────────────────────────┬─────────────┘
                │                               │
                ▼                               ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐
│ 3a. ValkeyStorageAdapter    │  │ 3b. Neo4jAdapter            │
│     .save_project()         │  │     .create_project_node()  │
│                             │  │                             │
│ - HGET status anterior      │  │ - MERGE (:Project)          │
│   → None (no existe)        │  │ - SET propiedades           │
│                             │  │                             │
│ - HSET hash completo        │  │                             │
│   planning:project:PROJ-xxx │  │                             │
│                             │  │                             │
│ - SADD all_projects         │  │                             │
│   → PROJ-xxx                │  │                             │
│                             │  │                             │
│ - SADD status:active        │  │                             │
│   → PROJ-xxx                │  │                             │
└─────────────────────────────┘  └─────────────────────────────┘
```

**Resultado**:
- ✅ Hash en Valkey con todos los campos
- ✅ Set `planning:projects:all` contiene `PROJ-xxx`
- ✅ Set `planning:projects:status:active` contiene `PROJ-xxx`
- ✅ Nodo `(:Project)` en Neo4j con propiedades mínimas

---

### Flujo 2: Listar Todos los Proyectos (Sin Filtro)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Cliente gRPC → ListProjectsRequest                       │
│    { limit: 10, offset: 0 }                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. list_projects_handler()                                  │
│    - Parsea request                                          │
│    - status_filter = None                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. ListProjectsUseCase.execute()                            │
│    - status_filter=None, limit=10, offset=0                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. StorageAdapter.list_projects()                            │
│    - Delega a ValkeyStorageAdapter                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. ValkeyStorageAdapter._list_projects_sync()               │
│                                                              │
│    a) SMEMBERS planning:projects:all                        │
│       → Set["PROJ-001", "PROJ-002", "PROJ-003", ...]        │
│                                                              │
│    b) Convert to list → ["PROJ-001", "PROJ-002", ...]       │
│                                                              │
│    c) Sort() → ["PROJ-001", "PROJ-002", "PROJ-003"]         │
│                                                              │
│    d) Slice [0:10] → ["PROJ-001", "PROJ-002", ...]          │
│                                                              │
│    e) Para cada ID:                                          │
│       - HGETALL planning:project:PROJ-001                   │
│       - ProjectValkeyMapper.from_dict()                     │
│       - Append to projects[]                                │
│                                                              │
│    f) Return projects[]                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Response → Cliente gRPC                                   │
│    { projects: [Project, ...], total_count: 10 }            │
└─────────────────────────────────────────────────────────────┘
```

**Ejemplo con datos reales**:

Supongamos que hay 5 proyectos en el sistema:

```
Valkey Sets:
  planning:projects:all = Set["PROJ-001", "PROJ-002", "PROJ-003", "PROJ-004", "PROJ-005"]
```

**Request**: `limit=2, offset=1`

1. `SMEMBERS all` → `["PROJ-001", "PROJ-002", "PROJ-003", "PROJ-004", "PROJ-005"]`
2. Sort → `["PROJ-001", "PROJ-002", "PROJ-003", "PROJ-004", "PROJ-005"]`
3. Slice [1:3] → `["PROJ-002", "PROJ-003"]`
4. `HGETALL planning:project:PROJ-002` → Project entity
5. `HGETALL planning:project:PROJ-003` → Project entity
6. Return `[Project(PROJ-002), Project(PROJ-003)]`

---

### Flujo 3: Listar Proyectos con Filtro de Status

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Cliente gRPC → ListProjectsRequest                       │
│    { status_filter: "completed", limit: 10, offset: 0 }     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. list_projects_handler()                                  │
│    - Parsea request                                          │
│    - Valida status_filter = "completed"                      │
│    - ProjectStatus("completed") → enum                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. ListProjectsUseCase.execute()                            │
│    - status_filter=ProjectStatus.COMPLETED                  │
│    - limit=10, offset=0                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. ValkeyStorageAdapter._list_projects_sync()               │
│                                                              │
│    a) status_filter existe → usar set filtrado              │
│                                                              │
│    b) SMEMBERS planning:projects:status:completed           │
│       → Set["PROJ-002", "PROJ-004"]                         │
│                                                              │
│    c) Convert to list → ["PROJ-002", "PROJ-004"]            │
│                                                              │
│    d) Sort() → ["PROJ-002", "PROJ-004"]                     │
│                                                              │
│    e) Slice [0:10] → ["PROJ-002", "PROJ-004"]               │
│                                                              │
│    f) Para cada ID:                                          │
│       - HGETALL planning:project:PROJ-002                   │
│       - HGETALL planning:project:PROJ-004                   │
│                                                              │
│    g) Return [Project(PROJ-002), Project(PROJ-004)]         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Response → Cliente gRPC                                   │
│    { projects: [Project(PROJ-002), Project(PROJ-004)] }     │
└─────────────────────────────────────────────────────────────┘
```

**Ventaja del filtrado en Set**:
- Sin filtro: Obtiene todos los IDs, luego filtra en memoria
- Con filtro: Obtiene solo IDs relevantes directamente del Set
- **Reducción de complejidad**: O(N total) → O(N filtered)

---

### Flujo 4: Actualizar Status de Proyecto

```
┌─────────────────────────────────────────────────────────────┐
│ 1. UpdateProjectStatusUseCase (futuro)                      │
│    - Obtiene proyecto actual                                │
│    - Crea nuevo Project con status diferente                │
│    - Llama save_project()                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. StorageAdapter.save_project(project)                     │
│    - project.status = "completed" (cambió de "active")      │
└───────────────┬───────────────────────────────┬─────────────┘
                │                               │
                ▼                               ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐
│ 3a. ValkeyStorageAdapter    │  │ 3b. Neo4jAdapter            │
│     .save_project()         │  │     .create_project_node()  │
│                             │  │                             │
│ - HGET status anterior      │  │ - MERGE (:Project)          │
│   → "active"                │  │ - SET status="completed"    │
│                             │  │   updated_at=...            │
│ - HSET hash completo        │  │                             │
│   (status="completed")      │  │                             │
│                             │  │                             │
│ - SADD all_projects         │  │                             │
│   (idempotente)             │  │                             │
│                             │  │                             │
│ - Detección cambio:         │  │                             │
│   "active" != "completed"   │  │                             │
│   → SREM status:active      │  │                             │
│     PROJ-001                │  │                             │
│                             │  │                             │
│ - SADD status:completed     │  │                             │
│   PROJ-001                  │  │                             │
└─────────────────────────────┘  └─────────────────────────────┘
```

**Estado final**:
- ✅ Hash actualizado en Valkey
- ✅ `planning:projects:status:active` ya no contiene `PROJ-001`
- ✅ `planning:projects:status:completed` ahora contiene `PROJ-001`
- ✅ Nodo Neo4j actualizado con nuevo status

---

## Decisiones de Diseño

### 1. ¿Por qué persistencia dual?

**Ventajas**:
- **Neo4j**: Ideal para relaciones y queries complejas
- **Valkey**: Ultra-rápido para lecturas simples y filtrados

**Trade-off**:
- Más complejidad de mantenimiento
- Posible inconsistencia si una operación falla
- Doble almacenamiento (redundancia)

**Justificación**:
- Stories ya usan este patrón (consistencia)
- Performance crítica para listados (UI necesita respuesta rápida)
- Valkey tiene persistencia AOF (no es volátil)

### 2. ¿Por qué Sets en Valkey para filtros?

**Alternativas consideradas**:
1. **Sets indexados por status** (implementado): O(1) lookup, O(N) para obtener todos
2. **Sorted Sets (ZSET)**: O(log N) lookup, ordenamiento nativo
3. **Filtrado en memoria**: O(N) scan de todos los proyectos

**Decisión**: Sets indexados porque:
- Filtrado por status es el caso más común
- O(1) membership test
- Suficientemente rápido para ~1000 proyectos

**Futuro**: Si hay >10k proyectos, considerar ZSET para ordenamiento.

### 3. ¿Por qué solo propiedades mínimas en Neo4j?

**Razones**:
- Neo4j es para estructura/relaciones, no detalles
- Valkey ya tiene todos los campos
- Reduce tamaño del nodo
- Más rápido para queries de grafo

**Cuándo usar Neo4j para detalles**:
- Si necesitas queries complejas sobre campos específicos
- Si necesitas full-text search (Neo4j + Elasticsearch)

### 4. ¿Por qué MERGE en lugar de CREATE?

**MERGE** (idempotente):
```cypher
MERGE (p:Project {id: $project_id})
SET p.status = $status
```
- Crea si no existe
- Actualiza si existe
- Útil para retries

**CREATE** (no idempotente):
```cypher
CREATE (p:Project {id: $project_id})
```
- Falla si ya existe
- Necesita verificar antes

**Decisión**: MERGE para idempotencia y simplicidad.

### 5. ¿Por qué ordenamiento por ID y no por timestamp?

**Implementación actual**:
```python
project_ids.sort()  # Ordena strings alfabéticamente
```

**Limitación**:
- `PROJ-001`, `PROJ-002`, ... funciona bien
- No garantiza orden cronológico exacto

**Alternativa** (futuro):
```python
# Usar ZSET con timestamp como score
ZADD planning:projects:by_created {timestamp} {project_id}
ZREVRANGE planning:projects:by_created {offset} {offset+limit}
```

**Decisión actual**: Sort por ID es suficiente para MVP, se puede mejorar después.

---

## Análisis de Complejidad

### Operaciones de Escritura

#### `save_project()` - Primera vez

| Operación | Complejidad | Descripción |
|-----------|-------------|-------------|
| `HGET status` | O(1) | Hash lookup |
| `HSET hash` | O(K) | K = número de campos (~7) |
| `SADD all_projects` | O(1) | Set add (amortizado) |
| `SADD status:active` | O(1) | Set add (amortizado) |
| Neo4j MERGE | O(1) | Constraint lookup |

**Total Valkey**: O(K) ≈ O(1)
**Total Neo4j**: O(1)
**Total**: O(1) constante

#### `save_project()` - Actualización con cambio de status

| Operación | Complejidad |
|-----------|-------------|
| `HGET status` | O(1) |
| `HSET hash` | O(K) |
| `SADD all_projects` | O(1) |
| `SREM status:old` | O(1) |
| `SADD status:new` | O(1) |
| Neo4j MERGE | O(1) |

**Total**: O(K) ≈ O(1) constante

### Operaciones de Lectura

#### `list_projects()` - Sin filtro

| Operación | Complejidad | Descripción |
|-----------|-------------|-------------|
| `SMEMBERS all` | O(N) | N = total proyectos |
| `sort()` | O(N log N) | Python sort |
| Slice | O(limit) | List slicing |
| `HGETALL` × limit | O(limit × M) | M = campos por hash (~7) |

**Total**: O(N log N + limit × M)

**Para N=1000, limit=10**:
- O(1000 log 1000 + 10 × 7) ≈ O(10,000 + 70) ≈ O(10,000)

#### `list_projects()` - Con filtro de status

| Operación | Complejidad | Descripción |
|-----------|-------------|-------------|
| `SMEMBERS status:X` | O(F) | F = proyectos filtrados |
| `sort()` | O(F log F) | Python sort |
| Slice | O(limit) | List slicing |
| `HGETALL` × limit | O(limit × M) | M = campos por hash |

**Total**: O(F log F + limit × M)

**Para F=50, limit=10**:
- O(50 log 50 + 10 × 7) ≈ O(300 + 70) ≈ O(370)

**Mejora**: 27x más rápido que sin filtro (en este ejemplo).

---

## Resumen Ejecutivo

### Lo que se implementó

1. ✅ **Persistencia dual completa**: Projects en Neo4j y Valkey
2. ✅ **Filtrado eficiente**: Sets indexados por status en Valkey
3. ✅ **Paginación funcional**: Limit y offset implementados
4. ✅ **Manejo de actualizaciones**: Cambios de status sincronizados en sets
5. ✅ **Queries reales**: Retorna proyectos almacenados (no stubs)

### Métricas de Performance

- **Escritura**: O(1) constante
- **Lectura sin filtro**: O(N log N) para N proyectos
- **Lectura con filtro**: O(F log F) para F proyectos filtrados
- **Mejora con filtro**: ~10-30x más rápido dependiendo de selectividad

### Cumplimiento de Requisitos

| Requisito | Estado | Implementación |
|-----------|--------|----------------|
| Persistencia Neo4j | ✅ | Nodos Project con propiedades mínimas |
| Persistencia Valkey | ✅ | Hash completo + sets indexados |
| Query real | ✅ | Lista proyectos desde Valkey |
| Filtro por status | ✅ | Sets indexados `planning:projects:status:{status}` |
| Paginación | ✅ | Limit y offset funcionales |

---

## Próximos Pasos (Opcionales)

1. **Tests unitarios**: Cubrir todos los métodos nuevos
2. **Tests de integración**: Verificar persistencia dual
3. **Optimización de ordenamiento**: ZSET para orden cronológico
4. **Caché de consultas**: Redis para listados frecuentes
5. **Métricas**: Agregar timing logs para monitoreo


