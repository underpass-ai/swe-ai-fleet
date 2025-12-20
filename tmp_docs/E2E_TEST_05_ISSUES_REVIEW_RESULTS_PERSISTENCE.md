# E2E Test 05: Issues with Review Results Persistence

**Fecha:** 2025-12-20
**Test:** `05-validate-deliberations-and-tasks`
**Ceremony ID:** `BRC-a5fe4346-e895-4abd-bf4d-c3e68dbde439`
**Estado:** ⚠️ Test bloqueado esperando review results

---

## 📋 Resumen Ejecutivo

El test E2E 05 está funcionando parcialmente:
- ✅ **Eventos canónicos funcionando**: Los eventos de task extraction se están publicando correctamente en formato canónico
- ✅ **Deliberaciones procesándose**: BRP está recibiendo y procesando deliberaciones correctamente
- ❌ **Review Results no se persisten**: Planning Service no está recibiendo las deliberaciones individuales, por lo que la ceremonia no tiene `review_results`
- ❌ **Tasks no se crean**: Las tasks no se están creando porque `'BACKLOG_REVIEW_IDENTIFIED'` no es un TaskType válido

**Resultado:** El test queda bloqueado en la Etapa 5 esperando que la ceremonia tenga `review_results` con feedback de los 3 roles (ARCHITECT, QA, DEVOPS), pero estos nunca aparecen porque BRP no está guardando las deliberaciones en Planning Service.

---

## 🔍 Comportamiento Observado

### 1. Eventos Canónicos Funcionando ✅

**Evidencia:**
```
2025-12-20 14:37:01,889 - backlog_review_processor.infrastructure.consumers.task_extraction_result_consumer - INFO - 📥 Received canonical task extraction event: ceremony-BRC-a5fe4346-e895-4abd-bf4d-c3e68dbde439:story-s-6cb06f84-d6cf-415f-b24d-261cd6397009:task-extraction (story: s-6cb06f84-d6cf-415f-b24d-261cd6397009, ceremony: BRC-a5fe4346-e895-4abd-bf4d-c3e68dbde439, tasks: 4)
```

**Análisis:**
- Los eventos de task extraction están llegando en formato canónico (con campo `tasks` ya parseado)
- El fix implementado en `execute_agent_task.py` y `ray_cluster_adapter.py` está funcionando correctamente
- La detección de task extraction por `original_task_id` está funcionando

### 2. Deliberaciones Procesándose ✅

**Evidencia:**
```
2025-12-20 14:36:51,277 - backlog_review_processor.application.usecases.accumulate_deliberations_usecase - INFO - 📥 Accumulated and saved deliberation: ceremony=BRC-a5fe4346-e895-4abd-bf4d-c3e68dbde439, story=s-6cb06f84-d6cf-415f-b24d-261cd6397009, role=ARCHITECT, agent=agent-architect-003, total=6
2025-12-20 14:36:51,277 - backlog_review_processor.application.usecases.accumulate_deliberations_usecase - INFO - ✅ All role deliberations complete for story s-6cb06f84-d6cf-415f-b24d-261cd6397009 in ceremony BRC-a5fe4346-e895-4abd-bf4d-c3e68dbde439. Publishing deliberations complete event.
```

**Análisis:**
- BRP está recibiendo deliberaciones de todos los roles (ARCHITECT, QA, DEVOPS)
- Las deliberaciones se están guardando en Neo4j correctamente
- Los eventos de "deliberations complete" se están publicando cuando todas las deliberaciones de un story están completas

### 3. Review Results No Se Persisten ❌

**Síntoma:**
```
ℹ Polling ceremony status (attempt 35/60)... Status: IN_PROGRESS, Review Results: 0/4
```

El test está esperando que la ceremonia tenga `review_results` con feedback de los 3 roles, pero estos nunca aparecen.

**Evidencia de que Planning Service recibe eventos pero no guarda:**
```
2025-12-20 14:36:42,970 [INFO] planning.infrastructure.consumers.deliberations_complete_progress_consumer: 📥 Received deliberations complete event: ceremony=BRC-a5fe4346-e895-4abd-bf4d-c3e68dbde439, story=s-11b74fc3-0c88-4350-b5fc-8a95b981c3be
2025-12-20 14:36:42,975 [INFO] planning.infrastructure.consumers.deliberations_complete_progress_consumer: ✅ Deliberations complete for story s-11b74fc3-0c88-4350-b5fc-8a95b981c3be in ceremony BRC-a5fe4346-e895-4abd-bf4d-c3e68dbde439
```

