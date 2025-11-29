# Jerarquía Actual del Dominio

**Fecha**: 2025-01-XX
**Objetivo**: Documentar la jerarquía actual vs la jerarquía deseada

---

## 📋 Jerarquía ACTUAL (según código)

```
Project
  └── Epic
      └── Story (Historia de Usuario)
          └── Plan (Plan de Implementación)
              └── Task
```

### Relaciones Actuales

1. **Project** (raíz)
   - `project_id: ProjectId`
   - No tiene padre

2. **Epic**
   - `epic_id: EpicId`
   - `project_id: ProjectId` (REQUIRED - domain invariant)
   - Pertenece a un Project

3. **Story** (Historia de Usuario)
   - `story_id: StoryId`
   - `epic_id: EpicId` (REQUIRED - domain invariant)
   - Pertenece a un Epic

4. **Plan** (Plan de Implementación)
   - `plan_id: PlanId`
   - `story_id: StoryId` (REQUIRED - domain invariant)
   - Pertenece a una Story
   - Contiene: description, acceptance_criteria, technical_notes, roles

5. **Task**
   - `task_id: TaskId`
   - `plan_id: PlanId` (REQUIRED - domain invariant)
   - `story_id: StoryId` (denormalized para búsquedas rápidas)
   - **Pertenece a un Plan** (relación directa)
   - **Pertenece a una Story** (denormalizado)

---

## 📋 Jerarquía DESEADA (según usuario)

```
Project
  └── Epic
      └── Story (Historia de Usuario)
          └── Task
```

**Plan como agregado:**
- Plan es una **agrupación extra** de historias de usuario
- Plan NO está en la jerarquía principal
- Plan es un agregado que agrupa múltiples Stories

---

## ⚠️ DISCREPANCIA IDENTIFICADA

### Problema 1: Task pertenece a Plan (no a Story)

**Código actual:**
```python
# services/planning/domain/entities/task.py
@dataclass(frozen=True)
class Task:
    plan_id: PlanId  # REQUIRED - domain invariant
    story_id: StoryId  # denormalized
```

**Problema**: Task tiene `plan_id` como REQUIRED, pero según la jerarquía deseada, Task debería pertenecer directamente a Story.

### Problema 2: Plan pertenece a Story (no agrupa Stories)

**Código actual:**
```python
# services/planning/domain/entities/plan.py
@dataclass(frozen=True)
class Plan:
    plan_id: PlanId
    story_id: StoryId  # REQUIRED - parent story (domain invariant)
```

**Problema**: Plan tiene `story_id` (pertenece a una Story), pero según la jerarquía deseada, Plan debería agrupar múltiples Stories.

### Problema 3: Plan en la jerarquía vs Plan como agregado

**Código actual**: Plan está en la jerarquía `Story → Plan → Task`

**Deseado**: Plan es un agregado que agrupa Stories, NO está en la jerarquía principal.

---

## 🔍 Evidencia en el Código

### Task Entity
```python
# services/planning/domain/entities/task.py:39-40
plan_id: PlanId  # Planning Service provides from context (domain invariant)
story_id: StoryId  # Planning Service provides from context (denormalized)
```

**Comentario en código**: "Domain invariant: Task MUST belong to a PlanVersion (plan_id/story_id required)"

### Plan Entity
```python
# services/planning/domain/entities/plan.py:32
story_id: StoryId  # REQUIRED - parent story (domain invariant)
```

**Comentario en código**: "DOMAIN INVARIANT: Plan MUST belong to a Story. NO orphan plans allowed."

### Task Derivation Service
```python
# services/planning/application/services/task_derivation_result_service.py:163-164
plan_id=plan_id,  # Planning Service provides from context (REQUIRED)
story_id=story_id,  # Planning Service provides from context (REQUIRED)
```

**Comentario**: Task se crea con `plan_id` REQUIRED.

---

## 💡 Cambios Necesarios

### 1. Task Entity

**Cambio**: `plan_id` pasa de REQUIRED a OPCIONAL

```python
# ANTES
plan_id: PlanId  # REQUIRED - domain invariant
story_id: StoryId  # denormalized

# DESPUÉS
story_id: StoryId  # REQUIRED - domain invariant
plan_id: PlanId | None = None  # OPCIONAL - solo para ceremonia de planning
```

**Razón**: Task debe poder existir sin Plan para replanificación individual.

### 2. Plan Entity

**Cambio**: `story_id` se convierte en `story_ids` (agrupación)

```python
# ANTES
story_id: StoryId  # REQUIRED - parent story (domain invariant)

# DESPUÉS
story_ids: tuple[StoryId, ...]  # REQUIRED - agrupación de Stories
```

**Razón**: Plan agrupa múltiples Stories, no pertenece a una Story.

### 3. Jerarquía Final

```
Project
  └── Epic
      └── Story
          └── Task (story_id REQUIRED, plan_id OPCIONAL)

Plan (agregado separado)
  └── Agrupa: story_ids: tuple[StoryId, ...]
```

**Razón**: Plan es un agregado separado para la ceremonia de planning.

---

## ✅ Respuestas Confirmadas

1. **Plan agrupa múltiples Stories**
   - Plan es una **planificación de historias de usuario**
   - Plan contiene una **agrupación de historias de usuario**
   - Plan NO pertenece a una Story

2. **Task pertenece directamente a Story**
   - Task es **dependiente de Story**
   - Task puede existir sin Plan (para replanificación individual)
   - Task debe tener `story_id` REQUIRED
   - Task debe tener `plan_id` OPCIONAL

3. **Plan es un agregado separado**
   - Plan NO está en la jerarquía principal
   - Plan es un agregado que agrupa Stories para planificación
   - Plan se usa durante la ceremonia de planning

---

## 🎯 Caso de Uso Clave

**Problema actual**: Task requiere Plan, pero un usuario debe poder:
- Ver una Story individual
- Replanificar una Story sin necesidad de un Plan
- Crear Tasks para una Story sin crear un Plan

**Solución**: Task debe poder existir sin Plan, solo con Story.

**Durante la ceremonia de planning**:
- Se crea un Plan que agrupa múltiples Stories
- Se crean Tasks para esas Stories (con `plan_id` opcional)
- El Plan es solo una agrupación/vista para la ceremonia

**Fuera de la ceremonia**:
- Un usuario puede crear Tasks para una Story individual
- No necesita crear un Plan
- Task solo necesita `story_id`

---

## 📝 Notas

- El código actual refleja: `Project → Epic → Story → Plan → Task`
- La jerarquía deseada es: `Project → Epic → Story → Task`
- Plan debería ser un agregado que agrupa Stories, no parte de la jerarquía

