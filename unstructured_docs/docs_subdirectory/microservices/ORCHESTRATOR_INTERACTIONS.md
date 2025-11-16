# Orchestrator Service - Interactions & Architecture

## 🔄 Orchestrator en el Ecosistema

### Diagrama de Interacciones

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   Gateway (REST/SSE)   │ ← Público: gateway.underpassai.com
        │      Port 8080         │
        └────────┬───────────────┘
                 │ gRPC calls
                 │
    ┌────────────┼────────────┬─────────────┐
    │            │            │             │
    ▼            ▼            ▼             ▼
┌────────┐  ┌────────────┐ ┌──────────┐ ┌──────────┐
│Planning│  │ORCHESTRATOR│ │ Context  │ │StoryCoach│
│ :50051 │  │  :50055    │ │  :50054  │ │  :50052  │
└────┬───┘  └─────┬──────┘ └────┬─────┘ └──────────┘
     │            │              │
     │            │              │
     └────────────┼──────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │   NATS Events   │
         │  JetStream      │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
    ┌──────────┐     ┌──────────┐
    │ Workspace│     │ Context  │
    │ Runner   │     │ Service  │
    └────┬─────┘     └──────────┘
         │
         ▼
    ┌──────────┐
    │  K8s Jobs│
    │ (Agents) │
    └──────────┘
```

## 📥 Entrada (Quién llama al Orchestrator)

### 1. **Gateway API (Síncrono)** - REST → gRPC
**Patrón:** Público vía gateway.underpassai.com

```
Usuario → React SPA → Gateway REST API
                       ↓
                    Gateway gRPC Client
                       ↓
                    Orchestrator gRPC Server (ClusterIP interno)
```

**Ejemplo:**
```javascript
// Frontend React
const response = await fetch('https://gateway.underpassai.com/api/orchestrate', {
  method: 'POST',
  body: JSON.stringify({
    task: 'Implement authentication',
    role: 'DEV'
  })
});

// Gateway traduce REST → gRPC
const grpcClient = new OrchestratorClient('orchestrator:50055');
const result = await grpcClient.Orchestrate({
  task_id: uuid(),
  task_description: body.task,
  role: body.role
});
```

### 2. **NATS Events (Asíncrono)** - Event-Driven
**Patrón:** Interno, consume eventos de Planning

```
Planning Service → NATS agile.events
                    ↓
                 Orchestrator (Consumer Durable)
                    ↓
                 Deriva tareas atómicas
                    ↓
                 NATS agent.requests
```

**Ejemplo:**
```json
// Planning publica:
{
  "subject": "agile.events",
  "data": {
    "event_type": "TRANSITION",
    "case_id": "US-123",
    "from": "DRAFT",
    "to": "DESIGN"
  }
}

// Orchestrator consume y reacciona:
// 1. Lee caso de Context Service
// 2. Deriva subtareas (DEV, QA, DEVOPS)
// 3. Publica a agent.requests
```

### 3. **CLI/Scripts (Síncrono)** - Directo
**Patrón:** Privado, acceso interno

```bash
# Desde dentro del cluster
grpcurl -plaintext orchestrator:50055 \
  orchestrator.v1.OrchestratorService/Deliberate
```

## 📤 Salida (A quién llama el Orchestrator)

### 1. **Context Service** (gRPC Síncrono)
**Por qué:** Obtener contexto hidratado para agentes

```python
# Orchestrator llama a Context
context_client = ContextServiceStub(channel)
response = context_client.GetContext(
    story_id=task.story_id,
    role=task.role,
    phase=task.phase
)
# Usa el contexto para configurar agents
```

**Endpoint:** `context:50054` (interno ClusterIP)

### 2. **NATS agent.requests** (Asíncrono)
**Por qué:** Publicar tareas para que Workspace Runner las ejecute

```python
# Orchestrator publica tarea
nats_client.publish('agent.requests', {
    'task_id': 'task-001',
    'role': 'DEV',
    'action': 'implement_feature',
    'context': {...},
    'workspace_spec': {...}
})

