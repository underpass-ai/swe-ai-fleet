# 🔍 Análisis de Pull Consumers - Estado Actual

**Fecha**: 16 de Octubre de 2025, 20:56  
**Versiones**: Context v0.8.1, Orchestrator v0.7.0

---

## 📊 RESUMEN DE CAMBIOS IMPLEMENTADOS

### 1. Migración: Push Consumers → Pull Consumers

**Razón**: Resolver error `"consumer is already bound to a subscription"` con múltiples pods

**Patrón implementado**:
```python
# ANTES (Push Consumer):
await js.subscribe(
    subject="planning.plan.approved",
    stream="PLANNING_EVENTS",
    durable="context-planning-plan-approved",
    cb=self._handle_plan_approved,  # ← Callback automático
    manual_ack=True,
)

# DESPUÉS (Pull Consumer):
self._plan_sub = await js.pull_subscribe(
    subject="planning.plan.approved",
    durable="context-planning-plan-approved",
    stream="PLANNING_EVENTS",
)

# Background task para polling:
async def _poll_plan_approvals(self):
    while True:
        msgs = await self._plan_sub.fetch(batch=1, timeout=5)
        for msg in msgs:
            await self._handle_plan_approved(msg)
```

---

## ✅ CÓDIGO MODIFICADO

### Consumers de Context Service

1. **planning_consumer.py**:
   - ✅ Pull subscribe para `planning.story.transitioned`
   - ✅ Pull subscribe para `planning.plan.approved`
   - ✅ Background tasks: `_poll_story_transitions()`, `_poll_plan_approvals()`
   - ✅ Logging INFO agregado (emojis para visibilidad)

2. **orchestration_consumer.py**:
   - ✅ Pull subscribe para `orchestration.deliberation.completed`
   - ✅ Pull subscribe para `orchestration.task.dispatched`
   - ✅ Background tasks: `_poll_deliberation_completed()`, `_poll_task_dispatched()`
   - ⚠️ Sin logging en polling loops

### Consumers de Orchestrator Service

3. **planning_consumer.py**:
   - ✅ Pull subscribe para `planning.story.transitioned`
   - ✅ Pull subscribe para `planning.plan.approved`
   - ✅ Background tasks creados
   - ⚠️ Sin logging en polling loops

4. **context_consumer.py**:
   - ✅ Pull subscribe para `context.updated`, `context.milestone.reached`, `context.decision.added`
   - ✅ Background tasks creados (3 tasks)
   - ⚠️ Sin logging en polling loops

---

## 🔍 PROBLEMA IDENTIFICADO

### Background Tasks NO están haciendo fetch

**Evidencia**:
```bash
# Log al iniciar:
2025-10-16 18:54:59 [INFO] 🔄 Background task _poll_plan_approvals started

# Pero NUNCA aparece:
📥 Fetching plan approvals (timeout=5s)...
✅ Received X plan approval messages
⏱️  No plan approvals (timeout), continuing...
```

**Consecuencia**: 13 mensajes sin procesar en el stream

**Posibles causas**:

### Causa #1: Background tasks se crean pero no se ejecutan
```python
# En start():
self._tasks = [
    asyncio.create_task(self._poll_story_transitions()),
    asyncio.create_task(self._poll_plan_approvals()),
]
# ← Los tasks se crean pero nadie los "awaits"
```

**Problema**: En Python async, `create_task()` crea el task pero si no hay un event loop activo o el task no está siendo await, puede no ejecutarse.

**Solución**: El event loop del servidor gRPC debe mantener los tasks vivos.

---

### Causa #2: Event loop del servidor gRPC no es async

```python
# services/context/server.py:842
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
# ← Este es un servidor SÍNCRONO (ThreadPoolExecutor)

# Los background tasks son ASÍNCRONOS
async def _poll_plan_approvals(self):
    while True:
        msgs = await self._plan_sub.fetch(...)
```

**Problema CRÍTICO**: 
- Servidor gRPC corre en threads síncronos
- Background tasks son async y necesitan event loop activo
- **No hay event loop activo después de `await planning_consumer.start()`**

---

## 🔧 SOLUCIÓN REQUERIDA

### Opción 1: Ejecutar tasks en el event loop principal

```python
# services/context/server.py (en main async)

# Crear consumers
await planning_consumer.start()
await orchestration_consumer.start()

# Los tasks ya están creados, pero necesitan ejecutarse
# Mantenerlos vivos hasta shutdown

# Al final del servidor:
try:
    await server.wait_for_termination()
finally:
    # Cancel background tasks
    for task in planning_consumer._tasks:
        task.cancel()
    for task in orchestration_consumer._tasks:
        task.cancel()
```

**Problema**: Los tasks se crean pero **el event loop termina** después de `start()` porque no hay nada que los mantenga vivos.

---

### Opción 2: Crear threads para ejecutar event loops

```python
# Cada consumer corre su propio event loop en thread separado
import threading

def run_consumer_loop(consumer):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(consumer.start())
    loop.run_forever()

# Start consumers en threads
threading.Thread(target=run_consumer_loop, args=(planning_consumer,), daemon=True).start()
```

---

### Opción 3: Usar gRPC async server (RECOMENDADO)

```python
# Usar aio.server() en lugar de grpc.server()
import grpc.aio

async def serve():
    server = grpc.aio.server()
    context_pb2_grpc.add_ContextServiceServicer_to_server(servicer, server)
    
    # Start consumers (background tasks se crean)
    await planning_consumer.start()
    await orchestration_consumer.start()
    
    # Start server
    server.add_insecure_port(f'[::]:{port}')
    await server.start()
    
    # Wait for termination (event loop sigue activo)
    await server.wait_for_termination()
```

**Beneficio**: El event loop async del servidor mantiene los background tasks vivos.

---

## 📋 ESTADO ACTUAL

### ✅ Lo que funciona

- Streams persistentes (FILE storage) ✅
- Pull subscriptions se crean correctamente ✅
- No hay conflictos de "already bound" con 2 pods ✅
- Neo4j: 2 nodos PlanApproval guardados ✅

### ❌ Lo que NO funciona

- Background tasks no hacen fetch ❌
- 13 mensajes sin procesar en stream ❌
- Solo procesó mensajes viejos al arrancar ❌

---

## 🎯 PRÓXIMOS PASOS

### CRÍTICO: Migrar a gRPC async server

**Archivos a modificar**:
1. `services/context/server.py` - Cambiar a `grpc.aio.server()`
2. `services/orchestrator/server.py` - Cambiar a `grpc.aio.server()`

**Impacto**:
- Event loop activo durante toda la vida del servidor
- Background tasks se ejecutan continuamente
- Compatible con Pull Consumers

---

## 🔄 ALTERNATIVA TEMPORAL (Sin cambiar servidor)

Cambiar background tasks a **threads síncronos** en lugar de async tasks:

```python
import threading

def run_polling_loop(pull_sub, handler):
    """Run synchronous polling loop in thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def poll():
        while True:
            msgs = await pull_sub.fetch(batch=1, timeout=5)
            for msg in msgs:
                await handler(msg)
    
    loop.run_until_complete(poll())

# En start():
threading.Thread(
    target=run_polling_loop,
    args=(self._plan_sub, self._handle_plan_approved),
    daemon=True
).start()
```

---

**Conclusión**: Los Pull Consumers están **correctamente implementados** pero los **background tasks no se ejecutan** porque el servidor gRPC no es async. Necesitamos migrar a `grpc.aio.server()` o usar threads para los polling loops.

**Recomendación**: Migrar a gRPC async server (más limpio y compatible con arquitectura async).

