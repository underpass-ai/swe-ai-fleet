# 🎯 Plan: Dashboard de Monitoreo en Tiempo Real

**Fecha**: 16 de Octubre de 2025, 23:31  
**Prioridad**: 🟡 Alta  
**Para**: Próxima sesión (17 de Octubre)

---

## 🎯 OBJETIVO

Crear un **dashboard web en tiempo real** que permita visualizar TODO el flujo del sistema multi-agent:

- Inicialización de councils y agents
- Eventos NATS (quién publica, qué, cuándo)
- Consumers procesando (quién consume, cuándo, qué hace)
- Ray Jobs ejecutándose (estado, logs, duración)
- vLLM requests (inferencias en tiempo real)
- Neo4j (nodos creándose en vivo)
- ValKey (cache updates)
- Decisiones y resultados de agents

---

## 🏗️ ARQUITECTURA DEL DASHBOARD

### Stack Tecnológico Propuesto

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Tailwind)                  │
│  - Dashboard con múltiples panels                               │
│  - WebSocket para updates en tiempo real                        │
│  - Charts para métricas (Recharts o Chart.js)                   │
│  - Timeline view para eventos                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │ WebSocket
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND (FastAPI + Python async)                   │
│  - WebSocket server                                             │
│  - Conecta a: NATS, Neo4j, ValKey, Ray, Kubernetes API          │
│  - Agrega eventos en tiempo real                                │
│  - Expone métricas via Server-Sent Events (SSE)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
    ┌───────┐      ┌─────────┐      ┌──────────┐
    │ NATS  │      │ Neo4j   │      │ Ray API  │
    │Stream │      │ Cypher  │      │Dashboard │
    └───────┘      └─────────┘      └──────────┘
```

---

## 📊 PANELS DEL DASHBOARD

### Panel 1: System Overview (Top)

```
╔═══════════════════════════════════════════════════════════════════╗
║  SWE AI Fleet - Real-Time Monitoring Dashboard                   ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🟢 Context v0.9.0    🟢 Orchestrator v1.0.3   🟢 Ray Cluster     ║
║ 🟢 vLLM (GPU: 95%)   🟢 Neo4j (1 nodo)        🟢 NATS (225 msgs) ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Datos mostrados**:
- Status de cada microservicio (verde/rojo)
- Número de pods por servicio
- Uptime
- Versiones desplegadas
- Uso de recursos (CPU, RAM, GPU)

---

### Panel 2: Councils & Agents (Left)

```
╔═══════════════════════════════════════════════════════════════════╗
║                      COUNCILS & AGENTS                            ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🧑‍💻 DEV (3 agents)       Status: Ready   Model: Qwen3-0.6B      ║
║   ├─ agent-dev-001      ● Idle                                   ║
║   ├─ agent-dev-002      🔄 Deliberating (task-123)               ║
║   └─ agent-dev-003      ✅ Completed (task-122)                  ║
║                                                                   ║
║ 🧪 QA (3 agents)         Status: Ready   Model: Qwen3-0.6B       ║
║   ├─ agent-qa-001       ● Idle                                   ║
║   ├─ agent-qa-002       🔄 Deliberating (task-124)               ║
║   └─ agent-qa-003       ● Idle                                   ║
║                                                                   ║
║ 🏗️  ARCHITECT (3 agents) Status: Ready                           ║
║ ⚙️  DEVOPS (3 agents)     Status: Ready                           ║
║ 📊 DATA (3 agents)        Status: Ready                           ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Datos mostrados**:
- Lista de councils
- Agents por council (con IDs)
- Estado de cada agent (Idle, Deliberating, Completed, Failed)
- Task ID asignado
- Tiempo en estado actual
- Modelo LLM usado

---

### Panel 3: Event Stream (Center)

```
╔═══════════════════════════════════════════════════════════════════╗
║                      NATS EVENT STREAM                            ║
╠═══════════════════════════════════════════════════════════════════╣
║ 23:15:42  📤 planning.plan.approved                              ║
║           Publisher: planning-service                             ║
║           Story: US-HEALTH-CHECK-001                              ║
║           Roles: DEV, DEVOPS                                      ║
║           ├─> Consumers: 2 (context, orchestrator)                ║
║           ├─> context: ✅ Processed in 15ms                       ║
║           └─> orchestrator: ✅ Processed in 23ms                  ║
║                                                                   ║
║ 23:15:43  📤 orchestration.deliberation.started                  ║
║           Publisher: orchestrator-pod-abc123                      ║
║           Task: US-HEALTH-CHECK-001-DEV-deliberation             ║
║           Agents: 3 (agent-dev-001, -002, -003)                  ║
║                                                                   ║
║ 23:15:45  📤 agent.response.completed                            ║
║           Publisher: ray-worker-xyz                               ║
║           Agent: agent-dev-001                                    ║
║           Duration: 2.3s                                          ║
║           Result: "Implement /health endpoint..."                 ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Datos mostrados**:
- Timeline de eventos en tiempo real
- Tipo de evento (con emoji)
- Publisher (quién lo envió)
- Payload resumido
- Consumers que lo procesaron
- Latencia de procesamiento
- Auto-scroll con últimos 50 eventos

