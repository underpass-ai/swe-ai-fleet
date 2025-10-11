# Análisis de Casos de Uso - Context Service

## 🎯 Resumen Ejecutivo

El servicio Context es un microservicio gRPC que gestiona el contexto hidratado para agentes AI, implementando Domain-Driven Design (DDD) con arquitectura limpia (Clean Architecture).

**Puerto**: 50054  
**Protocolo**: gRPC + NATS (async)  
**Dependencias**:
- Neo4j (bolt://neo4j:7687) - Grafo de decisiones (write model)
- Redis (redis:6379) - Datos de planificación (read model)
- NATS (nats://nats:4222) - Eventos asíncronos (opcional)

---

## 📡 API gRPC - 4 RPCs Principales

### 1. **GetContext**
Obtiene contexto hidratado para un agente específico.

**Entrada**:
```protobuf
- story_id: string
- role: string (DEV, QA, ARCHITECT, DEVOPS, DATA)
- phase: string (DESIGN, BUILD, TEST, DOCS)
- subtask_id: string (opcional)
- token_budget: int32 (opcional)
```

**Salida**:
```protobuf
- context: string (contexto formateado)
- token_count: int32
- scopes: repeated string (políticas aplicadas)
- version: string (hash de versión)
- blocks: PromptBlocks (estructurado)
```

**Flujo Interno**:
1. `build_prompt_blocks()` coordina todo el proceso
2. `SessionRehydrationUseCase.build()` rehidrata datos desde Neo4j + Redis
3. `PromptScopePolicy.check()` valida scopes de seguridad
4. `_build_system()`, `_build_context()`, `_build_tools()` ensamblan bloques
5. `policy.redact()` aplica redacción de seguridad

---

### 2. **UpdateContext**
Registra cambios en el contexto desde la ejecución de agentes.

**Entrada**:
```protobuf
- story_id: string
- task_id: string
- role: string
- changes: repeated ContextChange
  - operation: CREATE|UPDATE|DELETE
  - entity_type: DECISION|SUBTASK|MILESTONE
  - entity_id: string
  - payload: string (JSON)
  - reason: string
- timestamp: string (ISO 8601)
```

**Salida**:
```protobuf
- version: int32 (nueva versión)
- hash: string (hash de verificación)
- warnings: repeated string
```

**Flujo Interno**:
1. `_process_context_change()` valida cada cambio
2. Genera nueva versión con timestamp
3. Si NATS habilitado → publica evento `context.events.updated`

---

### 3. **RehydrateSession**
Reconstruye contexto completo desde almacenamiento persistente.

**Entrada**:
```protobuf
- case_id: string
- roles: repeated string
- include_timeline: bool
- include_summaries: bool
- timeline_events: int32 (default 50)
- persist_bundle: bool
- ttl_seconds: int32
```

**Salida**:
```protobuf
- case_id: string
- generated_at_ms: int64
- packs: map<string, RoleContextPack> (por rol)
- stats: RehydrationStats
```

**RoleContextPack contiene**:
- Case header (título, descripción, estado)
- Plan header (plan_id, versión, progreso)
- Subtasks del rol
- Decisiones relevantes
- Dependencias entre decisiones
- Subtasks impactadas
- Milestones recientes
- Último resumen
- Sugerencia de token budget

**Flujo Interno**:
1. Lee spec del caso desde Redis
2. Lee grafo de decisiones desde Neo4j
3. Lee plan draft y eventos desde Redis
4. Indexa datos por rol
5. Filtra decisiones relevantes por subtask
6. Construye relaciones de dependencias
7. Identifica subtasks impactados
8. Extrae milestones importantes
9. Sugiere token budget según complejidad
10. Opcionalmente persiste bundle en Redis con TTL

---

### 4. **ValidateScope**
Valida si los scopes proporcionados están permitidos para un rol/fase.

**Entrada**:
```protobuf
- role: string
- phase: string
- provided_scopes: repeated string
```

**Salida**:
```protobuf
- allowed: bool
- missing: repeated string (scopes requeridos faltantes)
- extra: repeated string (scopes no permitidos)
- reason: string (explicación)
```

**Flujo Interno**:
1. `PromptScopePolicy.check()` valida contra políticas
2. Detecta scopes faltantes (missing)
3. Detecta scopes extra no permitidos
4. Genera mensaje de razón legible

---

## 🔄 Casos de Uso Internos (Event Sourcing)

El servicio implementa un patrón de proyección de eventos coordinado por `ProjectorCoordinator`:

### 1. **ProjectCaseUseCase**
- **Evento**: `case.created`
- **Acción**: Crea nodo `Case` en Neo4j
- **Payload**: `{case_id, name?}`

### 2. **ProjectPlanVersionUseCase**
- **Evento**: `plan.versioned`
- **Acción**: Crea nodo `PlanVersion` y relación `HAS_PLAN` con Case
- **Payload**: `{case_id, plan_id, version}`

### 3. **ProjectSubtaskUseCase**
- **Evento**: `subtask.created`
- **Acción**: Crea nodo `Subtask` y relación `HAS_SUBTASK` con Plan
- **Payload**: `{plan_id, sub_id, title?, type?}`

### 4. **UpdateSubtaskStatusUseCase**
- **Evento**: `subtask.status_changed`
- **Acción**: Actualiza estado del `Subtask` en Neo4j
- **Payload**: `{sub_id, status}`

### 5. **ProjectDecisionUseCase**
- **Evento**: `decision.made`
- **Acción**: 
  - Crea nodo `Decision` en Neo4j
  - Si afecta subtask → crea relación `AFFECTS`
- **Payload**: `{node_id, kind?, summary?, sub_id?}`

---

## 🏗️ Arquitectura DDD / Clean Architecture

### Domain Layer (Core)
**Entities**:
- `Case` - Caso de trabajo
- `Decision` - Decisión técnica
- `Subtask` - Unidad de trabajo
- `PlanVersion` - Versión del plan
- `Milestone` - Evento importante

**Value Objects**:
- `CaseHeader` - Metadata del caso
- `PlanHeader` - Metadata del plan
- `DecisionRelation` - Relación entre decisiones
- `PromptBlocks` - Bloques de prompt estructurados
- `RehydrationBundle` - Bundle de rehidratación
- `RoleContextFields` - Campos de contexto por rol

**Domain Services**:
- `PromptScopePolicy` - Políticas de seguridad y scopes
- `ContextSections` - Ensamblador de secciones
- `DecisionRelationList` - Lista de relaciones
- `MilestoneList` - Lista de milestones

### Application Layer (Use Cases)
- `SessionRehydrationUseCase` - Rehidratación de sesión
- `ProjectCaseUseCase` - Proyección de caso
- `ProjectDecisionUseCase` - Proyección de decisión
- `ProjectPlanVersionUseCase` - Proyección de plan
- `ProjectSubtaskUseCase` - Proyección de subtask
- `UpdateSubtaskStatusUseCase` - Actualización de estado
- `ProjectorCoordinator` - Coordinador de proyecciones

### Infrastructure Layer (Adapters)
**Query Side** (Read Model):
- `Neo4jQueryStore` → `GraphQueryPort`
  - `case_plan(case_id)` - Obtiene plan del caso
  - `node_with_neighbors(node_id, depth)` - Obtiene nodo con vecinos
  - `query(cypher, params)` - Query genérico

- `RedisPlanningReadAdapter` → `PlanningReadPort`
  - `get_case_spec(case_id)` - Spec del caso
  - `get_plan_draft(case_id)` - Draft del plan
  - `get_planning_events(case_id, count)` - Eventos de planificación
  - `read_last_summary(case_id)` - Último resumen
  - `save_handoff_bundle(case_id, bundle, ttl)` - Guarda bundle

**Command Side** (Write Model):
- `Neo4jCommandStore` → `GraphCommandPort`
  - `init_constraints(labels)` - Inicializa constraints
  - `upsert_entity(label, id, properties)` - Upsert entidad
  - `upsert_entity_multi(labels, id, properties)` - Upsert multi-label
  - `relate(src_id, rel_type, dst_id, ...)` - Crea relación

### Interface Layer
- **gRPC Server**: `ContextServiceServicer` (server.py)
- **NATS Handler**: `ContextNATSHandler` (nats_handler.py)
  - Subscripciones: `context.update.request`, `context.rehydrate.request`
  - Publicaciones: `context.update.response`, `context.rehydrate.response`, `context.events.updated`

---

## 📊 Flujos de Datos

### Flujo de Lectura (Query)
```
gRPC GetContext
  → build_prompt_blocks()
    → SessionRehydrationUseCase.build()
      → Redis: get_case_spec, get_plan_draft, get_planning_events
      → Neo4j: get_plan_by_case, list_decisions, list_decision_dependencies, list_decision_impacts
    → _narrow_pack_to_subtask() [si subtask_id]
    → PromptScopePolicy.check()
    → _build_system(), _build_context(), _build_tools()
    → policy.redact()
  → GetContextResponse
```

### Flujo de Escritura (Command)
```
gRPC UpdateContext
  → _process_context_change() [validación]
  → _generate_new_version() [timestamp]
  → _generate_context_hash()
  → NATS publish → context.events.updated [async]
  → UpdateContextResponse
```

### Flujo de Proyección de Eventos
```
NATS Event (case.created, plan.versioned, etc.)
  → ProjectorCoordinator.handle()
    → ProjectXxxUseCase.execute()
      → Neo4jCommandStore.upsert_entity()
      → Neo4jCommandStore.relate() [si aplica]
```

---

## 🔐 Seguridad y Políticas

### Scope Policies
- Definen qué información puede ver cada rol en cada fase
- Implementadas en `PromptScopePolicy`
- Configuradas en `config/prompt_scopes.yaml`
- Validación automática en cada `GetContext`

### Redacción
- `policy.redact(role, context)` aplica redacción de seguridad
- Elimina información sensible según rol/fase

### Token Budget
- Calcula automáticamente según:
  - Rol: ARCHITECT = 8192 base, otros = 4096 base
  - +256 tokens por subtask
  - +128 tokens por decisión
  - Máximo bump: 4096 tokens

---

## 🧪 Escenarios de Testing E2E

### Escenario 1: Contexto Básico
1. Seed Neo4j con caso, plan, subtasks, decisiones
2. Seed Redis con spec, draft, eventos
3. GetContext → Verificar bloques completos

### Escenario 2: Contexto Enfocado en Subtask
1. GetContext con subtask_id
2. Verificar filtrado correcto

### Escenario 3: Actualización de Contexto
1. UpdateContext con cambios
2. Verificar versión nueva
3. Verificar evento NATS publicado

### Escenario 4: Rehidratación Multi-Rol
1. RehydrateSession con múltiples roles
2. Verificar packs por rol
3. Verificar filtrado de decisiones relevantes

### Escenario 5: Validación de Scopes
1. ValidateScope con scopes correctos → allowed=true
2. ValidateScope con scopes faltantes → allowed=false, missing
3. ValidateScope con scopes extra → allowed=false, extra

### Escenario 6: Resiliencia
1. Neo4j down → error manejado
2. Redis down → error manejado
3. NATS down → continúa funcionando (degraded mode)

### Escenario 7: Proyección de Eventos
1. Enviar evento via NATS → case.created
2. Verificar nodo en Neo4j
3. Enviar evento → decision.made
4. Verificar nodo y relación AFFECTS

---

## 📝 Observaciones para Tests

### Datos de Test Necesarios
1. **Neo4j**:
   - Nodos: Case, PlanVersion, Subtask, Decision
   - Relaciones: HAS_PLAN, HAS_SUBTASK, AFFECTS, DEPENDS_ON

2. **Redis**:
   - Keys: `swe:case:{id}:spec`, `swe:case:{id}:planning:draft`
   - Stream: `swe:case:{id}:planning:stream`

3. **NATS**:
   - Stream: `CONTEXT`
   - Subjects: `context.>`, `context.events.>`, `context.update.>`, `context.rehydrate.>`

### Configuración de Testcontainers
- Neo4j: puerto 7687, credenciales test
- Redis: puerto 6379
- NATS: puerto 4222, JetStream habilitado
- Context Service: puerto 50054, conectado a todos

### Fixtures Clave
- `neo4j_container` - Neo4j con datos seed
- `redis_container` - Redis con datos seed
- `nats_container` - NATS con JetStream
- `context_container` - Servicio Context
- `grpc_channel` - Canal gRPC al servicio
- `context_stub` - Stub gRPC

---

## 🎯 Conclusión

El servicio Context implementa un sistema completo de gestión de contexto con:

✅ **4 RPCs principales** para obtener, actualizar, rehidratar y validar contexto  
✅ **5 casos de uso de proyección** para sincronizar eventos con grafo  
✅ **CQRS** con Neo4j (write) y Redis (read)  
✅ **Event Sourcing** con NATS  
✅ **DDD/Clean Architecture** con separación clara de capas  
✅ **Seguridad** con políticas de scope y redacción  
✅ **Resiliencia** con NATS opcional y retry logic  

**Para tests e2e**: Necesitamos testcontainers de Neo4j, Redis, NATS y el servicio Context, con datos seed apropiados para cada escenario.

