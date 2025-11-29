# TODO: Refactorización Jerarquía Story → Task

Este documento rastrea el progreso específico de la refactorización para hacer que `Task` pertenezca directamente a `Story`, haciendo que `Plan` sea un agregado opcional.

**Basado en:** `tmp_docs/REFACTOR_PLAN_STORY_TASK.md`
**Estado:** 🚧 En Progreso

---

## 🔍 Fase 0: Análisis de Impacto y Flujo (Inter-Service)
*Objetivo: Identificar y mitigar acoplamientos fuertes en consumidores y eventos antes de cambiar el dominio.*

- [x] **0.1. Análisis de Eventos (AsyncAPI)**
  - [x] Verificar `TaskDerivationRequestPayload`: actualmente requiere `plan_id`. Necesita ser opcional.
    - **Resultado:** Schema `TaskDerivationRequestPayload` marca `plan_id` como requerido. Debe cambiar a opcional o permitir string vacío. `TaskDerivationCompletedPayload` y `TaskDerivationFailedPayload` también lo requieren.
  - [x] Verificar `PlanApproved` (AgileEvent): actualmente asume 1:1 Plan-Story. Necesita soportar N Stories.
    - **Resultado:** `AgileEventPayload` no define explícitamente `plan_id` o `story_id` en su schema base, pero el evento `HUMAN_APPROVAL` implícitamente transporta contexto. Se verificó en `PlanningEventsConsumer` que espera `plan_id` y `story_id` en el payload JSON.
  - [x] Definir estrategia de migración de contratos (¿v2 events?).
    - **Estrategia:** Relajar validación en consumers primero, luego actualizar producer. Mantener compatibilidad hacia atrás enviando `plan_id` si existe.

- [x] **0.2. Análisis de Task Derivation Service**
  - [x] `DeriveTasksUseCase` depende de `PlanContext`.
    - **Resultado:** El use case llama a `self.planning_port.get_plan(request.plan_id)`. Si `plan_id` es None, esto fallará. Se necesita un nuevo método en `PlanningPort` (ej: `get_derivation_context_from_story(story_id)`) o adaptar `get_plan` para aceptar `story_id`.
  - [x] Determinar si se puede construir un `StoryContext` suficiente para derivación sin Plan.
    - **Resultado:** `PlanContext` contiene `title`, `description`, `acceptance_criteria`, `technical_notes`. Una Story tiene `title`, `description`, `acceptance_criteria` (usualmente). Faltan `technical_notes` que suelen venir del Plan.
    - **Estrategia:** Si no hay Plan, usar la Story como fuente de verdad. `technical_notes` puede estar vacío.
  - [x] Actualizar lógica para soportar `plan_id=None`.
    - **Acción:** Refactorizar `DeriveTasksUseCase` para ramificar: si `plan_id` existe -> `get_plan`, sino -> `get_story`. Unificar en un DTO común `DerivationSourceContext`.

- [x] **0.3. Análisis de Context Service**
  - [x] `PlanningEventsConsumer._handle_plan_approved` asume `story_id` singular.
    - **Resultado:** El consumer extrae `story_id = event.get("story_id")`. Si el evento cambia a tener `story_ids` (lista), esto fallará o retornará None/List.
  - [x] Diseñar manejo de `PlanApproved` con múltiples stories.
    - **Estrategia:** Actualizar consumer para chequear si existe `story_ids` (lista). Si es así, iterar y crear relaciones `PlanApproval` para cada story.
  - [x] Verificar impacto en `ProjectCase` y grafo de Neo4j.
    - **Resultado:** `PlanApproval` en Neo4j tiene propiedad `story_id`. Si un plan abarca N stories, deberíamos crear N nodos `PlanApproval` o 1 nodo con relaciones a N `ProjectCase`s.
    - **Decisión:** Mantener simple. 1 nodo `PlanApproval` relacionado a N `ProjectCase` nodes. *Nota: La implementación actual usa `upsert_entity` que crea un nodo. Necesitamos cambiar a crear relaciones.*
    - **Acción:** Modificar `_handle_plan_approved` para manejar lista de stories.

- [x] **0.4. Análisis de Orchestrator Service**
  - [x] `AutoDispatchService` usa `plan_id` como pseudo-`task_id` para deliberación.
    - **Resultado:** En `_dispatch_single_deliberation`, se usa `task_id=plan_id`. Esto conceptualmente está mal si la tarea no es el plan completo.
    - **Problema:** `task_description` se construye hardcoded: `f"Implement plan {plan_id} for story {story_id}"`.
  - [x] Desacoplar identificación de tarea de deliberación del `plan_id`.
    - **Estrategia:** Si un plan tiene múltiples stories, deberíamos disparar deliberaciones separadas por story (granularidad fina) O una sola deliberación por plan (granularidad gruesa).
    - **Decisión:** Mantener deliberación por Story si es posible. Si el Plan agrupa stories, iterar sobre `event.story_ids` y despachar `DeliberateUseCase` para cada story.
    - **Acción:** Refactorizar `dispatch_deliberations_for_plan` para iterar sobre stories.

---

## 📅 Fase 1: Domain Layer (Core Business Logic)
*Objetivo: Actualizar las invariantes de dominio para reflejar la nueva jerarquía.*

- [ ] **1.1. Modificar Entity `Task`** (`services/planning/domain/entities/task.py`)
  - [ ] Hacer `story_id` **REQUIRED** (invariante de dominio).
  - [ ] Hacer `plan_id` **OPTIONAL** (`PlanId | None = None`).
  - [ ] Actualizar validaciones en `__post_init__`.F

