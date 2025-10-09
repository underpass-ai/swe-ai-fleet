# Orchestrator API - Gap Analysis

## ⚠️ Problem Statement

La API del Orchestrator (`orchestrator.proto`) fue diseñada **ANTES** de entender completamente:
1. Con quién interactúa el servicio
2. Cómo fluyen los datos
3. Qué eventos consume/produce
4. Qué casos de uso reales necesita soportar

## 📊 API Actual vs Necesidades Reales

### API Actual (orchestrator.proto)
```protobuf
service OrchestratorService {
  rpc Deliberate(DeliberateRequest) returns (DeliberateResponse);
  rpc Orchestrate(OrchestrateRequest) returns (OrchestrateResponse);
  rpc GetStatus(GetStatusRequest) returns (GetStatusResponse);
}
```

### Necesidades Reales (según MICROSERVICES_ARCHITECTURE.md)

#### ✅ Lo que está bien:
1. **Deliberate** - OK para peer review síncrono
2. **Orchestrate** - OK para workflow completo
3. **GetStatus** - OK para health checks

#### ❌ Lo que FALTA:

##### 1. **Consumo de Eventos NATS**
```
Planning → NATS agile.events: TRANSITION to BUILD
         ↓
Orchestrator consume? → ❌ NO HAY API PARA ESTO
```

**Falta:**
```protobuf
// Procesar evento de Planning
rpc HandlePlanningEvent(PlanningEventRequest) returns (PlanningEventResponse);

message PlanningEventRequest {
  string event_type = 1;    // "TRANSITION", "CASE_CREATED", etc.
  string case_id = 2;
  string from_state = 3;
  string to_state = 4;
  map<string, string> metadata = 5;
}
```

##### 2. **Derivación de Subtareas**
```
Orchestrator necesita:
- Leer caso/plan de Planning o Context
- Derivar tareas atómicas (DEV, QA, DEVOPS)
- ❌ NO HAY API PARA ESTO
```

**Falta:**
```protobuf
// Derivar subtareas de un caso/plan
rpc DeriveSubtasks(DeriveSubtasksRequest) returns (DeriveSubtasksResponse);

message DeriveSubtasksRequest {
  string case_id = 1;
  string plan_id = 2;
  repeated string roles = 3;  // Roles para los que derivar
}

message DeriveSubtasksResponse {
  repeated AtomicTask tasks = 1;
  string derivation_id = 2;
}

message AtomicTask {
  string task_id = 1;
  string role = 2;
  string description = 3;
  repeated string dependencies = 4;
}
```

##### 3. **Publicación a NATS agent.requests**
```
Orchestrator debe publicar tareas a NATS
❌ Esto no es una API gRPC - es lógica interna usando NATS client
```

**No necesita API gRPC** - pero el servidor necesita NATS client.

##### 4. **Integración con Context Service**
```
Orchestrator necesita:
- Obtener contexto hidratado de Context Service
- ❌ La API actual no muestra esta integración
```

**Falta en request:**
```protobuf
message OrchestrateRequest {
  string task_id = 1;
  string task_description = 2;
  string role = 3;
  TaskConstraints constraints = 4;
  OrchestratorOptions options = 5;
  
  // FALTA:
  string case_id = 6;        // Para obtener contexto
  string story_id = 7;       // Para referencias
  ContextOptions context = 8; // Cómo hidratar contexto
}
```

##### 5. **Registro de Agents**
```
Orchestrator necesita:
- Registrar agents dinámicamente
- Crear councils
- ❌ NO HAY API PARA ESTO
```

**Falta:**
```protobuf
// Registrar agents en councils
rpc RegisterAgent(RegisterAgentRequest) returns (RegisterAgentResponse);
rpc CreateCouncil(CreateCouncilRequest) returns (CreateCouncilResponse);
rpc ListCouncils(ListCouncilsRequest) returns (ListCouncilsResponse);
```

##### 6. **Streaming/Long-Running Operations**
```
Deliberación puede tomar 30+ segundos
❌ La API es unary (request-response simple)
```

**Debería considerar:**
```protobuf
// Stream de updates durante deliberación
rpc StreamDeliberation(DeliberateRequest) returns (stream DeliberationUpdate);

message DeliberationUpdate {
  string status = 1;  // "generating", "reviewing", "scoring"
  int32 progress_percent = 2;
  string current_step = 3;
}
```

## 🔍 Análisis de Flujos

### Flujo Real vs API Actual

#### **Flujo 1: UI pide deliberación**
```
UI → Gateway → Orchestrator.Deliberate()
                    ↓
                Context.GetContext() ← ❌ No está en la API
                    ↓
                Agents deliberan
                    ↓
                Neo4j.save() ← ❌ No está en la API
                    ↓
                Response
```

**Problemas API actual:**
- ✅ Tiene Deliberate RPC
- ❌ No especifica integración con Context
- ❌ No especifica persistencia de resultados
- ❌ No tiene case_id/story_id para contexto