# Workspace Runner consume y crea K8s Job
```

### 3. **Memory Layer** (Redis + Neo4j)
**Por qué:** Persistir decisiones y resultados

```python
# Guardar resultado de deliberación
neo4j_client.create_decision({
    'case_id': case_id,
    'decision': winner.content,
    'score': winner.score,
    'alternatives': candidates
})
```

### 4. **Planning Service** (gRPC Síncrono - Opcional)
**Por qué:** Actualizar estado de tareas/subtareas

```python
# Notificar completación
planning_client.UpdateTask(
    task_id=task_id,
    status='COMPLETED',
    result=orchestration_result
)
```

## 🔀 Flujos de Datos

### Flujo 1: Deliberación Síncrona (desde UI)

```
1. UI → POST /api/deliberate (Gateway REST)
   ↓
2. Gateway → Orchestrator.Deliberate (gRPC interno)
   ↓
3. Orchestrator → Context.GetContext (gRPC interno)
   ↓ contexto hidratado
4. Orchestrator → Agents deliberan
   ↓ propuestas + scoring
5. Orchestrator → Architect selecciona mejor
   ↓ resultado
6. Orchestrator → Neo4j (persistir decisión)
   ↓
7. Gateway → Response REST al UI
   ↓
8. UI muestra resultado
```

**Latencia esperada:** 5-30 segundos (depende de LLM)

### Flujo 2: Orquestación Asíncrona (desde Planning Events)

```
1. Planning → NATS agile.events: TRANSITION to BUILD
   ↓
2. Orchestrator (consumer) → recibe evento
   ↓
3. Orchestrator → deriva subtareas
   ├─ DEV: implementar feature
   ├─ QA: crear tests
   └─ DEVOPS: configurar deployment
   ↓
4. Orchestrator → NATS agent.requests (3 mensajes)
   ↓
5. Workspace Runner → consume agent.requests
   ↓
6. Workspace Runner → crea 3 K8s Jobs
   ↓
7. Jobs ejecutan → publican agent.responses
   ↓
8. Context Service → consume responses → actualiza Neo4j
   ↓
9. Context Service → NATS context.updated
   ↓
10. Gateway → SSE → UI actualiza en tiempo real
```

**Duración:** Minutos a horas (depende de complejidad)

## 🌐 Exposición de Servicios

### Servicios Públicos (Ingress)
```yaml
# Dominio público: *.underpassai.com
- gateway.underpassai.com:443      → Gateway (REST API)
- swe-fleet.underpassai.com:443    → UI React SPA
- ray.underpassai.com:443          → Ray Dashboard
```

### Servicios Privados (ClusterIP)
```yaml
# Solo accesibles dentro del cluster
- orchestrator:50055              → Orchestrator (gRPC)
- context:50054                   → Context (gRPC)
- planning:50051                  → Planning (gRPC)
- storycoach:50052               → Story Coach (gRPC)
- workspace:50053                → Workspace Scorer (gRPC)
- nats:4222                      → NATS
- redis:6379                     → Redis
- neo4j:7687                     → Neo4j
```

## ✅ Decisión de Arquitectura: Orchestrator

### **Recomendación: Servicio Privado (Solo ClusterIP)**

**Razón:**
1. ✅ El frontend NO llama directamente a gRPC services
2. ✅ Gateway actúa como BFF (Backend for Frontend)
3. ✅ Gateway traduce REST → gRPC
4. ✅ Orchestrator es backend-to-backend
5. ✅ Reduce superficie de ataque

### Arquitectura Recomendada

```yaml
# 11-orchestrator-service.yaml (actual)
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: swe-ai-fleet
spec:
  type: ClusterIP  # ← Solo interno
  ports:
    - port: 50055
  selector:
    app: orchestrator
