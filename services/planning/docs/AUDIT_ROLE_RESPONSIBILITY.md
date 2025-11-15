# Auditoría: Responsabilidad de ROLE en Task Derivation

**Fecha:** 2025-11-14
**Autor:** AI Assistant
**Contexto:** Revisión crítica de responsabilidades - ROLE no debe venir del LLM, debe venir del evento de dominio
**Estado:** 🔴 CRÍTICO - Requiere refactorización

---

## 📋 Resumen Ejecutivo

**PROBLEMA IDENTIFICADO:** El campo `ROLE` está siendo parseado del LLM cuando **NO debería venir del LLM**. El ROLE debe venir del **evento de dominio** que dispara la derivación de tareas.

### Problema Crítico

- **Actual:** LLM genera `ROLE` en su output → Mapper parsea `ROLE` → TaskNode tiene `role` → TaskDerivationResultService usa `role` del LLM
- **Correcto:** Evento de dominio contiene `ROLE` → TaskDerivationResultService obtiene `ROLE` del evento → Planning Service decide assignment basándose en RBAC + ROLE del evento

---

## 🔍 Análisis del Problema

### Flujo Actual (INCORRECTO)

```
1. planning.plan.approved event → PlanApprovedConsumer
2. PlanApprovedConsumer → DeriveTasksFromPlanUseCase
3. DeriveTasksFromPlanUseCase → LLM (prompt incluye ROLE)
4. LLM genera output con ROLE: DEVELOPER
5. LLMTaskDerivationMapper.parse() → extrae ROLE del LLM
6. TaskNode(role=Role(DEVELOPER)) ← ROLE del LLM
7. TaskDerivationResultService → usa task_node.role ← INCORRECTO
8. CreateTaskRequest(assigned_to=task_node.role) ← INCORRECTO
```

**Problemas:**
- ❌ LLM decide el ROLE (no debería)
- ❌ ROLE viene del LLM, no del evento de dominio
- ❌ No hay validación RBAC del ROLE
- ❌ El evento `planning.plan.approved` probablemente contiene información de ROLE que se ignora

### Flujo Correcto (PROPUESTO)

```
1. planning.plan.approved event → contiene ROLE (del contexto del plan/story)
2. PlanApprovedConsumer → extrae ROLE del evento
3. DeriveTasksFromPlanUseCase → NO incluye ROLE en prompt al LLM
4. LLM genera output SIN ROLE
5. LLMTaskDerivationMapper.parse() → NO parsea ROLE
6. TaskNode → NO tiene campo role (o es opcional)
7. TaskDerivationResultService → obtiene ROLE del evento de dominio
8. TaskDerivationResultService → valida ROLE con RBAC
9. CreateTaskRequest(assigned_to=role_validado_con_rbac) ← CORRECTO
```

---

## 📊 Estado Actual del Código

### 1. Prompt Template (`config/task_derivation.yaml`)

**Estado:** ❌ INCORRECTO - Incluye ROLE en instrucciones

```yaml
For each task, provide:
  3. **ROLE**: Assigned role (DEV, QA, ARCHITECT, PO)  ← INCORRECTO
```

**Debe ser:** Eliminar ROLE del prompt, LLM no debe generar ROLE

### 2. LLMTaskDerivationMapper (`planning/infrastructure/mappers/llm_task_derivation_mapper.py`)

**Estado:** ❌ INCORRECTO - Parsea ROLE del LLM

```python
role_match = re.search(r"ROLE:\s*(.+?)" + field_boundary, ...)  ← Línea 138-142
role_str = role_match.group(1).strip().upper()
role = LLMTaskDerivationMapper._map_role(role_str)  ← INCORRECTO
```

**Debe ser:** Eliminar parsing de ROLE, ROLE viene del evento de dominio

### 3. TaskNode (`planning/domain/value_objects/task_derivation/task_node.py`)

**Estado:** ⚠️ REVISAR - Tiene campo `role: Role`

```python
role: Role  # ← ¿Es necesario para dependency graph?
```

**Pregunta:** ¿TaskNode necesita `role` para el grafo de dependencias? Si no, eliminarlo.

### 4. TaskDerivationResultService (`planning/application/services/task_derivation_result_service.py`)

**Estado:** ❌ INCORRECTO - Usa ROLE del LLM

