# Análisis de Responsabilidades: Orchestrator Service

**Fecha**: 2 de noviembre, 2025
**Autor**: AI Assistant (Claude Sonnet 4.5)
**Solicitado por**: Tirso García Ibáñez (Software Architect)
**Pregunta**: "¿Estamos sobrepasando las responsabilidades del orchestrator?"

---

## 🎯 Resumen Ejecutivo

**Conclusión**: ⚠️ **SÍ, estamos cerca del límite**.

Orchestrator actualmente tiene **4 responsabilidades claras** y estamos **proponiendo añadir 5 más**, lo que lo convertiría en un **bounded context demasiado grande** (9 responsabilidades).

**Recomendación**: **DIVIDIR** responsabilidades propuestas en nuevos bounded contexts.

---

## 📊 Responsabilidades ACTUALES (Implementadas)

### Bounded Context Actual: `orchestrator`

**Definición** (README.md línea 9):
> "Coordinates multi-agent deliberation and task execution"

### Responsabilidades Implementadas

| # | Responsabilidad | Use Cases | Complejidad | Justificación |
|---|----------------|-----------|-------------|---------------|
| **1** | **Council Management** | CreateCouncil, DeleteCouncil, ListCouncils | Baja | Registry de councils por role ✅ |
| **2** | **Multi-Agent Deliberation** | Deliberate, GetDeliberationResult | Alta | Coordina peer review multi-agente ✅ |
| **3** | **Architect Selection** | Orchestrate (integra deliberation + architect) | Media | Selecciona mejor propuesta ✅ |
| **4** | **Event Processing** | Planning consumer, Agent response consumer | Media | React a eventos NATS ✅ |

**Total actual**: 4 responsabilidades

**Cohesión**: ✅ **ALTA** - Todas relacionadas con "coordinación de agentes"

**Acoplamiento**: ✅ **BAJO** - Usa ports para integraciones

---

### Desglose Detallado de Responsabilidades Actuales

#### 1. Council Management (Registry Pattern)

**Use Cases**:
```python
CreateCouncilUseCase      # Crear council de N agentes para un role
DeleteCouncilUseCase      # Eliminar council
ListCouncilsUseCase       # Listar councils activos
```

**Entidades**:
```python
CouncilRegistry          # Domain entity - Gestiona registry
AgentCollection          # Collection de agentes
RoleCollection           # Collection de roles
```

**Scope**: Registry pattern simple, cohesivo ✅

---

#### 2. Multi-Agent Deliberation (Core Responsibility)

**Use Cases**:
```python
DeliberateUseCase              # Ejecutar deliberación multi-agente
GetDeliberationResultUseCase   # Query resultados
PublishDeliberationEventUseCase # Publicar eventos
RecordAgentResponseUseCase     # Registrar respuestas
CleanupDeliberationsUseCase    # Cleanup después de uso
```

**Flujo**:
```
DeliberateUseCase.execute(council, task, constraints)
  ├─ Council.execute() → Peer deliberation
  ├─ Rank proposals
  ├─ Record stats
  └─ Return DeliberationResult
```

**Scope**: Coordinación multi-agente, **CORE del bounded context** ✅

---

#### 3. Architect Selection (Integration Pattern)

**Use Case**:
```python
# En Orchestrate RPC (server.py:266-313)
async def Orchestrate():
    # 1. Deliberate (multi-agent)
    result = council.execute(task, constraints)

    # 2. Architect selects best (using ArchitectPort)
    best = architect.choose(result.proposals, constraints)

    # 3. Return integrated result
```

**Scope**: Integra deliberation + architect selection ✅

**Justificación**: Architect es un "meta-agente" que evalúa propuestas

---

#### 4. Event Processing (Message Consumer Pattern)

**Consumers**:
```python
OrchestratorPlanningConsumer    # Consume planning.* events
OrchestratorAgentResponseConsumer # Consume agent.response events
OrchestratorContextConsumer     # Consume context.* events
```

