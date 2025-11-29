# Plan de Refactorización: Story → Task (sin Plan en jerarquía)

**Fecha**: 2025-01-XX
**Objetivo**: Refactorizar la jerarquía para que Task pertenezca directamente a Story, y Plan sea un agregado separado

---

## 📋 Cambios Principales

### 1. Task Entity

**Archivo**: `services/planning/domain/entities/task.py`

**Cambios**:
```python
# ANTES
plan_id: PlanId  # REQUIRED - domain invariant
story_id: StoryId  # denormalized

# DESPUÉS
story_id: StoryId  # REQUIRED - domain invariant
plan_id: PlanId | None = None  # OPCIONAL - solo para ceremonia de planning
```

**Validación**:
- `story_id` es REQUIRED (domain invariant)
- `plan_id` es OPCIONAL (puede ser None)
- Task puede existir sin Plan

### 2. Plan Entity

**Archivo**: `services/planning/domain/entities/plan.py`

**Cambios**:
```python
# ANTES
story_id: StoryId  # REQUIRED - parent story (domain invariant)

# DESPUÉS
story_ids: tuple[StoryId, ...]  # REQUIRED - agrupación de Stories
```

**Validación**:
- `story_ids` no puede estar vacío (al menos una Story)
- Plan agrupa múltiples Stories
- Plan NO pertenece a una Story

### 3. CreateTaskRequest

**Archivo**: `services/planning/domain/value_objects/requests/create_task_request.py`

**Cambios**:
```python
# ANTES
plan_id: PlanId
story_id: StoryId

# DESPUÉS
story_id: StoryId  # REQUIRED
plan_id: PlanId | None = None  # OPCIONAL
```

### 4. CreateTaskUseCase

**Archivo**: `services/planning/application/usecases/create_task_usecase.py`

**Cambios**:
- Validar que `story_id` existe (domain invariant)
- `plan_id` es opcional (no validar si es None)
- Actualizar comentarios sobre domain invariants

### 5. TaskDerivationResultService

**Archivo**: `services/planning/application/services/task_derivation_result_service.py`

**Cambios**:
- `plan_id` pasa a ser opcional al crear Tasks
- Tasks pueden crearse sin Plan (solo con Story)
- Actualizar lógica de creación de Tasks

### 6. Storage Adapters

**Archivos**:
- `services/planning/infrastructure/adapters/valkey_adapter.py`
- `services/planning/infrastructure/adapters/storage_adapter.py`

**Cambios**:
- Actualizar índices de Valkey:
  - `tasks_by_story` (REQUIRED)
  - `tasks_by_plan` (OPCIONAL - solo si plan_id no es None)
- Actualizar métodos `save_task`, `list_tasks`:
  - Filtrar por `story_id` (REQUIRED)
  - Filtrar por `plan_id` (OPCIONAL)

### 7. Protobuf Definitions

**Archivo**: `specs/fleet/planning/v2/planning.proto`

**Cambios**:
```protobuf
// Task message
message Task {
  string task_id = 1;
  string story_id = 2;        // REQUIRED - parent story
  optional string plan_id = 3; // OPCIONAL - solo para ceremonia
  // ... resto de campos
}

// Plan message
message Plan {
  string plan_id = 1;
  repeated string story_ids = 2;  // Agrupación de Stories
  // ... resto de campos
}
```

### 8. gRPC Handlers

**Archivos**:
- `services/planning/infrastructure/grpc/handlers/create_task_handler.py`
- `services/planning/infrastructure/grpc/handlers/list_tasks_handler.py`

**Cambios**:
- `create_task_handler`: `plan_id` opcional
- `list_tasks_handler`: Filtrar por `story_id` (REQUIRED), `plan_id` (OPCIONAL)

### 9. Mappers

**Archivos**:
- `services/planning/infrastructure/mappers/task_valkey_mapper.py` (si existe)
- `services/planning/infrastructure/grpc/mappers/response_mapper.py`

**Cambios**:
- Actualizar serialización/deserialización para `plan_id` opcional
- Actualizar mappers de Plan para `story_ids`

### 10. Task Derivation Service

**Archivos**:
- `services/task_derivation/domain/value_objects/task_derivation/commands/task_creation_command.py`
- `services/task_derivation/infrastructure/mappers/planning_grpc_mapper.py`

**Cambios**:
- `TaskCreationCommand`: `plan_id` opcional
- Actualizar mappers para reflejar cambios

---

## 🔄 Orden de Refactorización

### Fase 1: Domain Layer
1. ✅ Actualizar `Task` entity (`story_id` REQUIRED, `plan_id` OPCIONAL)
2. ✅ Actualizar `Plan` entity (`story_ids` en lugar de `story_id`)
3. ✅ Actualizar `CreateTaskRequest` VO

### Fase 2: Application Layer
4. ✅ Actualizar `CreateTaskUseCase`
5. ✅ Actualizar `TaskDerivationResultService`
6. ✅ Actualizar `ListTasksUseCase` (filtros)

### Fase 3: Infrastructure Layer
7. ✅ Actualizar `StoragePort` (interfaces)
8. ✅ Actualizar `ValkeyStorageAdapter` (índices y métodos)
9. ✅ Actualizar `StorageAdapter` (delegación)
10. ✅ Actualizar mappers (Valkey, Protobuf)

### Fase 4: API Layer
11. ✅ Actualizar protobuf definitions
12. ✅ Regenerar protobuf code
13. ✅ Actualizar gRPC handlers
14. ✅ Actualizar response mappers

### Fase 5: Task Derivation Service
15. ✅ Actualizar `TaskCreationCommand`
16. ✅ Actualizar mappers de Task Derivation

### Fase 6: Tests
17. ✅ Actualizar tests unitarios
18. ✅ Actualizar tests de integración
19. ✅ Verificar cobertura

---

## ⚠️ Consideraciones

### Compatibilidad

**Problema**: Cambios en protobuf pueden romper compatibilidad.

**Solución**:
- Usar `optional` en protobuf para `plan_id`
- Mantener campos en orden (no cambiar números de campo)
- Actualizar versión de API si es necesario

### Índices de Valkey

**Cambios necesarios**:
- `tasks_by_story` (REQUIRED - siempre indexar)
- `tasks_by_plan` (OPCIONAL - solo indexar si plan_id no es None)

**Nota**: No hay migración de datos necesaria (proyecto no es versión 0).

---

## 📝 Notas

- Esta refactorización permite que Tasks existan sin Plan
- Plan sigue siendo útil para la ceremonia de planning
- Story puede ser replanificada individualmente sin Plan
- La jerarquía final es: `Project → Epic → Story → Task`
- Plan es un agregado separado que agrupa Stories