```python
assigned_role = task_node.role  # LLM role hint ← INCORRECTO
assigned_to=assigned_role,  # Planning Service decides (RBAC) ← INCORRECTO
```

**Debe ser:** Obtener ROLE del evento de dominio, validar con RBAC

### 5. Evento de Dominio (`planning.plan.approved`)

**Estado:** ✅ ENCONTRADO - El evento contiene `roles: list[str]`

**Estructura del evento (según Orchestrator):**
```python
PlanApprovedEvent:
    story_id: str
    plan_id: str
    approved_by: str
    roles: list[str]  # ← ROLES vienen aquí del evento
    timestamp: str
```

**Plan Entity también tiene roles:**
```python
Plan:
    roles: tuple[str, ...] = ()  # Roles needed for execution
```

**Problema actual:**
- `PlanApprovedConsumer` solo extrae `plan_id` del evento
- **NO extrae `roles` del evento**
- `roles` del evento se ignoran completamente

---

## 🎯 Preguntas Críticas a Resolver

### 1. ¿Qué evento dispara la derivación de tareas?

**Respuesta:** ✅ `planning.plan.approved`

**Estructura confirmada:**
- Evento: `planning.plan.approved`
- Contiene: `plan_id`, `story_id`, `approved_by`, **`roles: list[str]`**, `timestamp`
- Ubicación: `services/orchestrator/domain/entities/incoming_events.py:77-95`
- El evento **SÍ contiene `roles`** - pero el consumer actual lo ignora

### 2. ¿De dónde viene el ROLE en el contexto del plan/story?

**Respuesta:** ✅ Del evento `planning.plan.approved` - campo `roles: list[str]`

**Confirmado:**
- El evento `planning.plan.approved` contiene `roles: list[str]`
- El `Plan` entity también tiene `roles: tuple[str, ...]`
- Los roles vienen del contexto del plan (quién lo aprobó, qué roles se necesitan)
- **Problema:** El consumer actual ignora completamente el campo `roles` del evento

### 3. ¿TaskNode necesita `role` para dependency graph?

**Análisis:**
- Dependency graph usa keywords para detectar dependencias
- `role` no parece necesario para dependency analysis
- `role` se usa solo para assignment, no para dependencias

**Conclusión probable:** TaskNode NO necesita `role` para dependency graph

### 4. ¿Cómo fluye el ROLE desde el evento hasta la creación de la tarea?

**Flujo propuesto:**
```
planning.plan.approved event
  ↓ (contiene roles: list[str] del evento)
PlanApprovedConsumer
  ↓ (extrae plan_id Y roles del evento)
DeriveTasksFromPlanUseCase.execute(plan_id, roles_from_event)
  ↓ (pasa roles al servicio, NO al LLM)
TaskDerivationResultService.process(plan_id, task_nodes, roles_from_event)
  ↓ (usa roles del evento para assignment, NO del LLM)
CreateTaskRequest(assigned_to=role_validated_with_rbac_from_event)
```

**Cambios específicos:**
1. `PlanApprovedConsumer._handle_message()` → extraer `roles` del payload
2. `DeriveTasksFromPlanUseCase.execute()` → agregar parámetro `roles: list[str]`
3. `TaskDerivationResultService.process()` → agregar parámetro `roles: list[str]`
4. Eliminar `ROLE` del prompt template
5. Eliminar parsing de `ROLE` del mapper
6. Hacer `role` opcional en `TaskNode` o eliminarlo

---

## 🔧 Cambios Requeridos

### Fase 1: Investigación (✅ COMPLETADA)

1. **Identificar evento de dominio:** ✅ COMPLETADO
   - Evento: `planning.plan.approved`
   - Ubicación: `services/orchestrator/domain/entities/incoming_events.py:77-95`
   - Contiene: `plan_id`, `story_id`, `approved_by`, **`roles: list[str]`**, `timestamp`

2. **Mapear flujo completo:** ✅ COMPLETADO
   - Evento dispara: `PlanApprovedConsumer` (línea 102-126)
   - Información del evento: `plan_id` (extraído), **`roles` (IGNORADO actualmente)**
   - ROLE viene del campo `roles` del evento, NO del LLM

### Fase 2: Refactorización (DESPUÉS de investigación)

1. **Eliminar ROLE del prompt template:**
   - Remover `ROLE` de instrucciones
   - Actualizar ejemplos sin ROLE