**Responsabilidad**:
- Escuchar eventos NATS
- Parsear como domain entities
- Triggear workflows (AutoDispatchService)

**Scope**: Event-driven integration ✅

---

### Análisis de Cohesión Actual

**Pregunta**: ¿Todas las responsabilidades actuales están relacionadas?

**Respuesta**: ✅ **SÍ** - Todas son sobre "coordinar agentes":
1. Council Management → Gestionar equipos de agentes
2. Deliberation → Coordinar deliberación multi-agente
3. Architect Selection → Integrar resultados
4. Event Processing → Reaccionar a eventos para orquestar

**Single Responsibility Principle**: ✅ "Coordinar ejecución multi-agente"

---

## 🚨 Responsabilidades PROPUESTAS (En Gap Analysis)

### Propuestas de los Documentos de Auditoría

| # | Responsabilidad Propuesta | Origen | Complejidad | Cohesión con Orchestrator |
|---|--------------------------|--------|-------------|---------------------------|
| **5** | **Task Derivation** (story→tasks) | PLANNER_VIABILITY_REPORT | Alta | ⚠️ **MEDIA** |
| **6** | **Decision Approval Workflow** | CRITICAL_GAPS_AUDIT | Alta | ⚠️ **BAJA** |
| **7** | **RBAC Decision Authority** | CRITICAL_GAPS_AUDIT | Media | ⚠️ **BAJA** |
| **8** | **Cross-Role Planning** | CRITICAL_GAPS_AUDIT | Alta | ✅ **ALTA** |
| **9** | **Context Rehydration** | CRITICAL_GAPS_AUDIT | Media | ❌ **NINGUNA** |

**Total propuesto**: +5 responsabilidades nuevas

**Total final**: 9 responsabilidades (4 actuales + 5 propuestas)

---

### Análisis Individual de Propuestas

#### Propuesta 5: Task Derivation

**Qué es**:
```python
DeriveSubtasksUseCase
  Input: story_id, plan_id, roles
  Output: list[Subtask] con dependencies

  Lógica:
  1. Fetch story de Context Service
  2. Usar LLM para descomponer story→tasks
  3. Crear grafo de dependencias
  4. Persistir en Neo4j + Valkey
```

**¿Pertenece a orchestrator?**
- ✅ **Usa LLM** (orchestrator coordina agentes)
- ✅ **Coordina derivación** (puede verse como "orchestrate task creation")
- ⚠️ **PERO**: Es planificación, no orquestación de ejecución

**Cohesión**: ⚠️ **MEDIA** - Relacionado pero diferente dominio

**Alternativa**: Bounded context `task-derivation` o `planner`

---

#### Propuesta 6: Decision Approval Workflow

**Qué es**:
```python
ApproveDecisionUseCase
RejectDecisionUseCase
ListPendingDecisionsUseCase
RequestChangesUseCase

Lógica:
1. PO aprueba/rechaza decisión
2. Trigger re-deliberation si rechazada
3. Trigger execution si aprobada
4. Tracking de decisiones
```

**¿Pertenece a orchestrator?**
- ⚠️ **Trigger deliberation**: Sí (orchestrator ya hace deliberate)
- ❌ **Approval workflow**: NO (es governance, no orquestación)
- ❌ **Decision tracking**: NO (es persistencia, no coordinación)

**Cohesión**: ⚠️ **BAJA** - Es workflow de aprobación humana, no coordinación de agentes

**Alternativa**: Bounded context `decision-management` o `governance`

---

#### Propuesta 7: RBAC Decision Authority

**Qué es**:
```python
DecisionAuthorityPort
ScopeValidator
ApprovalPolicyEnforcer

Lógica:
1. Validar que Architect puede rechazar
2. Validar que QA solo opina en spec
3. Enforcement de permisos
```

**¿Pertenece a orchestrator?**
- ❌ **RBAC**: NO (es cross-cutting concern)
- ❌ **Policy enforcement**: NO (es governance)

