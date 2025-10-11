# Context Service - Análisis de Interacciones

## 🎯 Resumen Ejecutivo

El **Context Service** es un microservicio Python gRPC (puerto 50054) que actúa como el **orquestador de contexto inteligente** para agentes AI. Gestiona la **hidratación de contexto**, **persistencia de decisiones** y **eventos de cambio de contexto**.

**Patrón de Acceso**: Interno (ClusterIP) - No expuesto a internet  
**Protocolo Síncrono**: gRPC  
**Protocolo Asíncrono**: NATS JetStream  
**Almacenamiento**: Neo4j (write model) + Redis (read model)

---

## 📡 Interacciones Síncronas (gRPC)

### 1. **Orchestrator → Context Service**

**Frecuencia**: Alta (cada deliberación/orquestación)  
**Patrón**: Request-Response  
**Latencia esperada**: 50-500ms

#### GetContext
```python
# Orchestrator solicita contexto para un agente
context_client = ContextServiceStub('context:50054')
response = context_client.GetContext(
    story_id='USR-001',
    role='DEV',
    phase='BUILD',
    subtask_id='TASK-001'  # opcional
)
# Usa context para construir prompt del agente
agent_prompt = build_agent_prompt(response.blocks)
```

**Flujo Interno**:
```
1. Orchestrator.Deliberate() → necesita contexto
2. gRPC Call → Context.GetContext()
3. Context Service →
   a. SessionRehydrationUseCase.build()
      - Lee spec/plan desde Redis
      - Lee decisiones/relaciones desde Neo4j
   b. _narrow_pack_to_subtask() [si subtask_id]
   c. PromptScopePolicy.check() [validación seguridad]
   d. _build_system(), _build_context(), _build_tools()
   e. policy.redact() [redacción sensible]
4. Return PromptBlocks → Orchestrator
5. Orchestrator → construye prompt final para agente
```

#### UpdateContext
```python
# Orchestrator registra decisiones del agente
context_client.UpdateContext(
    story_id='USR-001',
    task_id='TASK-001',
    role='DEV',
    changes=[
        ContextChange(
            operation='CREATE',
            entity_type='DECISION',
            entity_id='DEC-001',
            payload='{"title":"Use PostgreSQL","rationale":"..."}',
            reason='Database selection decision'
        )
    ]
)
```

**Flujo Interno**:
```
1. Orchestrator finaliza deliberación → tiene decisiones
2. gRPC Call → Context.UpdateContext()
3. Context Service →
   a. _process_context_change() [validación]
   b. _generate_new_version() [timestamp-based]
   c. _generate_context_hash()
   d. NATS publish → context.events.updated [async]
4. Return version + hash → Orchestrator
```

---

### 2. **Gateway → Context Service** (Futuro)

**Estado**: Planeado, no implementado aún  
**Uso**: UI necesita ver contexto directamente

```javascript
// Gateway traduce REST → gRPC
app.get('/api/context/:story_id', async (req, res) => {
  const response = await contextClient.GetContext({
    storyId: req.params.story_id,
    role: req.query.role,
    phase: req.query.phase
  });
  res.json(response);
});
```

---

### 3. **Planning Service → Context Service** (Futuro)

**Estado**: Planeado  
**Uso**: Planning consulta estado de contexto para validaciones FSM

```go
// Planning verifica si contexto está listo para transición
contextResp, err := contextClient.ValidateScope(ctx, &contextpb.ValidateScopeRequest{
    Role:  "DEV",
    Phase: "BUILD",
    ProvidedScopes: []string{"CASE_HEADER", "PLAN_HEADER"},
})
```

---

## 🔄 Interacciones Asíncronas (NATS JetStream)

### 1. **Context Service → NATS** (Publicador)

#### Subject: `context.events.updated`
**Stream**: `CONTEXT`  
**Retention**: Limits (últimos 1000 eventos, 7 días)  
**Frecuencia**: Cada UpdateContext exitoso

**Payload**:
```json
{
  "event_id": "uuid",
  "case_id": "USR-001",
  "ts": "2025-10-10T12:00:00Z",
  "producer": "context-service",
  "trace_id": "...",
  "event_type": "context.updated",
  "story_id": "USR-001",
  "version": 1234567890,
  "changed": ["task:t-123", "decision:d-45"],
  "snapshot": {
    "version": 42,
    "hash": "abc123def456"
  }
}
```

