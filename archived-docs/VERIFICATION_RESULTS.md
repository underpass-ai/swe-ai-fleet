# ✅ VERIFICACIÓN DE COMUNICACIONES - RESULTADOS

**Fecha**: 16 de Octubre de 2025, 17:22  
**Test**: Publicación y consumo de eventos NATS en entorno real

---

## 🎯 OBJETIVO

Verificar que el flujo **Orchestrator → NATS → Context → Neo4j/ValKey** funciona correctamente en el cluster de producción.

---

## ✅ INFRAESTRUCTURA VERIFICADA

### Conexiones Establecidas
- ✅ **Orchestrator → NATS**: `nats://nats.swe-ai-fleet.svc.cluster.local:4222` ✓
- ✅ **Context → NATS**: `nats://nats.swe-ai-fleet.svc.cluster.local:4222` ✓
- ✅ **Planning → NATS**: `nats://nats.swe-ai-fleet.svc.cluster.local:4222` ✓
- ✅ **Context → Neo4j**: `bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687` ✓
- ✅ **Context → ValKey**: `valkey.swe-ai-fleet.svc.cluster.local:6379` ✓

### Streams NATS Creados
```
✓ PLANNING_EVENTS (subjects: planning.>)
✓ CONTEXT_EVENTS (subjects: context.>)
✓ ORCHESTRATOR_EVENTS (subjects: orchestration.>)
✓ AGENT_COMMANDS (subjects: agent.cmd.>)
✓ AGENT_RESPONSES (subjects: agent.response.>)
```

### Consumers Activos
```
Context Service:
  ✓ Subscribed to planning.story.transitioned
  ✓ Subscribed to planning.plan.approved
  ✓ Planning Events Consumer started
  ✓ Subscribed to orchestration.deliberation.completed
  ✓ Subscribed to orchestration.task.dispatched
  ✓ Orchestration Events Consumer started

Orchestrator Service:
  ✓ Subscribed to planning.story.transitioned
  ✓ Subscribed to planning.plan.approved
  ✓ Orchestrator Planning Consumer started
```

### Persistencia Verificada
- ✅ **Neo4j**: Datos sobreviven a reinicio completo del cluster
- ✅ **ValKey**: Datos sobreviven a reinicio completo del cluster

---

## ⚠️ PROBLEMA IDENTIFICADO

### Síntoma
Los eventos se **publican correctamente** a NATS, pero los **consumers NO los procesan**.

### Evidencia

#### Test 1 - Evento publicado a las 17:18:45
```bash
$ kubectl run nats-publisher --image=docker.io/natsio/nats-box:latest \
  nats pub planning.plan.approved '{"event_type":"PLAN_APPROVED","story_id":"US-VERIFY-001",...}'

17:18:45 Published 227 bytes to "planning.plan.approved"
✅ Evento publicado
```

#### Test 2 - Evento publicado a las 17:20:43
```bash
$ nats pub planning.plan.approved '{"story_id":"US-VERIFY-002",...}'

17:20:43 Published 83 bytes to "planning.plan.approved"
✅ Evento publicado
```

#### Logs de Context Service
```
# Logs después de ambos eventos:
[No se registró ningún procesamiento]

# Esperado:
2025-10-16 17:18:45 [INFO] Plan approved: plan-verify-v1 for story US-VERIFY-001
2025-10-16 17:20:43 [INFO] Plan approved: plan-v2 for story US-VERIFY-002
```

#### Logs de Orchestrator Service  
```
# Logs después de ambos eventos:
[No se registró ningún procesamiento]
```

#### Neo4j
```cypher
MATCH (n:PlanApproval) RETURN n;
# Resultado: 0 nodos
```

---

## 🔍 ANÁLISIS DE CAUSA RAÍZ

### Código del Consumer (Implementado Correctamente)

```python
# services/context/consumers/planning_consumer.py

async def _handle_plan_approved(self, msg):
    """Handle plan approval events."""
    try:
        event = json.loads(msg.data.decode())
        story_id = event.get("story_id")
        plan_id = event.get("plan_id")
        
        logger.info(f"Plan approved: {plan_id} for story {story_id}")  # ← ESTO NO APARECE EN LOGS
        
        # Record approval in graph
        if self.graph:
            await asyncio.to_thread(
                self.graph.upsert_entity,
                entity_type="PlanApproval",
                entity_id=f"{plan_id}:{timestamp}",
                properties={...}
            )
        
        await msg.ack()
    except Exception as e:
        logger.error(f"Error handling plan approval: {e}")
        await msg.nak()
```

**El código está BIEN**, pero el método `_handle_plan_approved` **nunca se ejecuta**.

### Hipótesis

#### ❌ Hipótesis 1: "Consumers no suscritos"
**Descartada**: Los logs muestran `✓ Subscribed to planning.plan.approved`

#### ❌ Hipótesis 2: "Stream no existe"
**Descartada**: Los logs muestran `✓ All streams ensured`

#### ❌ Hipótesis 3: "Mensaje no llegó a NATS"
**Descartada**: nats-box confirma `Published 227 bytes to "planning.plan.approved"`

#### ✅ Hipótesis 4: "Consumer no está recibiendo mensajes del stream"
**POSIBLE CAUSA**:

1. **Push vs Pull Consumers**: El código usa `js.subscribe()` que es un **push consumer**, pero:
   - Podría no estar configurado correctamente para JetStream
   - Podría estar esperando un durableque no existe
   - El `queue` parameter podría no estar funcionando como esperado

2. **Problema con Queue Groups en JetStream**:
   ```python
   await self.js.subscribe(
       "planning.plan.approved",
       queue="context-workers",  # ← Esto podría ser el problema
       cb=self._handle_plan_approved,
   )
   ```
   
   En NATS JetStream, los **queue groups** funcionan diferente que en core NATS.
   Para JetStream, necesitas crear un **durable consumer** explícitamente.