---

### Panel 4: Ray Jobs (Right)

```
╔═══════════════════════════════════════════════════════════════════╗
║                        RAY JOBS                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🔄 RUNNING: task-US-001-DEV-deliberation                         ║
║    ├─ Started: 23:15:43 (2s ago)                                 ║
║    ├─ Worker: ray-gpu-worker-abc123                              ║
║    ├─ Agent: agent-dev-002                                       ║
║    ├─ vLLM requests: 1                                           ║
║    └─ Logs: "Analyzing task... calling vLLM..."                  ║
║                                                                   ║
║ ✅ COMPLETED: task-US-001-QA-deliberation                        ║
║    ├─ Duration: 3.2s                                             ║
║    ├─ Result published to NATS ✅                                ║
║    └─ Status: SUCCESS                                            ║
║                                                                   ║
║ ❌ FAILED: task-US-002-DEV-deliberation                          ║
║    ├─ Duration: 1.1s                                             ║
║    ├─ Error: "ConnectionError to vLLM"                           ║
║    └─ Retries: 2/3                                               ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Datos mostrados**:
- Lista de Ray Jobs (running, completed, failed)
- Worker asignado
- Logs en tiempo real
- Estado y duración
- Errores si fallan

---

### Panel 5: vLLM Activity (Bottom Left)

```
╔═══════════════════════════════════════════════════════════════════╗
║                    vLLM SERVER ACTIVITY                           ║
╠═══════════════════════════════════════════════════════════════════╣
║ GPU Usage:  ████████████████████░ 95% (23.4/24 GB)              ║
║ Utilization: ████░░░░░░░░░░░░░░░░ 20%                           ║
║                                                                   ║
║ Recent Requests:                                                  ║
║ 23:15:45  POST /v1/chat/completions                              ║
║           Agent: agent-dev-002                                    ║
║           Tokens: 512 in, 384 out                                 ║
║           Duration: 1.8s                                          ║
║                                                                   ║
║ 23:15:43  POST /v1/chat/completions                              ║
║           Agent: agent-qa-001                                     ║
║           Tokens: 256 in, 512 out                                 ║
║           Duration: 2.1s                                          ║
║                                                                   ║
║ Throughput: 12 requests/min                                       ║
║ Avg latency: 1.9s                                                 ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Datos mostrados**:
- Uso de GPU en tiempo real
- Requests recientes
- Tokens procesados
- Latencia
- Throughput

---

### Panel 6: Neo4j Graph (Bottom Center)