**Cohesión**: ❌ **NINGUNA** - RBAC es orthogonal a orquestación

**Alternativa**: Bounded context `access-control` o middleware en API Gateway

---

#### Propuesta 8: Cross-Role Planning

**Qué es**:
```python
CrossRolePlanningUseCase

Lógica:
1. Multi-role deliberation (DEV + QA + ARCHITECT juntos)
2. Cross-role critiques
3. Integration por Architect
```

**¿Pertenece a orchestrator?**
- ✅ **Multi-agent coordination**: SÍ (core del orchestrator)
- ✅ **Cross-role deliberation**: SÍ (variante de Deliberate)
- ✅ **Integration**: SÍ (Orchestrate ya lo hace)

**Cohesión**: ✅ **ALTA** - Es orquestación multi-agente

**Conclusión**: ✅ **SÍ PERTENECE** al orchestrator

---

#### Propuesta 9: Context Rehydration

**Qué es**:
```python
NavigateGraph()
RehydrateFromNode()

Lógica:
1. Graph traversal en Neo4j
2. Construir contexto desde cualquier nodo
3. Rehydration para PO
```

**¿Pertenece a orchestrator?**
- ❌ **Graph navigation**: NO (es responsabilidad de Context Service)
- ❌ **Rehydration**: NO (Context Service ya lo hace)

**Cohesión**: ❌ **NINGUNA** - Context Service ownership claro

**Conclusión**: ❌ **NO PERTENECE** al orchestrator (va en Context Service)

---

## 📊 Matriz de Cohesión

| Responsabilidad | Cohesión con "Coordinar Agentes" | ¿Pertenece? | Dónde debería ir |
|----------------|----------------------------------|-------------|------------------|
| **Actuales** |  |  |  |
| 1. Council Management | ✅ Alta | ✅ Sí | orchestrator |
| 2. Multi-Agent Deliberation | ✅ Alta | ✅ Sí | orchestrator |
| 3. Architect Selection | ✅ Alta | ✅ Sí | orchestrator |
| 4. Event Processing | ✅ Alta | ✅ Sí | orchestrator |
| **Propuestas** |  |  |  |
| 5. Task Derivation | ⚠️ Media | ⚠️ Discutible | **planner** o orchestrator |
| 6. Decision Approval | ❌ Baja | ❌ No | **decision-management** |
| 7. RBAC Authority | ❌ Ninguna | ❌ No | **access-control** o API Gateway |
| 8. Cross-Role Planning | ✅ Alta | ✅ Sí | orchestrator |
| 9. Context Rehydration | ❌ Ninguna | ❌ No | **context** (ya existe) |

---

## 🎯 Recomendación: Dividir Responsabilidades

### ✅ Mantener en Orchestrator (Cohesión Alta)

**Responsabilidades core**:
1. Council Management ✅
2. Multi-Agent Deliberation ✅
3. Architect Selection ✅
4. Event Processing ✅
5. **Cross-Role Planning** ← AGREGAR (cohesión alta)

**Total**: 5 responsabilidades (razonable)

---

### ⚠️ Considerar en Orchestrator (Cohesión Media)

**Responsabilidad**:
- **Task Derivation** (DeriveSubtasks)

**Argumentos a favor**:
- Usa LLM (orchestrator coordina agentes)
- Puede verse como "orchestrate task creation"
- Solución Hybrid del Viability Report

**Argumentos en contra**:
- Es planning/decomposition, no execution orchestration
- Crece el scope del bounded context
- Mejor separación con bounded context dedicado

**Recomendación**: ⚠️ **Implementar temporalmente en orchestrator**, **migrar después** si crece

---

### ❌ MOVER a Otros Bounded Contexts (Cohesión Baja/Nula)

#### Decision Approval Workflow → Nuevo BC: `decision-management`

**Responsabilidades**:
- Approval/rejection workflow
- Decision tracking
- PO notification
- Decision State Machine