```

**Acceso desde:**
- ✅ Gateway Service: `orchestrator.swe-ai-fleet.svc.cluster.local:50055`
- ✅ Context Service: `orchestrator:50055` (mismo namespace)
- ✅ Planning Service: `orchestrator:50055`
- ✅ NATS Consumers: Dentro del cluster

**NO exponer vía Ingress porque:**
- ❌ Frontend no necesita llamar directamente
- ❌ gRPC-Web requiere proxy adicional
- ❌ Aumenta complejidad
- ❌ Superficie de ataque mayor

### Arquitectura Alternativa (Si Frontend Necesita gRPC Directo)

**Solo si en el futuro:**
- Frontend React necesita gRPC streaming
- SSE no es suficiente
- Necesitas bidi streaming en tiempo real

```yaml
# Entonces agregar:
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: orchestrator
  annotations:
    nginx.ingress.kubernetes.io/backend-protocol: "GRPC"
spec:
  rules:
  - host: orchestrator.underpassai.com
    http:
      paths:
      - path: /
        backend:
          service:
            name: orchestrator
            port: 50055
```

## 🎯 Patrón de Acceso Actual

```
Frontend (React)
    ↓ HTTPS/REST
Gateway (gateway.underpassai.com)
    ↓ gRPC/interno
Orchestrator (orchestrator:50055)
    ↓ gRPC/interno
Context (context:50054)
    ↓ gRPC/interno
Otros Services...
```

## 📝 Configuración DNS Interna

```yaml
# Orchestrator es accesible como:
orchestrator:50055                                      # Mismo namespace
orchestrator.swe-ai-fleet:50055                        # Namespace completo
orchestrator.swe-ai-fleet.svc:50055                   # Con .svc
orchestrator.swe-ai-fleet.svc.cluster.local:50055     # FQDN completo
```

## 🔒 Security Considerations

### Privado (ClusterIP) - Recomendado ✅
**Pros:**
- ✅ Menor superficie de ataque
- ✅ No expuesto a internet
- ✅ Más simple (no TLS cert)
- ✅ NetworkPolicy más fácil
- ✅ Mejor para backend-to-backend

**Cons:**
- ⚠️ Gateway es single point of failure
- ⚠️ Gateway debe implementar todas las APIs

### Público (Ingress) - Si es Necesario
**Pros:**
- ✅ Frontend puede llamar directamente
- ✅ Menos latencia (sin Gateway hop)
- ✅ Streaming bidi possible

**Cons:**
- ❌ Expuesto a internet
- ❌ Requiere TLS cert
- ❌ Requiere gRPC-Web proxy (browsers)
- ❌ Mayor superficie de ataque
- ❌ Más complejo NetworkPolicy

## 🎯 Decisión Final

**Para Orchestrator: ClusterIP Privado**

Razones:
1. Gateway ya maneja REST para frontend
2. Orchestrator es coordinación backend
3. Eventos async vía NATS (no necesita Ingress)
4. Context Service también es privado (mismo patrón)
5. Menor complejidad, mayor seguridad

**Servicios que SÍ necesitan Ingress:**
- ✅ Gateway (gateway.underpassai.com) - API REST para frontend
- ✅ UI React (swe-fleet.underpassai.com) - SPA estático
- ✅ Ray Dashboard (ray.underpassai.com) - Monitoreo

**Servicios que NO necesitan Ingress:**
- ✅ Orchestrator - Backend-to-backend
- ✅ Context - Backend-to-backend
- ✅ Planning - Backend-to-backend
- ✅ StoryCoach - Backend-to-backend
- ✅ Workspace - Backend-to-backend

## 📋 Summary

| Servicio | Público | Puerto | Ingress | Razón |
|----------|---------|--------|---------|-------|
| **Gateway** | ✅ Sí | 8080 | gateway.underpassai.com | Frontend REST API |
| **UI** | ✅ Sí | 80 | swe-fleet.underpassai.com | React SPA |
| **Orchestrator** | ❌ No | 50055 | ❌ No | Backend coordination |
| **Context** | ❌ No | 50054 | ❌ No | Backend data |
| **Planning** | ❌ No | 50051 | ❌ No | Backend logic |
| **StoryCoach** | ❌ No | 50052 | ❌ No | Backend scoring |

**Orchestrator Access:**
- Frontend → ❌ No direct (usa Gateway)
- Gateway → ✅ Sí (gRPC interno)
- Other Services → ✅ Sí (gRPC interno)
- NATS → ✅ Sí (events)

