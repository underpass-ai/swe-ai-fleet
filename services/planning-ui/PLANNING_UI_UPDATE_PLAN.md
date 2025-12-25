# Planning UI - Plan de Actualización

**Fecha**: 2025-12-25
**Estado**: Análisis Completo - Listo para Implementación

## 📋 Resumen Ejecutivo

Planning UI actualmente tiene la funcionalidad básica para **aprobar planes** (`ApproveReviewPlan`), pero **NO muestra**:
- ❌ El `plan_id` generado después de aprobar (aunque el endpoint lo retorna)
- ❌ Las tasks creadas asociadas al plan
- ❌ Información del plan oficial creado
- ❌ Vista consolidada de planes y tasks por story

**Estado Actual**:
- ✅ Endpoint `/api/ceremonies/[id]/approve` retorna `plan_id` correctamente
- ✅ Endpoint `/api/tasks` existe pero **NO soporta filtro por `plan_id`** (solo `story_id` y `status_filter`)
- ✅ UI tiene botones para aprobar, pero no muestra el resultado

**Objetivo**: Actualizar Planning UI para mostrar completamente el flujo de aprobación de planes y generación de tasks.

---

## 🔍 Análisis del Estado Actual

### ✅ Funcionalidades Existentes

1. **Aprobación de Planes** (`/ceremonies/[id].astro`):
   - ✅ Botón "Approve Plan" para cada story con `approval_status=PENDING`
   - ✅ Modal para ingresar `po_notes`, `po_concerns`, `priority_adjustment`
   - ✅ Endpoint `/api/ceremonies/[id]/approve` que llama a `ApproveReviewPlan`
   - ✅ Recarga la página después de aprobar

2. **Visualización de Review Results**:
   - ✅ Muestra `plan_preliminary` (título, descripción, tasks_outline)
   - ✅ Muestra `approval_status` (PENDING, APPROVED, REJECTED)
   - ✅ Muestra feedback de roles (ARCHITECT, QA, DEVOPS)

3. **Gestión de Tasks**:
   - ✅ Página `/tasks/[id]` para ver detalles de una task
   - ✅ Componente `TaskCard.astro` para mostrar tasks
   - ✅ API `/api/tasks` para listar tasks

### ❌ Funcionalidades Faltantes

1. **Después de Aprobar un Plan**:
   - ❌ No se muestra el `plan_id` generado
   - ❌ No se muestran las tasks creadas asociadas al plan
   - ❌ No hay indicador visual de que el plan fue aprobado exitosamente
   - ❌ No se muestra información del plan oficial creado

2. **Visualización de Planes y Tasks**:
   - ❌ No hay vista para ver todos los planes de una story
   - ❌ No hay vista para ver tasks agrupadas por plan
   - ❌ No se muestra la relación plan → tasks en la UI

3. **Información del Plan Oficial**:
   - ❌ No se muestra el plan oficial después de aprobar (solo se muestra `plan_preliminary`)
   - ❌ No hay comparación entre `plan_preliminary` y plan oficial
   - ❌ No se muestran los metadatos del plan (created_at, plan_id)

---

## 🎯 Plan de Implementación

### Fase 1: Mostrar Plan ID y Tasks Después de Aprobar

**Objetivo**: Cuando un PO aprueba un plan, mostrar inmediatamente el `plan_id` generado y las tasks creadas.

#### 1.1 Actualizar Endpoint de Aprobación

**Archivo**: `src/pages/api/ceremonies/[id]/approve.ts`

**Cambios**:
- El endpoint ya retorna `plan_id` en la respuesta
- Verificar que se retorna correctamente
- Asegurar que se retorna información del plan creado

#### 1.2 Actualizar UI para Mostrar Resultado

**Archivo**: `src/pages/ceremonies/[id].astro`

**Cambios**:
- Después de aprobar exitosamente, mostrar un modal o sección con:
  - ✅ Plan ID generado
  - ✅ Mensaje de éxito
  - ✅ Link para ver las tasks del plan
- Actualizar la sección de review results para mostrar:
  - `plan_id` cuando `approval_status=APPROVED`
  - Badge o indicador visual de "Plan Aprobado"
  - Botón para ver tasks del plan

**Código a agregar**:
```astro
{result.approval_status === 'APPROVED' && result.plan_id && (
  <div class="mt-2 bg-green-50 border border-green-200 rounded-md p-3">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm font-medium text-green-800">Plan Aprobado</p>
        <p class="text-xs text-green-600">Plan ID: {result.plan_id}</p>
      </div>
      <a
        href={`/tasks?plan_id=${result.plan_id}`}
        class="text-xs text-green-700 hover:text-green-900 underline"
      >
        Ver Tasks →
      </a>
    </div>
  </div>
)}
```