**Consumidores**:
- **Gateway** → Envía SSE a UI para actualizar Context Viewer en tiempo real
- **Orchestrator** → Detecta cambios para re-planificar si necesario
- **Analytics** → Registra métricas de cambios de contexto

---

### 2. **NATS → Context Service** (Suscriptor)

#### Subject: `context.update.request`
**Stream**: `CONTEXT`  
**Durable Consumer**: `context-update-handler`  
**Patrón**: Async request-response via NATS

**Uso**: Otros servicios pueden solicitar actualizaciones de contexto de forma asíncrona

**Payload Request**:
```json
{
  "event_id": "uuid",
  "case_id": "USR-001",
  "story_id": "USR-001",
  "task_id": "TASK-001",
  "changes": [
    {
      "operation": "CREATE",
      "entity_type": "DECISION",
      "entity_id": "DEC-001",
      "payload": "{...}",
      "reason": "..."
    }
  ]
}
```

**Flujo**:
```
1. Servicio X → NATS publish → context.update.request
2. Context Service consume (durable)
3. Context Service procesa cambios
4. Context Service → NATS publish → context.update.response
5. Servicio X recibe confirmación
```

#### Subject: `context.rehydrate.request`
**Stream**: `CONTEXT`  
**Durable Consumer**: `context-rehydrate-handler`

**Uso**: Rehidratación de sesión en background para múltiples roles

**Payload Request**:
```json
{
  "event_id": "uuid",
  "case_id": "CASE-001",
  "roles": ["DEV", "QA", "ARCHITECT"],
  "include_timeline": true,
  "include_summaries": true
}
```

---

### 3. **Planning → NATS → Context Service** (Event Sourcing)

#### Subject: `agile.events`
**Stream**: `AGILE`  
**Eventos relevantes**:
- `case.created` → Proyecta Case a Neo4j
- `plan.versioned` → Proyecta PlanVersion a Neo4j
- `subtask.created` → Proyecta Subtask a Neo4j
- `subtask.status_changed` → Actualiza estado Subtask
- `decision.made` → Proyecta Decision a Neo4j

**Flujo (Event Sourcing)**:
```
1. Planning Service → cambio de estado FSM
2. Planning → NATS publish → agile.events
3. Context Service consume (ProjectorCoordinator)
4. Context Service → ProjectXxxUseCase.execute()
5. Context Service → Neo4jCommandStore.upsert_entity()
6. Context Service → Neo4jCommandStore.relate() [si aplica]
7. Neo4j actualizado → Graph de decisiones consistente
```

**Ejemplo: decision.made**:
```json
{
  "event_type": "decision.made",
  "case_id": "USR-001",
  "payload": {
    "node_id": "DEC-001",
    "kind": "technical",
    "summary": "Use PostgreSQL for persistence",
    "sub_id": "TASK-001"  // Subtask afectada
  },
  "ts": "2025-10-10T12:00:00Z",
  "actor": "agent:dev-1"
}
```

**Acción Context Service**:
```python
# ProjectDecisionUseCase
1. Crea nodo Decision en Neo4j
2. Si sub_id presente:
   - Crea relación (Decision)-[:AFFECTS]->(Subtask)
3. Event procesado
```

---

### 4. **Context Service → NATS → Gateway → UI** (Real-time Updates)

**Flujo completo para actualizaciones en tiempo real**:
```
1. Agente completa tarea
   ↓
2. Orchestrator → Context.UpdateContext (gRPC)
   ↓
3. Context Service procesa cambios
   ↓
4. Context Service → NATS publish → context.events.updated
   ↓
5. Gateway consume (SSE subscriber durable)
   ↓
6. Gateway → SSE → Browser
   ↓
7. UI React actualiza Context Viewer
```

**Latencia típica**: 100-500ms desde UpdateContext hasta UI

---

## 🗄️ Interacciones con Almacenamiento

### Neo4j (Write Model - CQRS)

**Uso**: Grafo de decisiones, relaciones, proyección de eventos