- [ ] **1.2. Modificar Entity `Plan`** (`services/planning/domain/entities/plan.py`)
  - [ ] Reemplazar `story_id` (single) por `story_ids` (`tuple[StoryId, ...]`).
  - [ ] Validar que `story_ids` no esté vacío.

- [ ] **1.3. Actualizar Value Object `CreateTaskRequest`** (`services/planning/domain/value_objects/requests/create_task_request.py`)
  - [ ] Marcar `story_id` como obligatorio.
  - [ ] Marcar `plan_id` como opcional.

---

## ⚙️ Fase 2: Application Layer (Use Cases)
*Objetivo: Ajustar la lógica de negocio para soportar la creación de tareas sin plan.*

- [ ] **2.1. Actualizar `CreateTaskUseCase`** (`services/planning/application/usecases/create_task_usecase.py`)
  - [ ] Validar existencia de `story_id`.
  - [ ] Eliminar validación estricta de `plan_id` (permitir None).
  - [ ] Ajustar lógica de instanciación de `Task`.

- [ ] **2.2. Actualizar `TaskDerivationResultService`** (`services/planning/application/services/task_derivation_result_service.py`)
  - [ ] Permitir creación de tasks derivadas asociadas solo a `story_id`.
  - [ ] Manejar `plan_id` como opcional en el flujo.

- [ ] **2.3. Actualizar `ListTasksUseCase`** (`services/planning/application/usecases/list_tasks_usecase.py`)
  - [ ] Agregar soporte para filtrar por `story_id` (nuevo filtro principal).
  - [ ] Mantener soporte para filtrar por `plan_id` (opcional).

---

## 🏗️ Fase 3: Infrastructure Layer (Storage & Adapters)
*Objetivo: Actualizar persistencia e índices en Valkey/Neo4j.*

- [ ] **3.1. Actualizar `StoragePort`** (`services/planning/application/ports/storage_port.py`)
  - [ ] Actualizar firmas de métodos `save_task`, `list_tasks` para reflejar opcionalidad de `plan_id`.

- [ ] **3.2. Actualizar `ValkeyStorageAdapter`** (`services/planning/infrastructure/adapters/valkey_adapter.py`)
  - [ ] **Indices:** Asegurar índice `tasks_by_story` (REQUIRED).
  - [ ] **Indices:** Indexar `tasks_by_plan` solo si `plan_id` no es None.
  - [ ] **Queries:** Actualizar `list_tasks` para buscar en el índice correcto según los filtros.

- [ ] **3.3. Actualizar `StorageAdapter`** (Delegator)
  - [ ] Propagar cambios de firma y delegación.

- [ ] **3.4. Actualizar Mappers de Infraestructura**
  - [ ] `TaskValkeyMapper`: Manejar serialización de `plan_id` nulo.
  - [ ] `PlanValkeyMapper`: Manejar lista de `story_ids`.

---

## 🔌 Fase 4: API Layer (gRPC & Protobuf)
*Objetivo: Exponer la nueva estructura a través de la API pública.*

- [ ] **4.1. Actualizar Protobuf** (`specs/fleet/planning/v2/planning.proto`)
  - [ ] `message Task`: Cambiar `plan_id` a `optional string`.
  - [ ] `message Plan`: Cambiar `story_id` a `repeated string story_ids`.
  - [ ] `message CreateTaskRequest`: Ajustar opcionalidad.

- [ ] **4.2. Regenerar Código gRPC**
  - [ ] Ejecutar scripts de generación de código (`make proto` o similar).

- [ ] **4.3. Actualizar Handlers gRPC**
  - [ ] `create_task_handler.py`: Extraer `story_id` obligatorio, `plan_id` opcional.
  - [ ] `list_tasks_handler.py`: Soportar filtros actualizados.

- [ ] **4.4. Actualizar `ResponseMapper`**
  - [ ] Mapear correctamente campos opcionales hacia la respuesta gRPC.

---

## 🤖 Fase 5: Task Derivation Service (Consumer)
*Objetivo: Alinear el servicio consumidor con los cambios de contrato.*

- [ ] **5.1. Actualizar `TaskCreationCommand`**
  - [ ] Reflejar cambio de opcionalidad en el comando interno.

- [ ] **5.2. Actualizar Mappers de Integración**
  - [ ] Ajustar mapping de mensajes NATS/gRPC a comandos de dominio.

---

## 🧪 Fase 6: Tests & Verificación
*Objetivo: Asegurar que nada se rompió y que la nueva lógica funciona.*

- [ ] **6.1. Unit Tests (Domain)**
  - [ ] Testear creación de Task sin Plan.
  - [ ] Testear Plan con múltiples Stories.

- [ ] **6.2. Unit Tests (Application)**
  - [ ] Testear Use Cases con y sin `plan_id`.

- [ ] **6.3. Unit Tests (Infrastructure)**
  - [ ] Verificar persistencia e indexación en Mock Valkey.

- [ ] **6.4. Integration Tests**
  - [ ] Verificar flujo completo: Crear Story -> Crear Task (sin Plan).

---

## 📝 Notas de Implementación
- **Compatibilidad:** Los cambios en Protobuf usan `optional` para `plan_id`, lo que debería minimizar roturas en clientes viejos, pero `story_id` se vuelve mandatorio.
- **Migración de Datos:** Como el proyecto está en desarrollo (alpha), no se requiere script de migración de datos complejos, pero se recomienda limpiar la BD (`FLUSHDB` en Valkey) si hay inconsistencias.