```
╔═══════════════════════════════════════════════════════════════════╗
║                    NEO4J GRAPH (LIVE)                             ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║       (ProjectCase)────APPROVED───>(PlanApproval)                ║
║            │                            │                         ║
║            │                            ↓                         ║
║       TRANSITIONED                (Deliberation)                 ║
║            │                       /    |    \                    ║
║            ↓                      /     |     \                   ║
║    (PhaseTransition)      (AgentProposal) x3                     ║
║                                    │                              ║
║                                    ↓                              ║
║                              (Decision)                           ║
║                                                                   ║
║ Total Nodes: 12    Total Relationships: 8                        ║
║ Last Update: 23:15:45 (2s ago)                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Datos mostrados**:
- Visualización del grafo en tiempo real
- Nodos creándose (animación)
- Relaciones
- Contador de nodos/relaciones
- Última actualización

---

### Panel 7: ValKey Cache (Bottom Right)

```
╔═══════════════════════════════════════════════════════════════════╗
║                      VALKEY CACHE                                 ║
╠═══════════════════════════════════════════════════════════════════╣
║ Keys: 12    Memory: 4.2 MB    Hits: 45    Misses: 3             ║
║                                                                   ║
║ Recent Activity:                                                  ║
║ 23:15:45  SET context:US-001:DEV      TTL: 3600s                ║
║ 23:15:44  GET context:US-001:QA       Hit ✅                    ║
║ 23:15:43  DEL context:US-001:DRAFT    Invalidated               ║
║ 23:15:42  SET planning:US-001         TTL: 1800s                ║
║                                                                   ║
║ Top Keys by Access:                                               ║
║ 1. context:US-001:DEV (15 accesses)                              ║
║ 2. planning:US-001 (8 accesses)                                  ║
║ 3. context:US-001:QA (5 accesses)                                ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Datos mostrados**:
- Estadísticas de cache
- Keys recientes (SET/GET/DEL)
- TTL de cada key
- Hits/Misses
- Top keys por acceso

---

## 🛠️ IMPLEMENTACIÓN

### Fase 1: Backend de Monitoreo (FastAPI)

**Archivo**: `services/monitoring/server.py`

```python
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import asyncio
import nats
from neo4j import GraphDatabase
import redis.asyncio as redis
from kubernetes import client, watch

app = FastAPI()

class MonitoringAggregator:
    """Agrega datos de todas las fuentes."""
    
    def __init__(self):
        self.nats_client = None
        self.neo4j_driver = None
        self.redis_client = None
        self.k8s_client = None
        self.subscribers = []  # WebSocket clients
    
    async def start(self):
        """Conectar a todas las fuentes."""
        # NATS
        self.nats_client = await nats.connect("nats://nats:4222")
        js = self.nats_client.jetstream()
        
        # Subscribe a todos los streams
        await js.subscribe("planning.>", cb=self.on_planning_event)
        await js.subscribe("orchestration.>", cb=self.on_orchestration_event)
        await js.subscribe("agent.>", cb=self.on_agent_event)
        
        # Neo4j
        self.neo4j_driver = GraphDatabase.driver(
            "bolt://neo4j:7687",
            auth=("neo4j", "password")
        )
        
        # ValKey
        self.redis_client = await redis.from_url("redis://valkey:6379")
        
        # Kubernetes API
        self.k8s_client = client.CoreV1Api()
        
        # Start background tasks
        asyncio.create_task(self.monitor_ray_jobs())
        asyncio.create_task(self.monitor_pods())
        asyncio.create_task(self.monitor_vllm())
    
    async def on_planning_event(self, msg):
        """Handle planning events."""
        event = {
            "type": "planning",
            "subject": msg.subject,
            "data": msg.data.decode(),
            "timestamp": time.time()
        }
        await self.broadcast(event)
    
    async def broadcast(self, event):
        """Broadcast to all WebSocket clients."""
        for ws in self.subscribers:
            await ws.send_json(event)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    aggregator.subscribers.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except:
        aggregator.subscribers.remove(websocket)

@app.get("/")
async def dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)
```

---

### Fase 2: Frontend (React)

**Archivo**: `services/monitoring/frontend/src/Dashboard.tsx`

