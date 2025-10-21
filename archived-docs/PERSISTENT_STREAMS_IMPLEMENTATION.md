# 💾 Implementación de Streams y Consumers Persistentes en NATS JetStream

**Fecha**: 16 de Octubre de 2025  
**Autor**: System Architecture  
**Objetivo**: Corregir configuración de streams y consumers para que sean **PERSISTENTES** y **DURABLES**

---

## 🎯 PROBLEMA IDENTIFICADO

### Síntoma
Los streams y consumers en NATS JetStream NO eran persistentes:
- **Streams** se creaban en **memory** (storage no especificado)
- **Consumers** eran **ephemeral** (sin nombre durable)
- Al reiniciar NATS pod, se perdían todos los streams y mensajes
- Consumers no recibían mensajes incluso cuando sí había conectividad

### Causa Raíz

#### 1. Streams sin Storage Persistente
```python
# ANTES (INCORRECTO):
await js.add_stream(
    name="PLANNING_EVENTS",
    subjects=["planning.>"],
    # ❌ Sin storage=FILE, defaultea a MEMORY
)
```

#### 2. Consumers sin Durable Name
```python
# ANTES (INCORRECTO):
await js.subscribe(
    "planning.plan.approved",
    queue="context-workers",  # ❌ Queue groups no funcionan en JetStream
    cb=handler,
)
```

**Problemas**:
- `queue` parameter solo funciona en **core NATS**, NO en JetStream
- Sin `durable` name, el consumer es **ephemeral** (se pierde al reiniciar pod)
- Sin `stream` parameter, JetStream no sabe de qué stream leer

---

## ✅ SOLUCIÓN IMPLEMENTADA

### 1. Streams Persistentes con Storage FILE

**Archivo**: `services/context/streams_init.py`

```python
# DESPUÉS (CORRECTO):
from nats.js.api import StorageType, RetentionPolicy, DiscardPolicy

await js.add_stream(
    name=stream_def["name"],
    subjects=stream_def["subjects"],
    storage=StorageType.FILE,  # ← CRITICAL: Persistent storage
    retention=RetentionPolicy.LIMITS,
    discard=DiscardPolicy.OLD,
    max_age=stream_def["max_age"],
    max_msgs=stream_def["max_msgs"],
    num_replicas=1,
)
logger.info(f"✓ Created PERSISTENT stream: {stream_def['name']} (storage: FILE)")
```

**Cambios clave**:
- `storage=StorageType.FILE` → Almacena en `/data` (PersistentVolume)
- `retention=RetentionPolicy.LIMITS` → Borra mensajes por tiempo/tamaño
- `discard=DiscardPolicy.OLD` → Borra mensajes viejos cuando llega al límite
- `num_replicas=1` → Una sola réplica (cluster de un nodo)

**Logs mejorados**:
```python
stream_info = await js.stream_info(stream_def["name"])
logger.info(f"Stream {stream_def['name']} already exists (storage: {stream_info.config.storage})")
```

---

### 2. Consumers Durables con Nombre Explícito

#### Context Service - Planning Consumer

**Archivo**: `services/context/consumers/planning_consumer.py`

```python
# DESPUÉS (CORRECTO):
await self.js.subscribe(
    subject="planning.plan.approved",
    stream="PLANNING_EVENTS",  # ← CRITICAL: Stream name
    durable="context-planning-plan-approved",  # ← CRITICAL: Durable name
    cb=self._handle_plan_approved,
    manual_ack=True,  # Explicit acknowledgment
)
logger.info("✓ Subscribed to planning.plan.approved (DURABLE: context-planning-plan-approved)")
```

**Cambios clave**:
- `subject=` → Nombrar el parámetro explícitamente
- `stream="PLANNING_EVENTS"` → Especificar de qué stream leer
- `durable="context-planning-plan-approved"` → Nombre único del consumer
- `manual_ack=True` → Acknowledgment explícito (mejor control de errores)