**Causa Raíz:**
1. **BRP no está llamando a `AddAgentDeliberation` gRPC**: BRP solo guarda las deliberaciones en Neo4j y publica eventos, pero no está actualizando Planning Service con las deliberaciones individuales.

2. **`DeliberationsCompleteProgressConsumer` solo loguea**: El consumer de Planning Service que recibe los eventos de "deliberations complete" solo loguea el evento pero no guarda los review results en la ceremonia.

**Código Problemático:**
```python
# services/planning/infrastructure/consumers/deliberations_complete_progress_consumer.py
# 3. Update ceremony progress (mark story deliberations as complete)
# For now, we'll just log it. The ceremony entity can be extended
# to track which stories have completed deliberations if needed.
logger.info(
    f"✅ Deliberations complete for story {story_id.value} "
    f"in ceremony {ceremony_id.value}"
)
```

**Flujo Esperado vs. Real:**

**Flujo Esperado:**
1. BRP recibe `agent.response.completed` para cada deliberación
2. BRP llama a Planning Service `AddAgentDeliberation` gRPC para guardar cada deliberación
3. Planning Service guarda el review result en la ceremonia
4. Cuando todas las deliberaciones de un story están completas, BRP publica evento `deliberations.complete`
5. Planning Service recibe el evento y verifica que todos los review results estén guardados
6. Planning Service actualiza el estado de la ceremonia a `REVIEWING`

**Flujo Real:**
1. BRP recibe `agent.response.completed` para cada deliberación ✅
2. BRP guarda en Neo4j ✅
3. BRP **NO** llama a Planning Service `AddAgentDeliberation` ❌
4. Cuando todas las deliberaciones están completas, BRP publica evento `deliberations.complete` ✅
5. Planning Service recibe el evento pero solo loguea, no guarda review results ❌
6. La ceremonia nunca tiene `review_results`, por lo que nunca cambia a `REVIEWING` ❌

### 4. Tasks No Se Crean ❌

**Evidencia:**
```
2025-12-20 14:36:57,891 [WARNING] planning.infrastructure.grpc.handlers.create_task_handler: CreateTask validation error: 'BACKLOG_REVIEW_IDENTIFIED' is not a valid TaskType
```

**Causa Raíz:**
BRP está intentando crear tasks con `type="BACKLOG_REVIEW_IDENTIFIED"`, pero este TaskType no existe en Planning Service.

**Código Problemático:**
```python
# services/backlog_review_processor/infrastructure/adapters/planning_service_adapter.py
proto_request = planning_pb2.CreateTaskRequest(
    story_id=request.story_id.value,
    plan_id="",  # Tasks from backlog review don't have plan yet
    title=request.title,
    description=request.description,
    type="BACKLOG_REVIEW_IDENTIFIED",  # ❌ Este TaskType no existe
    assigned_to="",  # Will be assigned later
    estimated_hours=request.estimated_hours,
    priority=1,  # Default priority, will be adjusted later
)
```

---

## 🎯 Problemas Identificados

### Problema 1: BRP No Guarda Deliberaciones en Planning Service

**Archivo:** `services/backlog_review_processor/application/usecases/accumulate_deliberations_usecase.py`

**Problema:**
- `AccumulateDeliberationsUseCase` solo guarda las deliberaciones en Neo4j
- No llama a Planning Service `AddAgentDeliberation` gRPC para actualizar la ceremonia con los review results

**Impacto:**
- Planning Service nunca tiene los review results en la ceremonia
- El test E2E 05 nunca puede completar la Etapa 5
- La ceremonia nunca cambia a estado `REVIEWING`

**Solución Propuesta:**
1. Agregar `PlanningPort` como dependencia de `AccumulateDeliberationsUseCase`
2. Llamar a `AddAgentDeliberation` después de guardar en Neo4j
3. Manejar errores de gRPC de forma resiliente (no bloquear el flujo si Planning Service está caído)

### Problema 2: DeliberationsCompleteProgressConsumer Solo Loguea

**Archivo:** `services/planning/infrastructure/consumers/deliberations_complete_progress_consumer.py`

**Problema:**
- El consumer solo loguea el evento pero no actualiza la ceremonia
- El comentario en el código dice "For now, we'll just log it"

**Impacto:**
- Aunque BRP llamara a `AddAgentDeliberation`, el consumer no verificaría que todos los review results estén completos
- La ceremonia nunca cambiaría a estado `REVIEWING` automáticamente

**Solución Propuesta:**
1. Implementar lógica para verificar que todos los review results de un story tengan los 3 roles
2. Actualizar el estado de la ceremonia a `REVIEWING` cuando todas las stories tengan review results completos
3. Persistir la ceremonia actualizada