#### Escritura (via GraphCommandPort)
```python
# ProjectDecisionUseCase
neo4j_command.upsert_entity(
    label='Decision',
    id='DEC-001',
    properties={
        'node_id': 'DEC-001',
        'kind': 'technical',
        'summary': 'Use PostgreSQL',
        'created_at': timestamp
    }
)

neo4j_command.relate(
    src_id='DEC-001',
    rel_type='AFFECTS',
    dst_id='TASK-001',
    src_labels=['Decision'],
    dst_labels=['Subtask']
)
```

#### Lectura (via GraphQueryPort)
```python
# SessionRehydrationUseCase
decisions = neo4j_query.list_decisions(case_id='USR-001')
# → [DecisionNode, DecisionNode, ...]

edges = neo4j_query.list_decision_dependencies(case_id='USR-001')
# → [DecisionEdges, DecisionEdges, ...]

impacts = neo4j_query.list_decision_impacts(case_id='USR-001')
# → [(decision_id, SubtaskNode), ...]
```

**Queries típicos**:
```cypher
# Decisiones de un caso
MATCH (c:Case {id:$case_id})-[:HAS_PLAN]->(p:PlanVersion)
      -[:CONTAINS_DECISION]->(d:Decision)
RETURN d

# Decisiones que afectan subtask
MATCH (d:Decision)-[:AFFECTS]->(s:Subtask {id:$subtask_id})
RETURN d

# Dependencias entre decisiones
MATCH (d1:Decision)-[:DEPENDS_ON]->(d2:Decision)
WHERE d1.case_id = $case_id
RETURN d1.id, d2.id
```

---

### Redis (Read Model - CQRS)

**Uso**: Cache de planificación, specs, eventos, bundles de rehidratación

#### Escritura (via PlanningReadPort)
```python
# Guardar bundle de rehidratación (TTL)
redis_planning.save_handoff_bundle(
    case_id='USR-001',
    bundle={...},  # RehydrationBundle serializado
    ttl_seconds=3600
)
```

#### Lectura
```python
# SessionRehydrationUseCase
spec = redis_planning.get_case_spec('USR-001')
# → CaseSpecDTO

plan_draft = redis_planning.get_plan_draft('USR-001')
# → PlanVersionDTO con subtasks

events = redis_planning.get_planning_events('USR-001', count=50)
# → [PlanningEventDTO, ...]

summary = redis_planning.read_last_summary('USR-001')
# → string | None
```

**Keys típicas**:
```
swe:case:USR-001:spec              → JSON CaseSpec
swe:case:USR-001:planning:draft    → JSON PlanVersion
swe:case:USR-001:planning:stream   → Redis Stream (eventos)
swe:case:USR-001:summaries:last    → String (último resumen)
swe:case:USR-001:handoff:123456    → JSON RehydrationBundle (TTL)
```

---

## 🔀 Diagramas de Flujo Completos

### Flujo 1: GetContext (Síncrono)

```
┌──────────────┐
│ Orchestrator │
└───────┬──────┘
        │ gRPC GetContext(story_id, role, phase)
        ▼
┌────────────────────────────────────────────┐
│         Context Service                     │
│                                            │
│  1. SessionRehydrationUseCase              │
│     ├─ Redis: get_case_spec()              │
│     ├─ Redis: get_plan_draft()             │
│     ├─ Redis: get_planning_events()        │
│     ├─ Neo4j: list_decisions()             │
│     ├─ Neo4j: list_decision_dependencies() │
│     └─ Neo4j: list_decision_impacts()      │
│                                            │
│  2. _narrow_pack_to_subtask() [si aplica]  │
│                                            │
│  3. PromptScopePolicy.check()              │
│     └─ Valida scopes permitidos            │
│                                            │
│  4. _build_system(), _build_context()      │
│     └─ Ensambla bloques de prompt          │
│                                            │
│  5. policy.redact()                        │
│     └─ Redacta info sensible               │
│                                            │
└───────┬────────────────────────────────────┘
        │ GetContextResponse(context, blocks, token_count)
        ▼
┌──────────────┐
│ Orchestrator │
│ → usa para   │
│   construir  │
│   prompt     │
└──────────────┘
```

**Latencia**: 50-500ms (depende de complejidad del grafo)

---

### Flujo 2: UpdateContext + Event (Async)