#### 1.3 Agregar Endpoint para Listar Tasks por Plan

**Archivo**: `src/pages/api/tasks/index.ts` (ya existe, pero **NO soporta `plan_id`**)

**⚠️ PROBLEMA DETECTADO**: El endpoint actual solo soporta `story_id` y `status_filter`, pero **NO soporta `plan_id`**.

**Solución**:
1. **Opción A (Recomendada)**: Filtrar tasks por `story_id` y luego filtrar por `plan_id` en el frontend
   - El endpoint ya retorna todas las tasks de una story
   - El frontend puede filtrar por `plan_id` en el cliente
   - Más simple, no requiere cambios en el backend

2. **Opción B**: Agregar soporte para `plan_id` en el endpoint
   - Requiere verificar si `ListTasksRequest` en protobuf soporta `plan_id`
   - Si no, requeriría actualizar el protobuf y el Planning Service
   - Más complejo, pero más eficiente

**Implementación Inicial (Opción A)**:
- Actualizar endpoint para aceptar `plan_id` como query param
- Si `plan_id` está presente, filtrar tasks en el cliente después de obtenerlas
- Si no está presente, retornar todas las tasks (comportamiento actual)

### Fase 2: Vista de Tasks por Plan

**Objetivo**: Crear una vista dedicada para ver todas las tasks de un plan específico.

#### 2.1 Crear Página de Tasks por Plan

**Archivo**: `src/pages/tasks/index.astro` (ya existe, verificar funcionalidad)

**Cambios**:
- Si existe query param `plan_id`, mostrar solo tasks de ese plan
- Mostrar información del plan (si está disponible)
- Agrupar tasks por tipo o estado
- Mostrar estadísticas (total tasks, completadas, en progreso)

#### 2.2 Agregar Filtro de Plan en Lista de Tasks

**Archivo**: `src/pages/tasks/index.astro`

**Cambios**:
- Agregar dropdown o selector para filtrar por `plan_id`
- Mostrar planes disponibles para la story actual
- Permitir ver todas las tasks o solo las de un plan específico

### Fase 3: Mejorar Visualización de Review Results

**Objetivo**: Mostrar información completa del plan aprobado, incluyendo tasks generadas.

#### 3.1 Expandir Sección de Review Results

**Archivo**: `src/pages/ceremonies/[id].astro`

**Cambios**:
- Cuando `approval_status=APPROVED`:
  - Mostrar `plan_id` prominentemente
  - Mostrar `approved_by` y `approved_at`
  - Mostrar `po_notes` (si está disponible)
  - Mostrar `po_concerns` (si está disponible)
  - Mostrar `priority_adjustment` (si está disponible)
- Agregar sección colapsable "Tasks del Plan" que muestre:
  - Lista de tasks asociadas al plan
  - Estado de cada task
  - Tipo de task
  - Prioridad

#### 3.2 Agregar Endpoint para Obtener Tasks de un Plan

**Archivo**: `src/pages/api/tasks/index.ts`

**Verificar/Crear**:
- Endpoint debe aceptar `plan_id` como query param
- Debe retornar lista de tasks filtradas por `plan_id`
- Debe incluir información completa de cada task

### Fase 4: Vista Consolidada de Planes

**Objetivo**: Crear una vista para ver todos los planes de una story y sus tasks asociadas.

#### 4.1 Crear Página de Planes por Story

**Archivo**: `src/pages/stories/[id]/plans.astro` (nuevo)

**Funcionalidad**:
- Listar todos los planes aprobados para una story
- Mostrar información de cada plan:
  - Plan ID
  - Fecha de aprobación
  - PO que aprobó
  - Número de tasks
  - Estado del plan
- Permitir expandir cada plan para ver sus tasks
- Permitir navegar a vista detallada del plan

#### 4.2 Agregar Link desde Story Detail

**Archivo**: `src/pages/stories/[id].astro`

**Cambios**:
- Agregar sección "Planes Aprobados"
- Mostrar lista de planes con link a `/stories/[id]/plans`
- Mostrar resumen (número de planes, tasks totales)

---

## 📝 Cambios Técnicos Detallados

### 1. Actualizar Tipos TypeScript

**Archivo**: `src/lib/types.ts`

**Agregar**:
```typescript
export interface Plan {
  plan_id: string;
  story_id: string;
  ceremony_id: string;
  title: string;
  description: string;
  approved_by: string;
  approved_at: string;
  created_at: string;
  updated_at: string;
}

export interface StoryReviewResult {
  // ... campos existentes
  plan_id?: string;  // Agregar este campo
  po_notes?: string;
  po_concerns?: string;
  priority_adjustment?: string;
  po_priority_reason?: string;
}
```