### Problema 3: TaskType 'BACKLOG_REVIEW_IDENTIFIED' No Existe

**Archivo:** `services/backlog_review_processor/infrastructure/adapters/planning_service_adapter.py`

**Problema:**
- BRP intenta crear tasks con `type="BACKLOG_REVIEW_IDENTIFIED"`
- Este TaskType no está definido en Planning Service

**Impacto:**
- Las tasks no se crean, fallando con `StatusCode.INVALID_ARGUMENT`
- El test E2E 05 no puede completar las etapas 6-12 (Task Creation Execution)

**Solución Propuesta:**
1. Verificar qué TaskTypes están disponibles en Planning Service
2. Usar un TaskType válido (por ejemplo, `"TASK"` o agregar `"BACKLOG_REVIEW_IDENTIFIED"` al enum)
3. O usar un campo diferente para identificar tasks de backlog review

---

## 📊 Estado del Test

**Etapa Actual:** Etapa 5 - Deliberations Complete
**Intento:** 35/60 (timeout: 600s, poll interval: 10s)
**Estado Ceremonia:** `IN_PROGRESS`
**Review Results:** `0/4` (esperado: `4/4`)
**Tiempo Transcurrido:** ~350 segundos

**Logs Relevantes:**
```
ℹ Polling ceremony status (attempt 35/60)... Status: IN_PROGRESS, Review Results: 0/4
```

---

## 🔧 Fixes Implementados (Funcionando)

### Fix 1: Eventos Canónicos para Task Extraction ✅

**Archivos Modificados:**
- `core/ray_jobs/application/execute_agent_task.py`
- `services/ray_executor/infrastructure/adapters/ray_cluster_adapter.py`
- `e2e/tests/05-validate-deliberations-and-tasks/validate_deliberations_and_tasks.py`

**Cambios:**
1. Agregado fallback para usar `request.task_id` si `metadata.task_id` está ausente
2. Asegurado que `task_id` siempre esté en metadata en Ray Executor
3. Test E2E 05 modificado para siempre crear nueva ceremonia (evita reutilizar ceremonias antiguas)

**Resultado:**
- Los eventos de task extraction ahora se publican en formato canónico
- BRP puede procesar los eventos sin errores de "non-canonical format"
- La idempotencia funciona correctamente (duplicados se ignoran)

---

## 📝 Próximos Pasos

### Prioridad Alta

1. **Implementar guardado de deliberaciones en Planning Service**
   - Modificar `AccumulateDeliberationsUseCase` para llamar a `AddAgentDeliberation`
   - Manejar errores de gRPC de forma resiliente
   - Agregar tests unitarios

2. **Implementar actualización de ceremonia en DeliberationsCompleteProgressConsumer**
   - Verificar que todos los review results estén completos
   - Actualizar estado a `REVIEWING` cuando corresponda
   - Persistir la ceremonia actualizada

3. **Corregir TaskType para tasks de backlog review**
   - Verificar TaskTypes disponibles en Planning Service
   - Usar TaskType válido o agregar nuevo tipo al enum

### Prioridad Media

4. **Mejorar logging y observabilidad**
   - Agregar métricas para tracking de deliberaciones
   - Mejorar mensajes de error para debugging

5. **Agregar tests E2E más granulares**
   - Test para validar guardado de deliberaciones individuales
   - Test para validar transición de estado de ceremonia

---

## 🔗 Referencias

- **PR relacionado:** `PR_FIX_CEREMONY_STORIES_PERSISTENCE.md` (persistencia de stories, no review results)
- **Test E2E:** `e2e/tests/05-validate-deliberations-and-tasks/`
- **BRP Use Case:** `services/backlog_review_processor/application/usecases/accumulate_deliberations_usecase.py`
- **Planning Consumer:** `services/planning/infrastructure/consumers/deliberations_complete_progress_consumer.py`
- **Planning Adapter:** `services/backlog_review_processor/infrastructure/adapters/planning_service_adapter.py`

---

## ✅ Checklist de Verificación

- [x] Eventos canónicos funcionando
- [x] Deliberaciones procesándose en BRP
- [x] Deliberaciones guardadas en Neo4j
- [ ] Deliberaciones guardadas en Planning Service (via AddAgentDeliberation)
- [ ] Review results visibles en ceremonia
- [ ] Ceremonia cambia a estado REVIEWING
- [ ] Tasks se crean correctamente
- [ ] Test E2E 05 completa exitosamente

---

**Última Actualización:** 2025-12-20 14:42 UTC
