# RBAC Review - Planning Service Integration

**Fecha:** 2025-11-14
**Contexto:** Revisión de RBAC para entender cómo se integra con Planning Service

---

## 📋 Resumen Ejecutivo

RBAC (Role-Based Access Control) está implementado en múltiples niveles en SWE AI Fleet:

### Niveles de RBAC

1. **RBAC L1 - Tool Access** (✅ Implementado)
   - Controla qué herramientas puede usar cada rol
   - Implementado en `core/agents_and_tools/agents/domain/entities/rbac/`
   - Roles: DEVELOPER, ARCHITECT, QA, PO, DevOps, Data
   - Cada rol tiene `allowed_tools` definido

2. **RBAC L2 - Workflow/Authorization** (✅ Implementado)
   - Controla acciones de workflow (quién puede hacer qué)
   - Implementado en **Workflow Service**
   - Verifica permisos para transiciones de estado, asignaciones, etc.
   - Ubicación: `services/workflow/`
   - Componentes clave:
     - `WorkflowStateMachine` - FSM con validación RBAC
     - `ExecuteWorkflowActionUseCase` - Valida acciones antes de transiciones
     - `AgentWorkCompletedConsumer` - Procesa eventos de agentes
     - `PlanningEventsConsumer` - Inicializa workflows desde Planning Service

3. **RBAC L3 - Data Access Control** (✅ Implementado)
   - Controla visibilidad de datos por rol
   - Implementado en **Context Service**
   - Filtra columnas y filas según el rol del agente/usuario
   - Ubicación: `core/context/application/rbac_context_service.py`
   - Servicios relacionados:
     - `core/context/domain/services/authorization_checker.py` - Authorization checks
     - `core/context/domain/services/column_filter_service.py` - Column-level filtering

---

## 🔍 RBAC en Planning Service

### Responsabilidad de Planning Service

**Planning Service es para PLANIFICAR con el HUMANO (Product Owner).**

**Planning Service es responsable de:**
- ✅ **Crear historias de usuario** (planificación)
- ✅ **Puerta de entrada** para visualizar historias/epics/tareas (PO-UI backend)
- ✅ **Planificación con humano** (human-in-the-loop):
  - Humano valida o rechaza historias terminadas
  - Humano inicia o no un nuevo ciclo de agile
  - Humano decide qué historias van al nuevo ciclo
- ✅ **Gestionar ciclo de vida de historias** (FSM para planificación)
- ✅ **Derivar tareas** desde planes aprobados (para planificación)

**Planning Service NO es responsable de:**
- ❌ Validar permisos RBAC (eso es Workflow Service - RBAC L2)
- ❌ Filtrar datos según rol (eso es Context Service - RBAC L3)
- ❌ Controlar acceso a herramientas (eso es Agent domain - RBAC L1)
- ❌ Ejecutar tareas (eso es Orchestrator/Workflow)
- ❌ Controlar workflow de ejecución (eso es Workflow Service)

### Estado Actual

**Planning Service es Backend para PO-UI:**
- ✅ **Visualización:** PO ve historias/epics/tareas en la UI
- ✅ **Planificación:** PO crea historias, aprueba planes, deriva tareas
- ✅ **Human-in-the-loop:** PO valida/rechaza historias terminadas
- ✅ **Ciclos Agile:** PO decide qué historias van al nuevo ciclo

**Task Assignment (assigned_to):**
- **Estado:** ✅ CORRECTO - Planning Service asigna tareas con `assigned_to` basado en contexto del plan
- **Ubicación:** `services/planning/planning/application/services/task_derivation_result_service.py:143-145`
- **Propósito:** Para planificación y visualización (PO ve qué tareas están asignadas a qué roles)
- **Nota:** La validación RBAC real ocurre cuando la tarea se ejecuta (Workflow Service)

### Flujo Correcto

1. **Planning Service (Planificación con Humano):**
   - PO crea historias → Planning Service
   - PO aprueba planes → Planning Service deriva tareas
   - PO visualiza historias/epics/tareas → Planning Service (PO-UI backend)
   - PO valida/rechaza historias terminadas → Planning Service
   - PO decide qué historias van al nuevo ciclo → Planning Service
   - NO valida RBAC (no es su responsabilidad)

2. **Workflow Service (Ejecución):**
   - Valida permisos RBAC L2 antes de ejecutar tareas
   - Verifica que el agente/rol puede ejecutar la acción
   - Controla transiciones de estado según RBAC

