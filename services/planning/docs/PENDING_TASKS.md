# Planning Service - Tareas Pendientes

**Fecha:** 2025-11-14
**Estado:** 🟡 En progreso - Issues críticos identificados

---

## 🔴 CRÍTICO - Task Derivation (No Confiable)

### 1. ROLE debe venir del evento, NO del LLM

**Problema:** Según `AUDIT_ROLE_RESPONSIBILITY.md`, ROLE está siendo parseado del LLM cuando debe venir del evento `planning.plan.approved`.

**Tareas requeridas:**

1. **Eliminar ROLE del prompt template** (`config/task_derivation.yaml`)
   - [x] Remover `ROLE` de las instrucciones del LLM
   - [x] Actualizar ejemplo de output para no incluir ROLE

2. **Eliminar parsing de ROLE** (`llm_task_derivation_mapper.py`)
   - [x] Remover regex que parsea `ROLE:` del LLM output
   - [x] Remover método `_map_role()` si ya no se usa
   - [x] Actualizar `TaskNode` para hacer `role` opcional o eliminarlo

3. **Modificar PlanApprovedConsumer** (`plan_approved_consumer.py`)
   - [ ] Extraer `roles` del evento `planning.plan.approved`
   - [ ] Pasar `roles` a `TaskDerivationResultService`

4. **Modificar TaskDerivationResultService** (`task_derivation_result_service.py`)
   - [x] Recibir `roles` del evento (no del LLM) - Usa `plan.roles` del Plan que viene del evento
   - [ ] Validar `roles` con RBAC antes de asignar
   - [x] Remover uso de `task_node.role` del LLM - Completado (TaskNode ya no tiene role)

**Archivos afectados:**
- `config/task_derivation.yaml`
- `planning/infrastructure/mappers/llm_task_derivation_mapper.py`
- `planning/domain/value_objects/task_derivation/task_node.py`
- `planning/infrastructure/consumers/plan_approved_consumer.py`
- `planning/application/services/task_derivation_result_service.py`

**Referencia:** `docs/AUDIT_ROLE_RESPONSIBILITY.md`

---

### 2. Parsing del LLM no es confiable

**Problema:** El LLM no es idempotente, el parsing puede fallar silenciosamente.

**Tareas requeridas:**

1. **Mejorar robustez del parsing** (`llm_task_derivation_mapper.py`)
   - [ ] Hacer regex más flexible para variaciones del LLM
   - [ ] Agregar validación exhaustiva de campos parseados
   - [ ] Agregar logging detallado cuando el parsing falla
   - [ ] Manejar casos edge (campos faltantes, valores inválidos)

2. **Agregar validación de output del LLM**
   - [ ] Validar que todos los campos requeridos estén presentes
   - [ ] Validar rangos (priority 1-10, estimated_hours 1-40)
   - [ ] Validar formato de keywords
   - [ ] Fallar rápido si el output es inválido

3. **Mejorar manejo de errores**
   - [ ] Publicar evento `task.derivation.failed` con detalles del error
   - [ ] Notificar al PO cuando el parsing falla
   - [ ] Permitir re-derivación manual

**Archivos afectados:**
- `planning/infrastructure/mappers/llm_task_derivation_mapper.py`
- `planning/application/services/task_derivation_result_service.py`

---

### 3. Dependencias basadas en keywords pueden ser incorrectas

**Problema:** El cálculo de dependencias basado en keyword matching puede generar dependencias incorrectas.

**Tareas requeridas:**

1. **Revisar algoritmo de dependencias** (`dependency_graph.py`)
   - [ ] Validar que el keyword matching es correcto
   - [ ] Agregar tests para casos edge
   - [ ] Mejorar logging de cómo se calculan las dependencias

2. **Considerar alternativas**
   - [ ] Evaluar si el LLM debería generar dependencias explícitas
   - [ ] O si el keyword matching necesita ser más inteligente

**Archivos afectados:**
- `planning/domain/value_objects/task_derivation/dependency_graph.py`

---

## ⚠️ IMPORTANTE - RBAC Integration

### 4. Integración completa de RBAC para assignment

**Problema:** Actualmente hay un TODO en el código: "Planning Service should decide assignment based on RBAC"

**Tareas requeridas:**

1. **Definir cómo Planning Service integra con RBAC**
   - [ ] Revisar `RBAC_REVIEW.md` para entender niveles de RBAC
   - [ ] Determinar si Planning Service necesita port para RBAC
   - [ ] O si RBAC se valida en otro servicio (Workflow Service)

2. **Implementar validación RBAC**
   - [ ] Crear port para RBAC si es necesario
   - [ ] Validar permisos antes de asignar tasks
   - [ ] Usar roles del evento (no del LLM) para validación