### 2. Actualizar Componente de Review Result

**Archivo**: `src/components/ReviewResultCard.astro` (crear nuevo componente)

**Funcionalidad**:
- Mostrar información completa del review result
- Mostrar plan_id cuando está aprobado
- Mostrar tasks del plan (con fetch dinámico)
- Mostrar información de aprobación (po_notes, concerns, etc.)

### 3. Agregar Fetch de Tasks en Frontend

**Archivo**: `src/pages/ceremonies/[id].astro` (script section)

**Agregar función**:
```javascript
async function fetchTasksForPlan(planId) {
  try {
    const response = await fetch(`/api/tasks?plan_id=${planId}`);
    if (response.ok) {
      const data = await response.json();
      return data.tasks || [];
    }
    return [];
  } catch (error) {
    console.error('Error fetching tasks:', error);
    return [];
  }
}
```

### 4. Actualizar API de Tasks

**Archivo**: `src/pages/api/tasks/index.ts`

**Verificar/Cambiar**:
- Aceptar query param `plan_id`
- Filtrar tasks por `plan_id` si está presente
- Retornar tasks con información completa

---

## 🧪 Testing

### Tests a Crear/Actualizar

1. **Test de Aprobación de Plan**:
   - Verificar que se muestra `plan_id` después de aprobar
   - Verificar que se muestran tasks generadas
   - Verificar que se puede navegar a vista de tasks

2. **Test de Filtrado de Tasks por Plan**:
   - Verificar que el endpoint filtra correctamente por `plan_id`
   - Verificar que la UI muestra solo tasks del plan seleccionado

3. **Test de Visualización de Review Results**:
   - Verificar que se muestra información completa del plan aprobado
   - Verificar que se muestran `po_notes`, `po_concerns`, etc.

---

## 📊 Priorización

### Alta Prioridad (Fase 1)
- ✅ Mostrar `plan_id` después de aprobar
- ✅ Mostrar link para ver tasks del plan
- ✅ Actualizar UI para mostrar estado de aprobación

### Media Prioridad (Fase 2-3)
- ✅ Vista de tasks por plan
- ✅ Mejorar visualización de review results
- ✅ Mostrar información completa del plan aprobado

### Baja Prioridad (Fase 4)
- ✅ Vista consolidada de planes por story
- ✅ Estadísticas y resúmenes

---

## 🚀 Próximos Pasos

1. **Implementar Fase 1** (Mostrar Plan ID y Tasks):
   - Actualizar `ceremonies/[id].astro` para mostrar `plan_id`
   - Agregar sección de tasks después de aprobar
   - Verificar que el endpoint de tasks soporta `plan_id`

2. **Verificar Endpoints Existentes**:
   - Verificar que `ListTasks` acepta `plan_id` como filtro
   - Verificar que la respuesta de `ApproveReviewPlan` incluye `plan_id`

3. **Testing**:
   - Probar flujo completo de aprobación
   - Verificar que se muestran tasks correctamente
   - Verificar navegación entre vistas

---

## 📚 Referencias

- **Protobuf Spec**: `specs/fleet/planning/v2/planning.proto`
- **Planning Service**: `services/planning/`
- **E2E Test 06**: `e2e/tests/06-approve-review-plan-and-validate-plan-creation/`

---

## ✅ Checklist de Implementación

### Fase 1: Mostrar Plan ID y Tasks
- [ ] Verificar que `ApproveReviewPlan` retorna `plan_id`
- [ ] Actualizar UI para mostrar `plan_id` después de aprobar
- [ ] Agregar link para ver tasks del plan
- [ ] Verificar que endpoint de tasks soporta `plan_id`
- [ ] Agregar sección de tasks en review result cuando está aprobado

### Fase 2: Vista de Tasks por Plan
- [ ] Crear/actualizar página de tasks con filtro por `plan_id`
- [ ] Agregar información del plan en la vista de tasks
- [ ] Agregar estadísticas de tasks (total, completadas, etc.)

### Fase 3: Mejorar Visualización
- [ ] Mostrar información completa del plan aprobado
- [ ] Mostrar `po_notes`, `po_concerns`, `priority_adjustment`
- [ ] Agregar sección colapsable de tasks en review result

### Fase 4: Vista Consolidada
- [ ] Crear página de planes por story
- [ ] Agregar link desde story detail
- [ ] Agregar estadísticas y resúmenes

---

**Última Actualización**: 2025-12-25
**Autor**: AI Assistant
**Revisión**: Pendiente