3. **Context Service (Acceso a Datos):**
   - Filtra datos según rol (RBAC L3)
   - Aplica políticas de visibilidad

**Conclusión:** Planning Service es para planificación con el humano (PO). La validación RBAC ocurre en otros servicios (Workflow para L2, Context para L3).

---

## 📊 Roles Disponibles en RBAC

Según `core/agents_and_tools/agents/domain/entities/rbac/role_factory.py`:

- **DEVELOPER:** Implementación de código
- **ARCHITECT:** Diseño técnico, decisiones arquitecturales
- **QA:** Testing, calidad
- **PO:** Product Owner (humano)
- **DevOps:** Infraestructura, deployment
- **Data:** Análisis de datos, esquemas

---

## 🎯 Recomendaciones

### ✅ Planning Service NO necesita cambios de RBAC

**Planning Service está correctamente diseñado:**
- ✅ Backend para PO-UI (visualización de historias/epics/tareas)
- ✅ Planificación con humano (PO valida/rechaza, decide ciclos agile)
- ✅ Crea historias y deriva tareas (para planificación)
- ✅ NO valida RBAC (no es su responsabilidad)
- ✅ NO filtra datos según rol (no es su responsabilidad)
- ✅ NO controla workflow de ejecución (no es su responsabilidad)

**La validación RBAC ocurre en otros servicios:**
- ✅ **Workflow Service** valida RBAC L2 cuando ejecuta tareas
- ✅ **Context Service** aplica RBAC L3 cuando proporciona contexto
- ✅ **Agent domain** valida RBAC L1 cuando usa herramientas

### 📝 Documentación

**Clarificar responsabilidades:**
- **Planning Service:** Planificación con humano (PO crea historias, aprueba planes, visualiza, decide ciclos agile)
- **Workflow Service:** Ejecución de tareas y validación de permisos (RBAC L2)
- **Context Service:** Filtrado de datos según rol (RBAC L3)

---

## 📝 Referencias

- `core/agents_and_tools/agents/domain/entities/rbac/` - RBAC L1 domain (Tool Access)
- `services/workflow/` - RBAC L2 implementation (Workflow/Authorization) ✅ IMPLEMENTADO
  - `domain/services/workflow_state_machine.py` - FSM con validación RBAC
  - `application/usecases/execute_workflow_action_usecase.py` - Valida acciones
  - `infrastructure/consumers/agent_work_completed_consumer.py` - Procesa eventos
- `core/context/application/rbac_context_service.py` - RBAC L3 service (Data Access Control)
- `core/context/domain/services/authorization_checker.py` - Authorization checks (L3)
- `core/context/domain/services/column_filter_service.py` - Column-level filtering (L3)
- `docs/architecture/RBAC_REAL_WORLD_TEAM_MODEL.md` - Documentación completa

---

## ✅ Conclusión

RBAC está implementado en múltiples niveles:
- ✅ **L1 (Tool Access):** Implementado en `core/agents_and_tools/`
- ✅ **L2 (Workflow/Authorization):** Implementado en **Workflow Service** (`services/workflow/`)
- ✅ **L3 (Data Access Control):** Implementado en Context Service

**Planning Service NO necesita conocer RBAC:**

**Planning Service (Planificación con Humano):**
- ✅ Backend para PO-UI (visualización de historias/epics/tareas)
- ✅ PO crea historias, aprueba planes, deriva tareas
- ✅ PO valida/rechaza historias terminadas (human-in-the-loop)
- ✅ PO decide qué historias van al nuevo ciclo de agile
- ✅ Crea tareas con `assigned_to` basándose en contexto del plan (para planificación)
- ✅ NO valida RBAC (no es su responsabilidad)
- ✅ NO filtra datos según rol (no es su responsabilidad)
- ✅ NO controla workflow de ejecución (no es su responsabilidad)

**Validación RBAC ocurre en otros servicios:**
- ✅ **Workflow Service** valida RBAC L2 cuando ejecuta tareas y controla transiciones
- ✅ **Context Service** aplica RBAC L3 cuando filtra datos según rol
- ✅ **Agent domain** valida RBAC L1 cuando usa herramientas

**Arquitectura correcta:** Planning Service es para planificación con el humano (PO). Otros servicios validan RBAC según su responsabilidad (Workflow para ejecución, Context para acceso a datos).