```
┌──────────────┐
│ Orchestrator │
│ (agente      │
│  finalizó)   │
└───────┬──────┘
        │ gRPC UpdateContext(story_id, changes)
        ▼
┌─────────────────────────────────────────────┐
│         Context Service                      │
│                                             │
│  1. _process_context_change()               │
│     └─ Valida cambios                       │
│                                             │
│  2. _generate_new_version()                 │
│     └─ Timestamp-based versioning           │
│                                             │
│  3. _generate_context_hash()                │
│     └─ SHA256 hash                          │
│                                             │
└────┬────────────────────────────────────┬───┘
     │ UpdateContextResponse              │
     │ (version, hash)                    │
     ▼                                    │
┌──────────────┐                          │ async
│ Orchestrator │                          │ NATS publish
│ (continúa)   │                          │
└──────────────┘                          │
                                          ▼
                                ┌──────────────────┐
                                │   NATS Stream    │
                                │   CONTEXT        │
                                │ subject:         │
                                │ context.events.  │
                                │ updated          │
                                └────────┬─────────┘
                                         │
                        ┌────────────────┼────────────────┐
                        │                │                │
                        ▼                ▼                ▼
                ┌────────────┐  ┌────────────┐  ┌────────────┐
                │  Gateway   │  │Orchestrator│  │ Analytics  │
                │  (SSE→UI)  │  │ (replan?)  │  │ (metrics)  │
                └────────────┘  └────────────┘  └────────────┘
```

**Latencia**:
- UpdateContext gRPC: 10-50ms
- Event propagation: 50-200ms
- Total UI update: 100-500ms

---

### Flujo 3: Event Sourcing (agile.events → Neo4j)

```
┌──────────────┐
│   Planning   │
│   Service    │
│ (FSM change) │
└───────┬──────┘
        │ NATS publish
        │ subject: agile.events
        │ event_type: decision.made
        ▼
┌──────────────────┐
│   NATS Stream    │
│     AGILE        │
└────────┬─────────┘
         │ durable consumer
         │ "context-projector"
         ▼
┌─────────────────────────────────────────────┐
│         Context Service                      │
│                                             │
│  1. ContextNATSHandler                      │
│     └─ _handle_update_request()             │
│                                             │
│  2. ProjectorCoordinator.handle()           │
│     └─ Route event_type → UseCase           │
│                                             │
│  3. ProjectDecisionUseCase.execute()        │
│     ├─ Decision.from_payload()              │
│     ├─ Neo4jCommandStore.upsert_entity()    │
│     │  → CREATE/MERGE Decision node         │
│     └─ Neo4jCommandStore.relate()           │
│        → (Decision)-[:AFFECTS]->(Subtask)   │
│                                             │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
            ┌──────────┐
            │  Neo4j   │
            │  Graph   │
            │ (updated)│
            └──────────┘
```

**Event Types Manejados**:
1. `case.created` → ProjectCaseUseCase
2. `plan.versioned` → ProjectPlanVersionUseCase
3. `subtask.created` → ProjectSubtaskUseCase
4. `subtask.status_changed` → UpdateSubtaskStatusUseCase
5. `decision.made` → ProjectDecisionUseCase

---

### Flujo 4: RehydrateSession (Multi-Role)

```
┌──────────────┐
│ Orchestrator │
│ o Gateway    │
└───────┬──────┘
        │ gRPC RehydrateSession
        │ (case_id, roles=[DEV,QA,ARCHITECT])
        ▼
┌─────────────────────────────────────────────────┐
│         Context Service                          │
│                                                 │
│  SessionRehydrationUseCase.build()              │
│  ├─ 1. get_case_spec() → Redis                  │
│  ├─ 2. get_plan_by_case() → Neo4j               │
│  ├─ 3. list_decisions() → Neo4j                 │
│  ├─ 4. list_decision_dependencies() → Neo4j     │
│  ├─ 5. list_decision_impacts() → Neo4j          │
│  ├─ 6. get_plan_draft() → Redis                 │
│  ├─ 7. get_planning_events() → Redis            │
│  │                                               │
│  ├─ FOR EACH role IN [DEV, QA, ARCHITECT]:      │
│  │   ├─ _index_subtasks_by_role()               │
│  │   ├─ _select_relevant_decisions()            │
│  │   │   (filtrado por impactos en subtasks)    │
│  │   ├─ DecisionRelationList.build()            │
│  │   ├─ _impacts_for_role()                     │
│  │   ├─ MilestoneList.build_from_events()       │
│  │   ├─ read_last_summary() [opcional]          │
│  │   └─ _suggest_token_budget()                 │
│  │                                               │
│  └─ RehydrationBundle(packs={DEV:{...},         │
│                               QA:{...},          │
│                               ARCHITECT:{...}})  │
│                                                 │
│  Opcionalmente: save_handoff_bundle() con TTL   │
│                                                 │
└────────┬────────────────────────────────────────┘
         │ RehydrateSessionResponse
         │ (packs map, stats)
         ▼
┌──────────────┐
│ Orchestrator │
│ → asigna     │
│   contexto   │
│   por rol    │
└──────────────┘
```