2. **Eliminar parsing de ROLE del mapper:**
   - Remover regex para ROLE
   - Remover validación de ROLE
   - Remover `_map_role()` si no se usa en otro lugar

3. **Hacer `role` opcional en TaskNode:**
   - Si no es necesario para dependency graph, eliminarlo
   - Si es necesario, hacerlo opcional y obtenerlo del evento

4. **Modificar TaskDerivationResultService:**
   - Agregar parámetro `role` del evento de dominio
   - Eliminar uso de `task_node.role`
   - Validar ROLE con RBAC antes de asignar

5. **Modificar PlanApprovedConsumer:**
   - Extraer ROLE del evento de dominio
   - Pasar ROLE a TaskDerivationResultService

---

## 📝 Archivos Afectados

### Archivos a Modificar:

1. `config/task_derivation.yaml`
   - Eliminar ROLE de instrucciones
   - Actualizar ejemplos

2. `planning/infrastructure/mappers/llm_task_derivation_mapper.py`
   - Eliminar parsing de ROLE (líneas 138-142)
   - Eliminar `_map_role()` si no se usa
   - Actualizar documentación

3. `planning/domain/value_objects/task_derivation/task_node.py`
   - Hacer `role` opcional o eliminarlo
   - Actualizar documentación

4. `planning/application/services/task_derivation_result_service.py`
   - Agregar parámetro `role` del evento
   - Eliminar uso de `task_node.role`
   - Validar con RBAC

5. `planning/infrastructure/consumers/plan_approved_consumer.py`
   - Extraer ROLE del evento
   - Pasar ROLE al servicio

### Archivos a Investigar:

1. Eventos de dominio relacionados con Plan
2. Estructura del evento `planning.plan.approved`
3. Cómo se determina ROLE desde el contexto del plan/story

---

## ⚠️ Riesgos y Consideraciones

### Riesgos:

1. **Breaking changes:** Si otros servicios dependen de `task_node.role`
2. **Dependency graph:** Verificar que no necesita `role` para funcionar
3. **Tests:** Actualizar todos los tests que crean TaskNode con `role`

### Consideraciones:

1. **RBAC:** El ROLE del evento debe validarse con RBAC antes de asignar
2. **Fallback:** ¿Qué pasa si el evento no tiene ROLE? ¿Default a DEVELOPER?
3. **Múltiples roles:** ¿Un plan puede tener múltiples roles? ¿Cómo se maneja?

---

## ✅ Criterios de Éxito

1. ✅ LLM NO genera ROLE en su output
2. ✅ Mapper NO parsea ROLE del LLM
3. ✅ ROLE viene del evento de dominio
4. ✅ TaskDerivationResultService obtiene ROLE del evento
5. ✅ ROLE se valida con RBAC antes de asignar
6. ✅ Tests actualizados y pasando
7. ✅ Documentación actualizada

---

## 🚨 ACCIÓN INMEDIATA REQUERIDA

**ANTES de hacer cambios:**

1. **Investigar evento de dominio:**
   - ¿Qué evento dispara la derivación?
   - ¿Qué información contiene?
   - ¿Cómo se determina ROLE?

2. **Mapear flujo completo:**
   - Desde evento → consumer → use case → service → task creation
   - Identificar dónde debe fluir el ROLE

3. **Validar con arquitecto:**
   - Confirmar de dónde viene el ROLE
   - Confirmar cómo debe fluir
   - Confirmar validación RBAC

**NO proceder con cambios hasta completar investigación.**

---

## 📚 Referencias

- [AUDIT_TASK_ID_RESPONSIBILITY.md](./AUDIT_TASK_ID_RESPONSIBILITY.md) - Auditoría similar sobre IDs
- [RBAC_REVIEW.md](./RBAC_REVIEW.md) - Revisión de RBAC
- [Task Derivation Flow](../../../docs/architecture/TASK_DERIVATION_FLOW.md) - Flujo de derivación de tareas

---

**Estado:** 🟡 LISTO PARA REFACTORIZACIÓN - Investigación completada, cambios identificados.

**Hallazgos clave:**
- ✅ Evento `planning.plan.approved` contiene `roles: list[str]`
- ✅ `PlanApprovedConsumer` actualmente ignora el campo `roles`
- ✅ `Plan` entity tiene `roles: tuple[str, ...]`
- ✅ ROLE debe venir del evento, NO del LLM
- ✅ Cambios requeridos identificados y documentados