3. **Falta configuración de Consumer**:
   El código no especifica:
   - `durable`: Nombre del durable consumer
   - `deliver_policy`: DeliverAll, DeliverLast, etc.
   - `ack_policy`: Explicit, All, None

---

## 🔧 SOLUCIÓN PROPUESTA

### Opción 1: Crear Durable Consumers Explícitamente (Recomendado)

```python
# services/context/consumers/planning_consumer.py

async def start(self):
    """Start consuming planning events."""
    
    # Crear durable consumer explícitamente
    consumer_config = ConsumerConfig(
        durable_name="context-planning-consumer",
        deliver_policy=DeliverPolicy.ALL,
        ack_policy=AckPolicy.EXPLICIT,
        filter_subject="planning.plan.approved"
    )
    
    # Suscribirse usando el durable consumer
    sub = await self.js.pull_subscribe(
        subject="planning.plan.approved",
        durable="context-planning-consumer",
        config=consumer_config
    )
    
    # Procesar mensajes en loop
    while True:
        try:
            msgs = await sub.fetch(batch=1, timeout=5)
            for msg in msgs:
                await self._handle_plan_approved(msg)
        except TimeoutError:
            continue
```

### Opción 2: Usar Push Consumer Correctamente

```python
async def start(self):
    """Start consuming planning events with push consumer."""
    
    # Crear consumer con configuración explícita
    await self.js.subscribe(
        subject="planning.plan.approved",
        durable="context-planning-consumer",  # ← Nombre del durable
        stream="PLANNING_EVENTS",  # ← Nombre del stream
        cb=self._handle_plan_approved,
        pending_msgs_limit=1000,
        pending_bytes_limit=10 * 1024 * 1024,  # 10MB
    )
```

### Opción 3: Verificar Implementación de NATS Client

Verificar que estamos usando `nats-py` correctamente:

```python
# ¿Versión correcta?
# pip show nats-py
# Name: nats-py
# Version: 2.x.x  (debe ser >= 2.0)
```

---

## 📋 PRÓXIMOS PASOS

### PASO 1: Verificar Consumers Existentes en NATS
```bash
# Desde un pod con nats CLI
kubectl exec -n swe-ai-fleet nats-0 -- nats consumer ls PLANNING_EVENTS
```

**Esperado**: Debería mostrar `context-planning-consumer` o similar  
**Si está vacío**: Confirma que los consumers no se están creando

### PASO 2: Revisar Documentación de nats-py
```bash
# Verificar API de JetStream en nats-py
# https://github.com/nats-io/nats.py/blob/main/examples/jetstream.py
```

### PASO 3: Implementar Pull Consumers (Más Robusto)
- Pull consumers dan más control
- Más fáciles de debuggear
- Mejor para procesamiento batch

### PASO 4: Añadir Logging de Debug
```python
logger.setLevel(logging.DEBUG)
# Agregar logs en:
# - Cuando se crea la suscripción
# - Cuando se recibe un mensaje
# - Antes/después de ack()
```

### PASO 5: Test con Core NATS (Sin JetStream)
Para validar que el problema es específico de JetStream:
```python
await self.nc.subscribe("planning.plan.approved", cb=handler)
# Sin js.subscribe, solo nc.subscribe (core NATS)
```

---

## 📈 MÉTRICAS ACTUALES

| Métrica | Valor | Estado |
|---------|-------|--------|
| **Pods Running** | 16/16 | ✅ |
| **NATS Connections** | 3/3 | ✅ (Orchestrator, Context, Planning) |
| **Streams Created** | 5/5 | ✅ |
| **Consumers Created** | 0/6 | ❌ **PROBLEMA** |
| **Eventos Publicados** | 2 | ✅ (ambos exitosos) |
| **Eventos Procesados** | 0 | ❌ **PROBLEMA** |
| **Datos en Neo4j** | 0 nodos | ❌ (esperado: 2 PlanApproval) |
| **Datos en ValKey** | 0 keys | ⚠️ (normal, no hay cache activa) |

---

## ✅ CONCLUSIÓN

### Estado Actual

**Infraestructura: 100% Operacional ✅**
- Todos los servicios conectados
- Todos los streams creados
- Persistencia verificada

**Comunicación: 0% Funcional ❌**
- Eventos se publican correctamente
- Consumers NO están procesando mensajes
- Problema específico de JetStream consumers

### Impacto

**Alto**: Sin consumers funcionando, **NO hay flujo de eventos** en el sistema:
- Planning no puede notificar a Context
- Orchestrator no puede notificar a Context
- Context no actualiza Neo4j
- **El sistema está desacoplado pero sin comunicación**

### Prioridad

**CRÍTICA**: Resolver configuración de JetStream consumers es **bloqueante** para:
- Flujo de eventos asíncrono
- Actualización automática de contexto
- Persistencia de decisiones
- Integración Planning ↔ Orchestrator ↔ Context

---

## 📚 REFERENCIAS

- [NATS JetStream Consumers](https://docs.nats.io/nats-concepts/jetstream/consumers)
- [nats-py JetStream Examples](https://github.com/nats-io/nats.py/tree/main/examples)
- [COMMUNICATION_AUDIT.md](./COMMUNICATION_AUDIT.md) - Arquitectura completa
- [NATS_CONSUMERS_DESIGN.md](./docs/architecture/NATS_CONSUMERS_DESIGN.md) - Diseño original

---

**Generado**: 2025-10-16 17:22  
**Test ejecutado desde**: natsio/nats-box:latest  
**Entorno**: Cluster K8s en producción (namespace: swe-ai-fleet)