**Bounded Context Nuevo**:
```
services/decision-management/
├── domain/
│   ├── entities/
│   │   ├── decision.py
│   │   └── decision_state.py
│   └── ports/
│       ├── decision_store_port.py
│       └── notification_port.py
├── application/
│   └── usecases/
│       ├── approve_decision_usecase.py
│       ├── reject_decision_usecase.py
│       └── list_pending_decisions_usecase.py
└── server.py (gRPC)
```

**Justificación**:
- Responsabilidad separada (governance vs execution)
- Reutilizable por otros servicios
- Testeable independientemente

---

#### RBAC Decision Authority → Implementar en: `API Gateway` o `access-control`

**Responsabilidades**:
- RBAC enforcement
- Permission validation
- Scope boundaries (QA no opina en técnica)
- Audit trail de violations

**Opción A: API Gateway** (Middleware pattern)
```
services/api-gateway/
├── middleware/
│   ├── rbac_middleware.py
│   └── scope_validator.py
└── config/
    └── rbac/
        ├── tool_permissions.yaml
        └── decision_authority.yaml
```

**Opción B: Bounded Context Dedicado**
```
services/access-control/
├── domain/
│   ├── entities/
│   │   └── permission_matrix.py
│   └── ports/
│       └── authority_validator_port.py
└── application/
    └── usecases/
        └── validate_permission_usecase.py
```

**Recomendación**: **Opción A (API Gateway)** - RBAC es cross-cutting concern

---

#### Context Rehydration Extended → Ya existe en: `Context Service`

**Responsabilidad**:
- NavigateGraph
- RehydrateFromNode

**NO mover a orchestrator** - Context Service ownership claro ✅

---

## 📊 Comparación: Actual vs Propuesto

### Escenario A: Implementar TODO en Orchestrator (NO RECOMENDADO)

```
Orchestrator (God Object):
├── Council Management               ✅ Core
├── Multi-Agent Deliberation         ✅ Core
├── Architect Selection              ✅ Core
├── Event Processing                 ✅ Core
├── Task Derivation                  ⚠️ Planning domain
├── Decision Approval Workflow       ❌ Governance domain
├── RBAC Decision Authority          ❌ Cross-cutting
├── Cross-Role Planning              ✅ Core
└── Context Rehydration Extended     ❌ Context domain

Responsabilidades: 9
Cohesión: ⚠️ BAJA (5 dominios mezclados)
Complejidad: 🔴 ALTA
Mantenibilidad: 🔴 BAJA
```

**Resultado**: ❌ **God Object** - Violación de Single Responsibility Principle

---

### Escenario B: Distribuir Responsabilidades (RECOMENDADO)

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Service                     │
│  Scope: Coordinación multi-agente (deliberation)           │
├─────────────────────────────────────────────────────────────┤
│  1. Council Management               ✅ Core                │
│  2. Multi-Agent Deliberation         ✅ Core                │
│  3. Architect Selection              ✅ Core                │
│  4. Event Processing                 ✅ Core                │
│  5. Cross-Role Planning              ✅ NUEVO (cohesivo)    │
│  (6. Task Derivation)                ⚠️ TEMPORAL           │
└─────────────────────────────────────────────────────────────┘
   Responsabilidades: 5-6
   Cohesión: ✅ ALTA

┌─────────────────────────────────────────────────────────────┐
│                 Decision Management Service                 │
│  Scope: Governance de decisiones técnicas                   │
├─────────────────────────────────────────────────────────────┤
│  1. Approval/Rejection Workflow      ✅ Core                │
│  2. Decision Tracking                ✅ Core                │
│  3. PO Notification                  ✅ Core                │
│  4. Decision State Machine           ✅ Core                │
└─────────────────────────────────────────────────────────────┘
   Responsabilidades: 4
   Cohesión: ✅ ALTA

┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Service                      │
│  Scope: REST API + RBAC enforcement                         │
├─────────────────────────────────────────────────────────────┤
│  1. REST API Endpoints               ✅ Core                │
│  2. RBAC Middleware                  ✅ Core                │
│  3. gRPC Client Integration          ✅ Core                │
│  4. WebSocket Notifications          ✅ Core                │
└─────────────────────────────────────────────────────────────┘
   Responsabilidades: 4
   Cohesión: ✅ ALTA

┌─────────────────────────────────────────────────────────────┐
│                    Planner Service (NEW)                    │
│  Scope: Task decomposition & planning                       │
├─────────────────────────────────────────────────────────────┤
│  1. Task Derivation (story→tasks)    ✅ Core                │
│  2. Dependency Graph Management      ✅ Core                │
│  3. Effort Estimation                ✅ Core                │
│  4. Priority Assignment              ✅ Core                │
└─────────────────────────────────────────────────────────────┘
   Responsabilidades: 4
   Cohesión: ✅ ALTA
```

**Resultado**: ✅ **4 bounded contexts bien delimitados**

---

## 🔍 Análisis de Single Responsibility

### Pregunta Clave: ¿Qué significa "Orchestrator"?

**Definición RAE - Orquestar**:
> "Organizar o coordinar diversos elementos para lograr un resultado"

**En nuestro contexto**:
> "Coordinar la ejecución de múltiples agentes para completar una tarea"

### ¿Qué SÍ es responsabilidad de Orchestrator?

✅ **Coordinar agents** (deliberation)
✅ **Gestionar councils** (registry)
✅ **Integrar resultados** (architect selection)
✅ **Cross-role planning** (multi-agent coordination)
✅ **Reaccionar a eventos** (trigger deliberations)

### ¿Qué NO es responsabilidad de Orchestrator?

❌ **Planning/Decomposition** (es dominio de "planner")
❌ **Approval workflow** (es dominio de "governance")
❌ **RBAC enforcement** (es cross-cutting concern)
❌ **Context management** (es dominio de "context")
❌ **Decision tracking** (es dominio de "decision-management")

---

## 💡 Propuesta de Refactor Arquitectural

### Distribución Recomendada

```
┌────────────────────────────────────────────────────────────┐
│                  EXECUTION DOMAIN                          │
├────────────────────────────────────────────────────────────┤
│  Orchestrator Service                                      │
│  - Multi-agent deliberation                                │
│  - Council management                                      │
│  - Architect selection                                     │
│  - Cross-role planning                                     │
│  - Event processing                                        │
├────────────────────────────────────────────────────────────┤
│  Ray Executor Service                                      │
│  - Distributed agent execution                             │
│  - Job scheduling                                          │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                  PLANNING DOMAIN                           │
├────────────────────────────────────────────────────────────┤
│  Planning Service (NEW - revivir)                          │
│  - Story FSM management                                    │
│  - Phase transitions                                       │
│  - DoR/DoD validation                                      │
│  - Event publishing (planning.*)                           │
├────────────────────────────────────────────────────────────┤
│  Task Derivation Service (NEW) OR Planner                  │
│  - Story decomposition → tasks                             │
│  - Dependency graph                                        │
│  - Effort estimation                                       │
│  - Priority assignment                                     │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                 GOVERNANCE DOMAIN                          │
├────────────────────────────────────────────────────────────┤
│  Decision Management Service (NEW)                         │
│  - Approval/rejection workflow                             │
│  - Decision tracking                                       │
│  - PO notification                                         │
│  - Decision State Machine                                  │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                 INTEGRATION LAYER                          │
├────────────────────────────────────────────────────────────┤
│  API Gateway (NEW)                                         │
│  - REST API for UI                                         │
│  - RBAC middleware                                         │
│  - gRPC client aggregation                                 │
│  - WebSocket notifications                                 │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                  CONTEXT DOMAIN                            │
├────────────────────────────────────────────────────────────┤
│  Context Service                                           │
│  - Smart context assembly                                  │
│  - Graph navigation (AGREGAR)                              │
│  - Rehydration from any node (AGREGAR)                     │
│  - Story/Task persistence                                  │
└────────────────────────────────────────────────────────────┘
```

---

## 🎯 Decisiones Arquitecturales Necesarias

### Decisión 1: Task Derivation

**Opciones**:

| Opción | Pros | Cons | Cohesión |
|--------|------|------|----------|
| **A. En Orchestrator** (temporal) | Rápido (1 sem) | Orchestrator crece | ⚠️ Media |
| **B. Nuevo servicio Planner** | Separación clara | Más servicios (2-3 sem) | ✅ Alta |
| **C. En Planning Service** | Menos servicios | Planning crece scope | ⚠️ Media |

**Tu decisión**: _____________

**Recomendación**: **Opción B** si tiempo no es crítico, **Opción A** para MVP rápido

---

### Decisión 2: Decision Approval

**Opciones**:

| Opción | Pros | Cons | Cohesión |
|--------|------|------|----------|
| **A. En Orchestrator** | Un servicio menos | God Object | ❌ Baja |
| **B. Nuevo servicio Decision-Management** | Separación clara | Más servicios | ✅ Alta |
| **C. En Context Service** | Menos servicios | Context crece | ❌ Baja |

**Tu decisión**: _____________

**Recomendación**: **Opción B** (bounded context dedicado)

---

### Decisión 3: RBAC

**Opciones**:

| Opción | Pros | Cons | Cohesión |
|--------|------|------|----------|
| **A. En API Gateway** (middleware) | Standard pattern | Solo protege API | ✅ Alta |
| **B. En cada servicio** | Granular | Duplicado, difícil mantener | ❌ Baja |
| **C. Servicio Access-Control** | Centralizado | Otro servicio | ⚠️ Media |

**Tu decisión**: _____________

**Recomendación**: **Opción A** (API Gateway middleware)

---

## 📊 Impacto en Complejidad

### Escenario Actual (Orchestrator Solo)

```
Orchestrator:
  Use Cases: 8 (actuales)
  Lines of Code: ~3,000
  Tests: 112
  Complexity: ⚠️ MEDIA
  Maintainability: ✅ BUENA (hexagonal)