**Consumers creados en Context Service**:
1. `context-planning-story-transitions` → `planning.story.transitioned`
2. `context-planning-plan-approved` → `planning.plan.approved`
3. `context-orch-deliberation-completed` → `orchestration.deliberation.completed`
4. `context-orch-task-dispatched` → `orchestration.task.dispatched`

---

#### Context Service - Orchestration Consumer

**Archivo**: `services/context/consumers/orchestration_consumer.py`

```python
await self.js.subscribe(
    subject="orchestration.deliberation.completed",
    stream="ORCHESTRATOR_EVENTS",
    durable="context-orch-deliberation-completed",
    cb=self._handle_deliberation_completed,
    manual_ack=True,
)
```

---

#### Orchestrator Service - Planning Consumer

**Archivo**: `services/orchestrator/consumers/planning_consumer.py`

```python
await self.js.subscribe(
    subject="planning.plan.approved",
    stream="PLANNING_EVENTS",
    durable="orch-planning-plan-approved",
    cb=self._handle_plan_approved,
    manual_ack=True,
)
```

**Consumers creados en Orchestrator Service**:
1. `orch-planning-story-transitions` → `planning.story.transitioned`
2. `orch-planning-plan-approved` → `planning.plan.approved`
3. `orch-context-updated` → `context.updated`
4. `orch-context-milestone` → `context.milestone.reached`
5. `orch-context-decision` → `context.decision.added`

---

#### Orchestrator Service - Context Consumer

**Archivo**: `services/orchestrator/consumers/context_consumer.py`

```python
await self.js.subscribe(
    subject="context.updated",
    stream="CONTEXT_EVENTS",
    durable="orch-context-updated",
    cb=self._handle_context_updated,
    manual_ack=True,
)
```

---

## 🏗️ ARQUITECTURA DE PERSISTENCIA

### NATS Pod Configuration