#### **Flujo 2: Planning event → Derivar tareas**
```
NATS agile.events → Orchestrator consume
                         ↓
                    ❌ NO HAY RPC PARA ESTO
                         ↓
                    Deriva subtareas ← ❌ NO HAY RPC
                         ↓
                    NATS agent.requests
```

**Problemas API actual:**
- ❌ No hay RPC para procesar eventos
- ❌ No hay RPC para derivar subtareas
- ❌ Asume que Orchestrator es solo request-response

## 🎯 Arquitectura Real que Necesitamos

### Orchestrator tiene 2 ROLES:

#### **Rol 1: Coordinador Síncrono** (Request-Response)
```
Gateway → Orchestrator.Deliberate/Orchestrate
```
**API actual:** ✅ OK (Deliberate, Orchestrate)

#### **Rol 2: Event Processor Asíncrono** (Event-Driven)
```
NATS agile.events → Orchestrator procesa
                    → Deriva tareas
                    → NATS agent.requests
```
**API actual:** ❌ FALTA COMPLETAMENTE

## 🔧 API Correcta (Basada en Contexto Real)

```protobuf
syntax = "proto3";

package orchestrator.v1;

service OrchestratorService {
  // ========== Coordinación Síncrona (desde Gateway) ==========
  
  // Deliberación peer-to-peer
  rpc Deliberate(DeliberateRequest) returns (DeliberateResponse);
  
  // Orquestación completa
  rpc Orchestrate(OrchestrateRequest) returns (OrchestrateResponse);
  
  // Deliberación con streaming de progreso
  rpc StreamDeliberation(DeliberateRequest) returns (stream DeliberationUpdate);
  
  // ========== Gestión de Agents/Councils ==========
  
  // Registrar agent en un council
  rpc RegisterAgent(RegisterAgentRequest) returns (RegisterAgentResponse);
  
  // Crear council para un role
  rpc CreateCouncil(CreateCouncilRequest) returns (CreateCouncilResponse);
  
  // Listar councils activos
  rpc ListCouncils(ListCouncilsRequest) returns (ListCouncilsResponse);
  
  // ========== Event Processing (desde NATS) ==========
  
  // Procesar evento de Planning
  rpc ProcessPlanningEvent(PlanningEventRequest) returns (PlanningEventResponse);
  
  // Derivar subtareas de un caso/plan
  rpc DeriveSubtasks(DeriveSubtasksRequest) returns (DeriveSubtasksResponse);
  
  // ========== Integración con Context ==========
  
  // Obtener contexto para una tarea (wrapper de Context Service)
  rpc GetTaskContext(GetTaskContextRequest) returns (GetTaskContextResponse);
  
  // ========== Health & Observability ==========
  
  // Status del servicio
  rpc GetStatus(GetStatusRequest) returns (GetStatusResponse);
  
  // Métricas de performance
  rpc GetMetrics(GetMetricsRequest) returns (GetMetricsResponse);
}

// ========== Requests con contexto completo ==========

message OrchestrateRequest {
  string task_id = 1;
  string task_description = 2;
  string role = 3;
  TaskConstraints constraints = 4;
  OrchestratorOptions options = 5;
  
  // AGREGADO: Contexto completo
  string case_id = 6;      // Para obtener contexto de Context Service
  string story_id = 7;     // Para referencias
  string plan_id = 8;      // Para contexto de plan
  ContextOptions context_options = 9; // Cómo hidratar contexto
}

message ContextOptions {
  bool include_timeline = 1;
  bool include_decisions = 2;
  int32 max_events = 3;
}

// ========== Event Processing ==========

message PlanningEventRequest {
  string event_type = 1;    // TRANSITION, CASE_CREATED, etc.
  string case_id = 2;
  string from_state = 3;
  string to_state = 4;
  map<string, string> metadata = 5;
}

message DeriveSubtasksRequest {
  string case_id = 1;
  string plan_id = 2;
  repeated string roles = 3;    // DEV, QA, DEVOPS
  DerivationStrategy strategy = 4;
}

message DerivationStrategy {
  bool parallel_execution = 1;
  repeated string dependencies = 2;
  int32 max_tasks_per_role = 3;
}

// ========== Agent Management ==========

message RegisterAgentRequest {
  string agent_id = 1;
  string role = 2;
  AgentCapabilities capabilities = 3;
  string endpoint = 4;  // Si agent es servicio externo
}

message CreateCouncilRequest {
  string role = 1;
  int32 num_agents = 2;
  CouncilConfig config = 3;
}
```

## 📝 Lecciones Aprendidas

### ❌ Lo que hice mal:
1. Diseñé API basándome en supuestos
2. No analicé interacciones primero
3. No entendí los flujos async (NATS)
4. No consideré Context Service integration
5. No pensé en agent registration

### ✅ Lo que debí hacer:
1. **Leer arquitectura existente** (MICROSERVICES_ARCHITECTURE.md)
2. **Mapear interacciones** (quién llama, quién es llamado)
3. **Entender flujos de datos** (sync/async, eventos)
4. **Documentar use cases** (INTERACTIONS.md)
5. **LUEGO diseñar API** que cubra esos casos