```

### Escenario A: TODO en Orchestrator (NO recomendado)

```
Orchestrator (God Object):
  Use Cases: 17 (+9 nuevos)
  Lines of Code: ~8,000 (+5,000)
  Tests: 250+ (+138)
  Complexity: 🔴 ALTA
  Maintainability: 🔴 BAJA

  Dominios mezclados:
  - Execution (core)
  - Planning (external)
  - Governance (external)
  - Access Control (external)
  - Context (external)
```

**Resultado**: ❌ **Anti-pattern - God Object**

---

### Escenario B: Bounded Contexts Separados (RECOMENDADO)

```
Orchestrator:
  Scope: Multi-agent coordination
  Use Cases: 9 (+1 cross-role planning)
  LOC: ~3,500
  Complexity: ⚠️ MEDIA
  Maintainability: ✅ BUENA

Decision-Management:
  Scope: Approval workflow
  Use Cases: 4
  LOC: ~1,500
  Complexity: ✅ BAJA
  Maintainability: ✅ BUENA

Planner:
  Scope: Task decomposition
  Use Cases: 4
  LOC: ~2,000
  Complexity: ⚠️ MEDIA
  Maintainability: ✅ BUENA

API Gateway:
  Scope: REST + RBAC
  Use Cases: N/A (middleware)
  LOC: ~1,000
  Complexity: ✅ BAJA
  Maintainability: ✅ BUENA