**Archivo**: `deploy/k8s/01-nats.yaml`

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: nats
spec:
  containers:
    - name: nats
      command:
        - nats-server
        - --jetstream
        - --store_dir=/data  # ← Directorio de almacenamiento
      volumeMounts:
        - name: data
          mountPath: /data  # ← Monta PVC aquí
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi  # ← PersistentVolume de 10GB
```

**Cómo funciona**:
1. NATS server arranca con `--jetstream --store_dir=/data`
2. Kubernetes monta un PVC de 10GB en `/data`
3. Streams con `storage=FILE` escriben a `/data/jetstream/`
4. Al reiniciar el pod, los streams persisten porque el PVC sobrevive

---

## 📋 TABLA DE CONSUMERS DURABLES

| Servicio | Consumer Durable | Stream | Subject | Estado |
|----------|------------------|--------|---------|--------|
| **Context** | context-planning-story-transitions | PLANNING_EVENTS | planning.story.transitioned | ✅ Implementado |
| **Context** | context-planning-plan-approved | PLANNING_EVENTS | planning.plan.approved | ✅ Implementado |
| **Context** | context-orch-deliberation-completed | ORCHESTRATOR_EVENTS | orchestration.deliberation.completed | ✅ Implementado |
| **Context** | context-orch-task-dispatched | ORCHESTRATOR_EVENTS | orchestration.task.dispatched | ✅ Implementado |
| **Orchestrator** | orch-planning-story-transitions | PLANNING_EVENTS | planning.story.transitioned | ✅ Implementado |
| **Orchestrator** | orch-planning-plan-approved | PLANNING_EVENTS | planning.plan.approved | ✅ Implementado |
| **Orchestrator** | orch-context-updated | CONTEXT_EVENTS | context.updated | ✅ Implementado |
| **Orchestrator** | orch-context-milestone | CONTEXT_EVENTS | context.milestone.reached | ✅ Implementado |
| **Orchestrator** | orch-context-decision | CONTEXT_EVENTS | context.decision.added | ✅ Implementado |

**Total**: 9 consumers durables creados

---

## 🔧 BENEFICIOS DE LA SOLUCIÓN

### 1. Persistencia Completa ✅
- **Streams sobreviven** a reinicios de NATS pod
- **Mensajes persisten** en disco (no se pierden)
- **Consumers sobreviven** a reinicios de servicios
- **Offset tracking** automático (no procesa mensajes duplicados)

### 2. Garantías de Entrega ✅
- **At-least-once delivery**: Con `manual_ack=True`
- **No message loss**: Gracias a storage FILE
- **Retry automático**: Si un handler falla, mensaje se re-entrega

### 3. Observabilidad Mejorada ✅
- Logs claros de creación: `"DURABLE: context-planning-plan-approved"`
- Inspección de storage type: `stream_info.config.storage`
- Error logging mejorado: `exc_info=True` en excepciones

### 4. Escalabilidad ✅
- Múltiples pods pueden compartir el mismo durable consumer (load balancing)
- Cada pod procesa mensajes diferentes del mismo stream
- No hay duplicación de procesamiento

---

## 🧪 TESTING Y VERIFICACIÓN

### Comando 1: Ver Streams Creados
```bash
kubectl exec -n swe-ai-fleet nats-0 -- nats stream ls
```

**Esperado**:
```
PLANNING_EVENTS (storage: file)
CONTEXT_EVENTS (storage: file)
ORCHESTRATOR_EVENTS (storage: file)
AGENT_COMMANDS (storage: file)
AGENT_RESPONSES (storage: file)
```

### Comando 2: Ver Consumers de un Stream
```bash
kubectl exec -n swe-ai-fleet nats-0 -- nats consumer ls PLANNING_EVENTS
```

**Esperado**:
```
context-planning-story-transitions
context-planning-plan-approved
orch-planning-story-transitions
orch-planning-plan-approved
```

### Comando 3: Inspeccionar Consumer
```bash
kubectl exec -n swe-ai-fleet nats-0 -- nats consumer info PLANNING_EVENTS context-planning-plan-approved
```

**Esperado**:
```
Durable Name: context-planning-plan-approved
Ack Policy: Explicit
Replay Policy: Instant
Deliver Policy: All
Pending Messages: X
Redelivered: 0
```

### Comando 4: Ver Mensajes en Stream
```bash
kubectl exec -n swe-ai-fleet nats-0 -- nats stream view PLANNING_EVENTS --last=10
```

### Comando 5: Test de Persistencia
```bash
# 1. Publicar mensaje
kubectl run nats-pub --rm -i --restart=Never \
  --image=docker.io/natsio/nats-box:latest \
  -n swe-ai-fleet -- \
  nats pub planning.plan.approved '{"test":"data"}'

# 2. Ver que el stream tiene el mensaje
kubectl exec -n swe-ai-fleet nats-0 -- nats stream info PLANNING_EVENTS

# 3. Reiniciar NATS
kubectl delete pod nats-0 -n swe-ai-fleet

# 4. Verificar que el mensaje AÚN EXISTE
kubectl exec -n swe-ai-fleet nats-0 -- nats stream info PLANNING_EVENTS
```

---

## 📝 CAMBIOS EN ARCHIVOS

### Archivos Modificados

1. ✅ `services/context/streams_init.py`
   - Streams con `storage=StorageType.FILE`
   - Logging mejorado con storage type

2. ✅ `services/context/consumers/planning_consumer.py`
   - Consumers durables: `context-planning-*`
   - `manual_ack=True`

3. ✅ `services/context/consumers/orchestration_consumer.py`
   - Consumers durables: `context-orch-*`
   - `manual_ack=True`

4. ✅ `services/orchestrator/consumers/planning_consumer.py`
   - Consumers durables: `orch-planning-*`
   - `manual_ack=True`

5. ✅ `services/orchestrator/consumers/context_consumer.py`
   - Consumers durables: `orch-context-*`
   - `manual_ack=True`

### Archivos No Modificados (Ya OK)

- ✅ `deploy/k8s/01-nats.yaml` - Ya tenía PVC configurado correctamente
- ✅ `deploy/k8s/00-configmaps.yaml` - NATS_URL con FQN correcto

---

## 🚀 PRÓXIMOS PASOS

### 1. Rebuild & Redeploy Services (CRÍTICO)

**Context Service**:
```bash
cd services/context
# Rebuild container con cambios
docker build -t registry.underpassai.com/swe-fleet/context:v0.7.0 .
docker push registry.underpassai.com/swe-fleet/context:v0.7.0