## 🎯 Proceso Correcto para Próximos Microservicios

### Checklist Pre-API Design

- [ ] **1. Análisis de Dominio**
  - [ ] ¿Qué bounded context representa?
  - [ ] ¿Qué responsabilidades tiene?
  - [ ] ¿Qué NO debe hacer?

- [ ] **2. Análisis de Interacciones** [[memory:9734055]]
  - [ ] ¿Quién va a llamarlo? (frontend, backend, ambos)
  - [ ] ¿Cómo lo van a llamar? (REST, gRPC, NATS)
  - [ ] ¿Es público o privado?
  - [ ] ¿Necesita Ingress?

- [ ] **3. Análisis de Dependencias**
  - [ ] ¿Qué servicios necesita llamar?
  - [ ] ¿Qué datos necesita? (Redis, Neo4j, etc.)
  - [ ] ¿Qué eventos consume?
  - [ ] ¿Qué eventos produce?

- [ ] **4. Análisis de Casos de Uso**
  - [ ] Flujo síncrono (request-response)
  - [ ] Flujo asíncrono (event-driven)
  - [ ] Long-running operations
  - [ ] Error scenarios

- [ ] **5. Documentar Todo**
  - [ ] Crear `{SERVICE}_INTERACTIONS.md`
  - [ ] Diagramas de flujo
  - [ ] Casos de uso con ejemplos
  - [ ] Dependencias upstream/downstream

- [ ] **6. SOLO ENTONCES: Diseñar API**
  - [ ] Crear `.proto` basado en casos de uso reales
  - [ ] RPCs que cubran todos los flujos
  - [ ] Mensajes con campos necesarios
  - [ ] Considerar streaming si es long-running

## 🔄 Opciones para Orchestrator

### Opción A: Refactor Completo de API
**Pros:**
- ✅ API correcta desde el inicio
- ✅ Cubre todos los casos de uso

**Cons:**
- ⏳ Requiere tiempo
- ⏳ Hay que regenerar todo
- ⏳ Tests hay que actualizar

### Opción B: API Evolutiva (Iterativa)
**Pros:**
- ✅ Lo actual funciona para casos básicos
- ✅ Agregar RPCs según se necesiten

**Cons:**
- ⚠️ Puede crear deuda técnica
- ⚠️ API fragmentada

### Opción C: API Actual + Worker Interno
**Pros:**
- ✅ API gRPC para llamadas síncronas
- ✅ Worker NATS interno para eventos
- ✅ Separación de concerns

**Cons:**
- ⚠️ Dos patrones diferentes en mismo servicio

## 💡 Recomendación

### Para Orchestrator (ahora):
**Opción C - API Síncrona + Worker NATS Interno**

**Razón:**
1. La API actual funciona para llamadas síncronas (Gateway)
2. Agregar worker NATS interno para eventos async
3. No exponer event processing como gRPC (no tiene sentido)

```python
# En server.py
async def serve_async():
    # gRPC server para llamadas síncronas
    grpc_server = start_grpc_server()
    
    # NATS consumer para eventos async
    nats_client = await nats.connect("nats://nats:4222")
    js = nats_client.jetstream()
    
    # Consumer durable para agile.events
    sub = await js.subscribe(
        "agile.events",
        durable="orchestrator",
        queue="orchestrator-workers"
    )
    
    # Loop de procesamiento async
    async def process_events():
        async for msg in sub.messages:
            event = parse_event(msg.data)
            await handle_planning_event(event)
            await msg.ack()
    
    # Ambos corren en paralelo
    await asyncio.gather(
        grpc_server.wait_for_termination(),
        process_events()
    )
```

### Para Futuros Microservicios:
**Siempre empezar con INTERACTIONS.md ANTES de .proto**

## 📋 Action Items

### Corto Plazo (Orchestrator actual):
- [ ] Agregar NATS client al servidor
- [ ] Implementar consumer para agile.events
- [ ] Agregar case_id/story_id a OrchestrateRequest
- [ ] Integrar con Context Service para obtener contexto
- [ ] Documentar que API es solo para sync calls

### Largo Plazo (Futuros servicios):
- [ ] Seguir checklist pre-API [[memory:9734181]]
- [ ] Crear INTERACTIONS.md primero
- [ ] Revisar con equipo antes de implementar
- [ ] Validar API con casos de uso reales

## 🎓 Lección Principal

> **"La API es la consecuencia del diseño, no el punto de partida."**

**Proceso correcto:**
```
Dominio → Interacciones → Flujos → Casos de Uso → API
```

**Proceso incorrecto (lo que hice):**
```
API → Implementación → "Oops, falta esto"
```

## 📖 Referencias

- [[memory:9734181]] - Context-first API design
- [[memory:9734055]] - Microservices pre-implementation questions
- [MICROSERVICES_ARCHITECTURE.md](../architecture/MICROSERVICES_ARCHITECTURE.md)
- [ORCHESTRATOR_INTERACTIONS.md](./ORCHESTRATOR_INTERACTIONS.md)

---

**Status:** Documentado para aprendizaje futuro. API actual es funcional pero incompleta.

