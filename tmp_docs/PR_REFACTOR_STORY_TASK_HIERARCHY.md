# PR: Refactor Story-Task Hierarchy + Fix UserName Serialization

## 📋 Resumen

Esta PR implementa la **Fase 1** de la refactorización de la jerarquía Story-Task y corrige un bug crítico de serialización de Value Objects.

### Cambios Principales

1. **Refactorización Domain Layer (Fase 1):**
   - ✅ `Task` entity: `story_id` ahora es REQUIRED, `plan_id` es OPTIONAL
   - ✅ `Plan` entity: `story_id` (singular) → `story_ids` (tuple) para soportar múltiples stories
   - ✅ `CreateTaskRequest`: `story_id` obligatorio, `plan_id` opcional

2. **Bug Fix: UserName Serialization:**
   - ✅ Corregido `StoryProtobufMapper` para extraer `.value` de Value Objects antes de serializar
   - ✅ Corregido `StorageAdapter` para extraer `.value` antes de pasar a Neo4j
   - ✅ Actualizado test correspondiente

## 🐛 Bug Fix: UserName Serialization

### Problema
Error al crear historias:
```
"Values of type <class 'planning.domain.value_objects.actors.user_name.UserName'> are not supported"
```

### Causa
Los adapters de protobuf y Neo4j esperan tipos primitivos (strings), pero se estaban pasando Value Objects directamente.

### Solución
- `StoryProtobufMapper.to_protobuf()`: Extrae `.value` de todos los Value Objects antes de crear el mensaje protobuf
- `StorageAdapter.save_story()`: Extrae `story.created_by.value` antes de pasar a Neo4j
- Tests actualizados para reflejar el cambio

### Archivos Modificados
- `services/planning/infrastructure/mappers/story_protobuf_mapper.py`
- `services/planning/infrastructure/adapters/storage_adapter.py`
- `services/planning/tests/unit/infrastructure/test_storage_adapter.py`

## 🔄 Refactorización: Story-Task Hierarchy

### Objetivo
Hacer que `Task` pertenezca directamente a `Story`, haciendo que `Plan` sea un agregado opcional. Esto permite:
- Crear tareas directamente desde stories sin necesidad de un plan
- Un plan puede cubrir múltiples stories
- Mayor flexibilidad en el flujo de trabajo

### Cambios en Domain Layer

#### Task Entity (`services/planning/domain/entities/task.py`)
```python
# ANTES
task_id: TaskId
plan_id: PlanId  # REQUIRED
story_id: StoryId  # Denormalized

# DESPUÉS
task_id: TaskId
story_id: StoryId  # REQUIRED - Parent Story (domain invariant)
plan_id: PlanId | None = None  # Optional link to a plan version
```

**Invariantes:**
- ✅ `story_id` es REQUIRED (invariante de dominio)
- ✅ `plan_id` es OPTIONAL
- ✅ Validaciones actualizadas en `__post_init__`

#### Plan Entity (`services/planning/domain/entities/plan.py`)
```python
# ANTES
story_id: StoryId  # Single story

# DESPUÉS
story_ids: tuple[StoryId, ...]  # Multiple stories
```

**Invariantes:**
- ✅ `story_ids` no puede estar vacío (mínimo 1 story)
- ✅ Validación agregada en `__post_init__`

#### CreateTaskRequest (`services/planning/domain/value_objects/requests/create_task_request.py`)
```python
story_id: StoryId  # REQUIRED
plan_id: PlanId | None = None  # OPTIONAL
```

### Archivos Modificados
- `services/planning/domain/entities/task.py`
- `services/planning/domain/entities/plan.py`
- `services/planning/domain/value_objects/requests/create_task_request.py`
- `services/planning/domain/events/task_created_event.py`

## 📊 Estado del TODO

### ✅ Completado
- [x] **Fase 0:** Análisis de Impacto y Flujo (Inter-Service)
- [x] **Fase 1.1:** Modificar Entity `Task`
- [x] **Fase 1.2:** Modificar Entity `Plan`
- [x] **Fase 1.3:** Actualizar Value Object `CreateTaskRequest`

### 🚧 Pendiente
- [ ] **Fase 2:** Application Layer (Use Cases)
- [ ] **Fase 3:** Infrastructure Layer (Storage & Adapters)
- [ ] **Fase 4:** API Layer (gRPC & Protobuf)
- [ ] **Fase 5:** Task Derivation Service (Consumer)
- [ ] **Fase 6:** Tests & Verificación

Ver `tmp_docs/TODO_REFACTOR_STORY_TASK_HIERARCHY.md` para detalles completos.

## 🧪 Testing

### Tests Unitarios
- ✅ `test_story_protobuf_mapper.py`: Verifica serialización correcta de Value Objects
- ✅ `test_storage_adapter.py`: Verifica extracción de `.value` antes de pasar a Neo4j
- ✅ Tests de dominio para Task y Plan con nuevas invariantes

### Verificación Manual
- ✅ Creación de historias funciona correctamente
- ✅ `created_by` se serializa como string en protobuf
- ✅ `created_by` se guarda como string en Neo4j

## 🚀 Deployment

### Servicios Afectados
- **Planning Service**: Desplegado y funcionando
  - Imagen: `registry.underpassai.com/swe-ai-fleet/planning:v2.0.0-20251129-*`
  - Estado: ✅ Running (2 replicas)

### Verificación Post-Deploy
```bash
# Test creación de historia
curl -X POST 'https://planning.underpassai.com/api/stories' \
  -H 'content-type: application/json' \
  --data-raw '{"epic_id":"E-...","title":"test","brief":"test","created_by":"Tirso"}'
```

## 📝 Notas de Implementación

### Compatibilidad
- Los cambios en `Task` y `Plan` son breaking changes en el dominio
- Los cambios en protobuf aún no están implementados (Fase 4 pendiente)
- Se recomienda limpiar la BD (`FLUSHDB` en Valkey) si hay inconsistencias

### Próximos Pasos
1. Completar Fase 2: Actualizar Use Cases para soportar `plan_id=None`
2. Completar Fase 3: Actualizar Storage adapters e índices
3. Completar Fase 4: Actualizar Protobuf y handlers gRPC
4. Completar Fase 5: Actualizar Task Derivation Service
5. Completar Fase 6: Tests de integración y E2E

## 🔗 Referencias

- TODO Principal: `tmp_docs/TODO_REFACTOR_STORY_TASK_HIERARCHY.md`
- RFC Base: `tmp_docs/REFACTOR_PLAN_STORY_TASK.md`
- Issue relacionado: Error de serialización UserName

## ✅ Checklist Pre-Merge

- [x] Tests unitarios pasan
- [x] Bug fix verificado en producción
- [x] TODO actualizado
- [x] Código sigue principios DDD y Hexagonal Architecture
- [x] No se usan reflection ni mutación dinámica
- [x] Value Objects se serializan correctamente (extraen `.value`)
- [ ] Tests de integración (pendiente Fase 6)
- [ ] Actualización de Protobuf (pendiente Fase 4)