**Performance**:
- Caso pequeño (5 decisions, 3 subtasks): ~100ms
- Caso mediano (50 decisions, 20 subtasks): ~500ms
- Caso grande (200+ decisions): ~2s

---

## 📊 Tabla de Interacciones Resumida

| Origen | Destino | Protocolo | Síncrono | Frecuencia | Latencia | Uso |
|--------|---------|-----------|----------|------------|----------|-----|
| **Orchestrator** | Context | gRPC | ✅ | Alta | 50-500ms | GetContext, UpdateContext |
| **Gateway** | Context | gRPC | ✅ | Media | 50-500ms | UI consulta contexto |
| **Planning** | Context | NATS | ❌ | Media | Async | Event sourcing (agile.events) |
| **Context** | NATS | NATS | ❌ | Alta | Async | Publish context.events.updated |
| **Context** | Neo4j | Bolt | ✅ | Alta | 10-100ms | Proyecciones, queries grafo |
| **Context** | Redis | TCP | ✅ | Alta | 1-10ms | Cache specs, eventos, bundles |
| **NATS** | Gateway | NATS | ❌ | Alta | Async | Gateway forward a UI via SSE |

---

## 🔒 Consideraciones de Seguridad

### 1. **Acceso Interno Solo (ClusterIP)**
```yaml
# Context Service NO expuesto a internet
apiVersion: v1
kind: Service
metadata:
  name: context
spec:
  type: ClusterIP  # ← Solo interno
  ports:
    - port: 50054
```

**Por qué**: Context maneja información sensible (decisiones, estrategia)

### 2. **Scope Policy Enforcement**
```python
# En cada GetContext
scope_check = policy.check(phase=phase, role=role, provided_scopes=scopes)
if not scope_check.allowed:
    raise ValueError("Scope violation")
```

**Evita**: Leakage de información entre roles/fases

### 3. **Redacción de Información Sensible**
```python
# Antes de retornar contexto
redacted_context = policy.redact(role, context_text)
```

**Ejemplo**: DEV no ve credenciales de DEVOPS

### 4. **Event Deduplication (NATS)**
```json
{
  "event_id": "uuid",  // ← Unique ID for idempotency
  "case_id": "...",
  "ts": "..."
}
```

**Evita**: Procesamiento duplicado de eventos

---

## 🎯 Testing E2E - Escenarios de Interacción

### Escenario 1: Flujo Completo GetContext
```python
# Test: Orchestrator solicita contexto → Context rehidrata → responde
def test_get_context_full_flow(context_stub, neo4j_seed, redis_seed):
    # 1. Seed data
    neo4j_seed.create_case_with_decisions('USR-001')
    redis_seed.create_spec_and_plan('USR-001')
    
    # 2. GetContext
    response = context_stub.GetContext(
        story_id='USR-001',
        role='DEV',
        phase='BUILD'
    )
    
    # 3. Verify
    assert response.token_count > 0
    assert 'DEV' in response.context
    assert len(response.scopes) > 0
```