```

**Resultado**: ✅ **Clean Architecture** - Bounded contexts bien delimitados

---

## 🚀 Arquitectura Final Propuesta

### Microservicios Resultantes

| Servicio | Responsabilidad | Tamaño | Prioridad | Estado |
|----------|----------------|--------|-----------|--------|
| **Orchestrator** | Multi-agent deliberation | ~3.5K LOC | ✅ Existe | Mantener + Cross-Role Planning |
| **Planning** | Story FSM management | ~2K LOC | 🔴 P0 | Revivir (Python) |
| **Planner** | Task derivation | ~2K LOC | 🔴 P0 | Crear nuevo |
| **Decision-Management** | Approval workflow | ~1.5K LOC | 🔴 P0 | Crear nuevo |
| **API Gateway** | REST + RBAC | ~1K LOC | 🔴 P0 | Crear nuevo |
| **Context** | Smart context + Navigation | ~4K LOC | ✅ Existe | Extender (NavigateGraph) |
| **Ray Executor** | Distributed execution | ~2K LOC | ✅ Existe | Sin cambios |

**Total servicios**: 7 (4 existen + 3 nuevos)

---

## ⚖️ Trade-offs

### Opción A: Menos Servicios (Orchestrator God Object)

**Pros**:
- ✅ Menos servicios (simplifica deployment)
- ✅ Menos overhead de comunicación gRPC
- ✅ Implementación más rápida (corto plazo)

**Cons**:
- ❌ Violación de Single Responsibility
- ❌ Alta complejidad en un solo servicio
- ❌ Difícil de mantener (largo plazo)
- ❌ Difícil de escalar independientemente
- ❌ Tests más complejos
- ❌ Deploy atómico (cambio en RBAC requiere redeploy de deliberation)

---

### Opción B: Más Servicios (Bounded Contexts Separados)

**Pros**:
- ✅ Single Responsibility por servicio
- ✅ Fácil de mantener
- ✅ Fácil de testear
- ✅ Escalado independiente
- ✅ Deploy independiente
- ✅ Equipos pueden trabajar en paralelo

**Cons**:
- ❌ Más servicios (mayor complejidad operacional)
- ❌ Overhead de comunicación gRPC
- ❌ Más tiempo de implementación inicial
- ❌ Más recursos (CPU/RAM/Pods)

---

## 📋 Recomendación Final

### ✅ OPCIÓN B: Bounded Contexts Separados

**Justificación arquitectural**:

1. **Single Responsibility Principle** - Cada servicio una responsabilidad
2. **Separation of Concerns** - Dominios claramente separados
3. **Scalability** - Servicios escalan independientemente
4. **Maintainability** - Código más fácil de entender y mantener
5. **Team Scalability** - Equipos pueden trabajar en paralelo

### Arquitectura Propuesta (7 Servicios)

```
EXECUTION DOMAIN:
  1. Orchestrator    ← Mantener + Cross-Role Planning
  2. Ray Executor    ← Sin cambios

PLANNING DOMAIN:
  3. Planning        ← Revivir (FSM de stories)
  4. Planner         ← Crear (task derivation)

GOVERNANCE DOMAIN:
  5. Decision-Mgmt   ← Crear (approval workflow)

INTEGRATION LAYER:
  6. API Gateway     ← Crear (REST + RBAC)

CONTEXT DOMAIN:
  7. Context         ← Extender (graph navigation)
```

### Timeline Actualizado

**Sprint 1-2 (4 semanas)**: Foundation
- Planning Service (Python)
- Planner Service (task derivation)
- Decision-Management Service (approval)

**Sprint 3-4 (4 semanas)**: Integration
- API Gateway (REST + RBAC)
- Context Service (extend)
- Orchestrator (cross-role planning)

**Sprint 5 (2 semanas)**: UI & E2E
- Frontend UI complete
- E2E tests
- Integration validation

**TOTAL**: 10 semanas (4 bounded contexts nuevos bien diseñados)

---

## 🎯 Pregunta para el Arquitecto

**¿Prefieres?**

### Opción A: MVP Rápido (Orchestrator God Object)
- ✅ 4 semanas
- ❌ Deuda técnica
- ❌ Refactor futuro necesario

### Opción B: Arquitectura Limpia (7 Servicios)
- ⚠️ 10 semanas
- ✅ Sin deuda técnica
- ✅ Escalable y mantenible

---

**Tu decisión es crítica para el futuro del proyecto.**