```tsx
import React, { useEffect, useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';

export const Dashboard = () => {
  const { events, councils, rayJobs, vllmActivity } = useWebSocket('ws://localhost:8080/ws');
  
  return (
    <div className="grid grid-cols-3 gap-4 p-4">
      {/* System Overview */}
      <div className="col-span-3">
        <SystemOverview />
      </div>
      
      {/* Left column */}
      <div>
        <CouncilsPanel councils={councils} />
      </div>
      
      {/* Center column */}
      <div>
        <EventStream events={events} />
        <Neo4jGraph />
      </div>
      
      {/* Right column */}
      <div>
        <RayJobsPanel jobs={rayJobs} />
        <VLLMActivity activity={vllmActivity} />
      </div>
      
      {/* Bottom row */}
      <div className="col-span-3">
        <ValKeyPanel />
      </div>
    </div>
  );
};

const EventStream = ({ events }) => {
  return (
    <div className="bg-gray-900 text-green-400 p-4 rounded font-mono text-sm max-h-96 overflow-y-auto">
      {events.map((event, i) => (
        <div key={i} className="mb-2">
          <span className="text-gray-500">{event.timestamp}</span>
          <span className="ml-2">{event.emoji}</span>
          <span className="ml-2 font-bold">{event.subject}</span>
          <div className="ml-8 text-gray-400">{event.summary}</div>
        </div>
      ))}
    </div>
  );
};
```

---

### Fase 3: Data Sources

#### NATS Event Aggregator

```python
# services/monitoring/sources/nats_source.py
class NATSEventSource:
    """Captura todos los eventos de NATS."""
    
    async def start(self, callback):
        nc = await nats.connect("nats://nats:4222")
        js = nc.jetstream()
        
        # Subscribe a TODOS los eventos con wildcard
        await js.subscribe("*.>", cb=lambda msg: callback({
            "source": "NATS",
            "subject": msg.subject,
            "data": msg.data.decode(),
            "metadata": msg.metadata,
            "timestamp": datetime.utcnow().isoformat()
        }))
```

#### Ray Jobs Monitor

```python
# services/monitoring/sources/ray_source.py
class RayJobsSource:
    """Monitorea Ray Jobs via Kubernetes API."""
    
    async def watch_jobs(self, callback):
        from kubernetes import client, watch
        
        api = client.CustomObjectsApi()
        w = watch.Watch()
        
        for event in w.stream(
            api.list_namespaced_custom_object,
            group="ray.io",
            version="v1",
            namespace="ray",
            plural="rayjobs"
        ):
            job = event['object']
            await callback({
                "source": "Ray",
                "event_type": event['type'],  # ADDED, MODIFIED, DELETED
                "job_name": job['metadata']['name'],
                "status": job.get('status', {}).get('jobStatus', 'UNKNOWN'),
                "timestamp": datetime.utcnow().isoformat()
            })
```

#### vLLM Logs Parser

```python
# services/monitoring/sources/vllm_source.py
class VLLMLogSource:
    """Parse vLLM logs para extraer inferencias."""
    
    async def tail_logs(self, callback):
        # Tail logs del pod vLLM
        v1 = client.CoreV1Api()
        
        for line in v1.read_namespaced_pod_log(
            name="vllm-server-xxx",
            namespace="swe-ai-fleet",
            follow=True,
            _preload_content=False
        ).stream():
            
            # Parse línea
            if "POST /v1/chat/completions" in line:
                # Extraer detalles
                await callback({
                    "source": "vLLM",
                    "type": "inference_request",
                    "timestamp": extract_timestamp(line),
                    "client_ip": extract_ip(line)
                })
```

---

## 📋 FEATURES DEL DASHBOARD

### 1. Real-Time Updates ⚡
- WebSocket con latencia < 100ms
- Auto-refresh cada 1s para métricas
- Animaciones suaves en UI

### 2. Historical View 📚
- Slider de tiempo (últimos 5 min, 1h, 24h)
- Replay de eventos
- Exportar a JSON

### 3. Filtering & Search 🔍
- Filtrar por Story ID
- Filtrar por rol (DEV, QA, etc.)
- Filtrar por tipo de evento
- Search en event stream

### 4. Alerts 🚨
- Notificaciones cuando:
  - Ray Job falla
  - Agent no responde en 30s
  - vLLM latencia > 5s
  - Pod crashea