### Escenario 2: UpdateContext + NATS Event
```python
# Test: UpdateContext → NATS event publicado → Gateway consume
def test_update_context_publishes_event(context_stub, nats_subscriber):
    # 1. Subscribe to events
    events = []
    nats_subscriber.subscribe('context.events.updated', events.append)
    
    # 2. UpdateContext
    response = context_stub.UpdateContext(
        story_id='USR-001',
        task_id='TASK-001',
        changes=[...]
    )
    
    # 3. Wait for event
    wait_for(lambda: len(events) > 0, timeout=5)
    
    # 4. Verify event
    event = events[0]
    assert event['story_id'] == 'USR-001'
    assert event['version'] == response.version
```

### Escenario 3: Event Sourcing (agile.events → Neo4j)
```python
# Test: Planning publica decision.made → Context proyecta a Neo4j
def test_event_sourcing_decision_made(nats_publisher, neo4j_query):
    # 1. Publish event
    nats_publisher.publish('agile.events', {
        'event_type': 'decision.made',
        'case_id': 'USR-001',
        'payload': {
            'node_id': 'DEC-001',
            'kind': 'technical',
            'summary': 'Use PostgreSQL',
            'sub_id': 'TASK-001'
        }
    })
    
    # 2. Wait for projection
    wait_for(lambda: neo4j_query.node_exists('DEC-001'), timeout=5)
    
    # 3. Verify Neo4j
    decision = neo4j_query.get_node('DEC-001')
    assert decision['kind'] == 'technical'
    
    # 4. Verify relationship
    affects = neo4j_query.get_relationships('DEC-001', 'AFFECTS')
    assert any(r['target'] == 'TASK-001' for r in affects)
```

### Escenario 4: RehydrateSession Multi-Role
```python
# Test: Rehidrata contexto para múltiples roles
def test_rehydrate_session_multi_role(context_stub, neo4j_seed, redis_seed):
    # 1. Seed complex data
    neo4j_seed.create_complex_case('USR-001', decisions=10, subtasks=15)
    redis_seed.create_spec_and_plan('USR-001')
    
    # 2. Rehydrate
    response = context_stub.RehydrateSession(
        case_id='USR-001',
        roles=['DEV', 'QA', 'ARCHITECT'],
        include_timeline=True,
        include_summaries=True
    )
    
    # 3. Verify each role pack
    assert 'DEV' in response.packs
    assert 'QA' in response.packs
    assert 'ARCHITECT' in response.packs
    
    # 4. Verify DEV pack has DEV subtasks only
    dev_pack = response.packs['DEV']
    assert all(st.role == 'DEV' for st in dev_pack.subtasks)
    
    # 5. Verify decisions are relevant to each role
    assert len(dev_pack.decisions) > 0
```

### Escenario 5: Resiliencia - Neo4j Down
```python
# Test: Context Service maneja Neo4j down gracefully
def test_resilience_neo4j_down(context_stub, neo4j_container):
    # 1. Stop Neo4j
    neo4j_container.stop()
    
    # 2. GetContext should fail gracefully
    with pytest.raises(grpc.RpcError) as exc:
        context_stub.GetContext(
            story_id='USR-001',
            role='DEV',
            phase='BUILD'
        )
    
    # 3. Verify error code
    assert exc.value.code() == grpc.StatusCode.UNAVAILABLE
```

---

## 📝 Conclusión

El **Context Service** es el **hub central de información** para el sistema SWE AI Fleet:

### ✅ **Interacciones Síncronas (gRPC)**
- **Orchestrator** lo llama para obtener/actualizar contexto
- **Gateway** (futuro) para consultas UI
- Latencia: 50-500ms típico

### ✅ **Interacciones Asíncronas (NATS)**
- **Publica** `context.events.updated` para notificar cambios
- **Consume** `agile.events` para proyectar eventos a Neo4j
- **Soporta** request-response async vía NATS

### ✅ **Almacenamiento Dual (CQRS)**
- **Neo4j** = Write Model (grafo de decisiones)
- **Redis** = Read Model (cache de planificación)

### ✅ **Seguridad Multi-Capa**
- Scope policies por rol/fase
- Redacción de información sensible
- Solo acceso interno (ClusterIP)

**Para tests E2E**: Necesitamos testcontainers de:
1. **Neo4j** (bolt://neo4j:7687) con seed de grafo
2. **Redis** (redis:6379) con seed de specs/plans
3. **NATS** (nats://nats:4222) con JetStream
4. **Context Service** (context:50054) conectado a todos