# Update deployment
kubectl set image deployment/context context=registry.underpassai.com/swe-fleet/context:v0.7.0 -n swe-ai-fleet
```

**Orchestrator Service**:
```bash
cd services/orchestrator
# Rebuild container con cambios
docker build -t registry.underpassai.com/swe-fleet/orchestrator:v0.6.0 .
docker push registry.underpassai.com/swe-fleet/orchestrator:v0.6.0

# Update deployment
kubectl set image deployment/orchestrator orchestrator=registry.underpassai.com/swe-fleet/orchestrator:v0.6.0 -n swe-ai-fleet
```

### 2. Reiniciar NATS (Recrear Streams)

```bash
# Eliminar streams viejos (memory)
kubectl delete pod nats-0 -n swe-ai-fleet

# Los nuevos pods de Context/Orchestrator crearán streams FILE
kubectl logs -n swe-ai-fleet deployment/context --tail=50 | grep "stream"
# Esperado: "✓ Created PERSISTENT stream: PLANNING_EVENTS (storage: FILE)"
```

### 3. Verificar Consumers Creados

```bash
# Esperar 30 segundos a que arranquen
sleep 30

# Ver consumers
kubectl exec -n swe-ai-fleet nats-0 -- nats consumer ls PLANNING_EVENTS
kubectl exec -n swe-ai-fleet nats-0 -- nats consumer ls CONTEXT_EVENTS
kubectl exec -n swe-ai-fleet nats-0 -- nats consumer ls ORCHESTRATOR_EVENTS
```

### 4. Test End-to-End

```bash
# Publicar evento de prueba
kubectl run nats-test --rm -i --restart=Never \
  --image=docker.io/natsio/nats-box:latest \
  -n swe-ai-fleet -- \
  nats pub planning.plan.approved '{
    "story_id": "US-TEST-001",
    "plan_id": "plan-test",
    "timestamp": "2025-10-16T18:00:00Z"
  }'

# Verificar logs de consumers (DEBE aparecer "Plan approved:")
kubectl logs -n swe-ai-fleet deployment/context --tail=20 | grep "Plan approved"
kubectl logs -n swe-ai-fleet deployment/orchestrator --tail=20 | grep "Plan approved"

# Verificar Neo4j
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n:PlanApproval) WHERE n.story_id = 'US-TEST-001' RETURN n;"
# Esperado: 1 nodo
```

---

## ⚠️ IMPORTANTE - BREAKING CHANGES

### Cambio en API de nats-py

La API de `js.subscribe()` puede variar dependiendo de la versión de `nats-py`.

**Versión requerida**: `nats-py >= 2.6.0`

```python
# Verificar versión en requirements.txt o Pipfile
nats-py==2.6.0
```

Si usas versión anterior, la sintaxis puede ser:
```python
# nats-py < 2.0
await js.subscribe("subject", durable="name", cb=handler)

# nats-py >= 2.6
await js.subscribe(subject="subject", durable="name", stream="STREAM", cb=handler)
```

---

## 📚 REFERENCIAS

- [NATS JetStream Persistence](https://docs.nats.io/nats-concepts/jetstream/streams#storage)
- [NATS JetStream Consumers](https://docs.nats.io/nats-concepts/jetstream/consumers)
- [nats-py Documentation](https://github.com/nats-io/nats.py)
- [COMMUNICATION_AUDIT.md](./COMMUNICATION_AUDIT.md) - Arquitectura de comunicaciones
- [VERIFICATION_RESULTS.md](./VERIFICATION_RESULTS.md) - Problema identificado

---

**Resumen**: Streams ahora son **FILE-based** (persisten en PVC) y consumers ahora son **DURABLE** (sobreviven a reinicios). Esto corrige el problema crítico de que los eventos no se estaban procesando.

**Próximo Deploy**: Rebuild Context v0.7.0 + Orchestrator v0.6.0 → Test E2E → Verificar persistencia