### 5. Drill-Down 🔬
- Click en evento → ver payload completo
- Click en Ray Job → ver logs completos
- Click en agent → ver historial de tareas
- Click en nodo Neo4j → ver propiedades

---

## 🎨 UI/UX

### Design System
- **Framework**: React 18 + TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui
- **Icons**: Lucide React
- **Charts**: Recharts
- **Theme**: Dark mode (estilo terminal)

### Color Scheme
```css
Background: #0f172a (slate-900)
Panels: #1e293b (slate-800)
Text: #e2e8f0 (slate-200)
Accent: #3b82f6 (blue-500)
Success: #10b981 (green-500)
Warning: #f59e0b (amber-500)
Error: #ef4444 (red-500)
```

### Typography
```css
Headings: Inter (sans-serif)
Code/Logs: JetBrains Mono (monospace)
Data: Fira Code (monospace with ligatures)
```

---

## 🚀 DEPLOYMENT

### Docker Compose (Development)

```yaml
version: '3.8'
services:
  monitoring-backend:
    build: services/monitoring
    ports:
      - "8080:8080"
    environment:
      - NATS_URL=nats://nats:4222
      - NEO4J_URI=bolt://neo4j:7687
      - REDIS_URL=redis://valkey:6379
    depends_on:
      - nats
      - neo4j
      - valkey
  
  monitoring-frontend:
    build: services/monitoring/frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_WS_URL=ws://localhost:8080/ws
```

### Kubernetes (Production)

```yaml
# deploy/k8s/13-monitoring-dashboard.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: monitoring-dashboard
  namespace: swe-ai-fleet
spec:
  replicas: 1
  selector:
    matchLabels:
      app: monitoring
  template:
    spec:
      containers:
      - name: backend
        image: registry.underpassai.com/swe-fleet/monitoring:latest
        ports:
        - containerPort: 8080
      - name: frontend
        image: registry.underpassai.com/swe-fleet/monitoring-ui:latest
        ports:
        - containerPort: 3000
---
apiVersion: v1
kind: Service
metadata:
  name: monitoring-dashboard
  namespace: swe-ai-fleet
spec:
  selector:
    app: monitoring
  ports:
  - name: api
    port: 8080
  - name: ui
    port: 3000
  type: LoadBalancer
```

---

## 📊 MÉTRICAS A CAPTURAR

### Por Evento NATS
1. Subject
2. Publisher (pod name, service)
3. Timestamp
4. Payload size
5. Consumers que lo procesaron
6. Latencia de procesamiento por consumer
7. ACK/NAK status

### Por Ray Job
1. Job ID
2. Task description
3. Agent ID
4. Worker asignado
5. Inicio/fin timestamp
6. Duración
7. Estado (PENDING, RUNNING, COMPLETED, FAILED)
8. Logs (últimas 20 líneas)
9. vLLM requests realizados

### Por Agent
1. Agent ID
2. Rol
3. Council
4. Estado actual (Idle, Deliberating, Completed)
5. Task ID asignado
6. Historial de tareas (últimas 10)
7. Tasa de éxito
8. Latencia promedio

### Por vLLM Request
1. Timestamp
2. Client (agent ID o IP)
3. Modelo usado
4. Tokens in/out
5. Duración
6. Status code

### Por Nodo Neo4j
1. Tipo de nodo (label)
2. Propiedades
3. Timestamp creación
4. Relaciones
5. Creado por (service, agent)

---

## 🎯 MVP (Minimum Viable Product)

### Para la Próxima Sesión

**Tiempo estimado**: 4-6 horas

**Scope mínimo**:
1. ✅ Backend FastAPI con WebSocket
2. ✅ Frontend React básico (sin styling)
3. ✅ Panel de Event Stream (NATS)
4. ✅ Panel de Ray Jobs
5. ✅ Panel de Councils/Agents (static)

**Features opcionales** (si hay tiempo):
- Neo4j graph visualization
- vLLM activity panel
- ValKey panel
- Historical view

---

## 📂 ESTRUCTURA DE ARCHIVOS