**Archivos afectados:**
- `planning/application/services/task_derivation_result_service.py`
- `planning/application/ports/` (nuevo port si es necesario)

**Referencia:** `docs/RBAC_REVIEW.md`

---

## 🧪 TESTS - Cobertura y Confiabilidad

### 5. Tests de integración para Task Derivation

**Problema:** Task Derivation necesita tests de integración para validar el flujo completo.

**Tareas requeridas:**

1. **Tests de integración end-to-end**
   - [ ] Test: Plan approved → Tasks derived → Tasks stored
   - [ ] Test: LLM output parsing → TaskNode VOs → Tasks created
   - [ ] Test: Dependency graph calculation → Tasks ordered correctly
   - [ ] Test: Circular dependencies detected → Error published

2. **Tests de edge cases**
   - [ ] Test: LLM output inválido → Error handling
   - [ ] Test: LLM output con campos faltantes → Defaults aplicados
   - [ ] Test: Keywords duplicados → Dependencias correctas

**Archivos afectados:**
- `tests/integration/test_task_derivation_integration.py` (nuevo)

---

### 6. Tests E2E mencionados en IMPLEMENTATION_SUMMARY.md

**Problema:** IMPLEMENTATION_SUMMARY.md menciona E2E tests como follow-up pero no están implementados.

**Tareas requeridas:**

1. **E2E tests para flujo completo**
   - [ ] Test: Create Story → Approve Plan → Derive Tasks → Transition Story
   - [ ] Test: Story sin Tasks → Cannot transition to READY_FOR_EXECUTION
   - [ ] Test: Story con Tasks inválidas → PO notified

**Archivos afectados:**
- `tests/e2e/test_planning_workflow_e2e.py` (nuevo)

---

## 📝 DOCUMENTACIÓN - Actualizaciones Pendientes

### 7. Actualizar documentación con correcciones recientes

**Estado:** ARCHITECTURE.md ya fue actualizado con:
- ✅ Plan como Sprint/Iteration (no entidad persistida)
- ✅ Consumidores NATS documentados
- ✅ Eventos NATS completos
- ✅ Jerarquía completa Project → Epic → Story → Task

**Tareas requeridas:**

1. **Actualizar README.md**
   - [ ] Incluir Task Derivation en el flujo
   - [ ] Documentar jerarquía completa
   - [ ] Actualizar ejemplos de uso

2. **Actualizar IMPLEMENTATION_SUMMARY.md**
   - [ ] Incluir Task Derivation en estadísticas
   - [ ] Actualizar con issues conocidos
   - [ ] Marcar tareas pendientes

---

## 🔍 VALIDACIÓN - Verificaciones Finales

### 8. Verificar que no hay imports de core/*

**Problema:** AUDIT_ARCHITECTURE_COMPLIANCE.md menciona verificar imports de `core/shared`.

**Tareas requeridas:**

1. **Auditar imports**
   - [ ] Verificar que no hay imports de `core/*`
   - [ ] Verificar bounded context isolation
   - [ ] Corregir cualquier import incorrecto

**Comando:**
```bash
grep -r "from.*core\.\|import.*core\." services/planning/planning/
```

---

## 📊 RESUMEN DE PRIORIDADES

### 🔴 CRÍTICO (Bloquea confiabilidad):
1. **ROLE debe venir del evento** - Según auditoría previa
2. **Parsing del LLM más robusto** - Usuario indica que no es confiable
3. **Dependencias correctas** - Puede generar dependencias incorrectas

### ⚠️ IMPORTANTE (Mejora funcionalidad):
4. **RBAC Integration** - Assignment necesita validación RBAC
5. **Tests de integración** - Validar flujo completo
6. **Tests E2E** - Validar workflow end-to-end

### 📝 MEJORAS (Documentación y validación):
7. **Actualizar documentación** - README y summaries
8. **Verificar bounded context** - No imports de core/*

---

## 🎯 ESTADO ACTUAL

**Implementado:**
- ✅ Arquitectura Hexagonal completa
- ✅ Domain Layer (Project → Epic → Story → Task)
- ✅ Application Layer (15+ use cases)
- ✅ Infrastructure Layer (adapters, consumers, mappers)
- ✅ Task Derivation (implementado pero no confiable)
- ✅ Tests unitarios (>90% coverage)
- ✅ Documentación ARCHITECTURE.md actualizada

**Pendiente:**
- 🔴 Corregir Task Derivation (ROLE, parsing, dependencias)
- ⚠️ Integrar RBAC para assignment
- 🧪 Tests de integración y E2E
- 📝 Actualizar README y summaries

**Conclusión:** Planning Service está **funcionalmente completo** pero necesita **correcciones críticas en Task Derivation** para ser confiable en producción.