```
services/monitoring/
├── Dockerfile
├── requirements.txt
├── server.py                    # FastAPI backend
├── sources/
│   ├── __init__.py
│   ├── nats_source.py          # NATS event capture
│   ├── ray_source.py           # Ray Jobs monitoring
│   ├── k8s_source.py           # Kubernetes API
│   ├── vllm_source.py          # vLLM log parsing
│   ├── neo4j_source.py         # Graph changes
│   └── valkey_source.py        # Cache monitoring
├── aggregator.py                # Central event aggregator
└── frontend/
    ├── package.json
    ├── tailwind.config.js
    ├── src/
    │   ├── App.tsx
    │   ├── Dashboard.tsx
    │   ├── components/
    │   │   ├── SystemOverview.tsx
    │   │   ├── CouncilsPanel.tsx
    │   │   ├── EventStream.tsx
    │   │   ├── RayJobsPanel.tsx
    │   │   ├── VLLMActivity.tsx
    │   │   ├── Neo4jGraph.tsx
    │   │   └── ValKeyPanel.tsx
    │   └── hooks/
    │       └── useWebSocket.ts
    └── public/
        └── index.html
```

---

## 🔧 APIs DEL BACKEND

### WebSocket Events

```typescript
// Events que el frontend recibe:

interface Event {
  source: 'NATS' | 'Ray' | 'Neo4j' | 'ValKey' | 'vLLM' | 'K8s';
  type: string;
  timestamp: string;
  data: any;
}

// Ejemplos:
{
  source: "NATS",
  type: "plan.approved",
  timestamp: "2025-10-16T21:15:42Z",
  data: {
    story_id: "US-001",
    roles: ["DEV", "QA"],
    approved_by: "tirso@underpassai.com"
  }
}

{
  source: "Ray",
  type: "job.started",
  timestamp: "2025-10-16T21:15:43Z",
  data: {
    job_id: "task-US-001-DEV",
    agent_id: "agent-dev-002",
    worker: "ray-gpu-worker-abc123"
  }
}
```

### REST Endpoints

```
GET /api/councils            - List all councils
GET /api/agents              - List all agents
GET /api/events?since=5m     - Get historical events
GET /api/ray/jobs            - Get Ray jobs
GET /api/metrics/vllm        - vLLM metrics
GET /api/graph/nodes         - Neo4j nodes
GET /api/cache/keys          - ValKey keys
```

---

## 📝 CHECKLIST PARA MAÑANA

### Backend
- [ ] Crear `services/monitoring/server.py` con FastAPI
- [ ] Implementar WebSocket server
- [ ] Conectar a NATS y suscribirse a todos los eventos
- [ ] Conectar a Kubernetes API para Ray Jobs
- [ ] Implementar broadcast a WebSocket clients
- [ ] Dockerfile y docker-compose.yml

### Frontend
- [ ] Crear React app con TypeScript
- [ ] Implementar `useWebSocket` hook
- [ ] Componente `EventStream` (básico)
- [ ] Componente `RayJobsPanel` (básico)
- [ ] Componente `CouncilsPanel` (estático con datos hardcoded)
- [ ] Tailwind CSS setup

### Deploy
- [ ] Build de imágenes
- [ ] Deploy en Kubernetes
- [ ] Ingress para acceso desde navegador
- [ ] Port-forward para testing local

### Testing
- [ ] Publicar evento NATS → ver en dashboard
- [ ] Crear Ray Job → ver en dashboard
- [ ] Verificar updates en tiempo real

---

## 💡 IDEAS ADICIONALES

### Modo "Debug"
- Ver payloads completos de eventos
- Ver stack traces de errores
- Ver configuración de cada componente

### Modo "Replay"
- Reproducir secuencia de eventos
- Debugging de flujos complejos
- Training/demos

### Integration con Alerting
- Slack notifications
- Email alerts
- Webhooks

### Exportación
- Export to JSON
- Export to CSV
- Generate report PDF

---

**Próxima sesión**: Implementar MVP del dashboard en 4-6 horas  
**Owner**: Tirso  
**Objetivo**: Ver el sistema multi-agent funcionando visualmente en el navegador


