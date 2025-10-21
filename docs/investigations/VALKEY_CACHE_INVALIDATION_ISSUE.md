# ⚠️ Issue: ValKey Cache Invalidation No Funciona

**Fecha**: 16 de Octubre de 2025  
**Severidad**: 🟡 Media (no bloquea flujo principal)  
**Componente**: Context Service - Planning Consumer

---

## 🔍 PROBLEMA

El consumer `context-planning-story-transitions` **recibe eventos** de `planning.story.transitioned` pero **NO invalida el cache** en ValKey.

### Evidencia del Test de Stress

```bash
# Test ejecutado:
- 50 keys creadas en ValKey: context:STRESS-NEO-0001, context:STRESS-NEO-0002, ...
- 50 eventos planning.story.transitioned publicados
- Consumer procesó 50 mensajes (Delivered: 50, Unprocessed: 0)

# Resultado esperado:
- 0 keys restantes en ValKey (todas invalidadas)

# Resultado real:
- 50 keys restantes en ValKey ❌ (ninguna invalidada)
```

---

## 📋 CÓDIGO ACTUAL

**Archivo**: `services/context/consumers/planning_consumer.py`

**Handler**: `_handle_story_transitioned()`

```python
async def _handle_story_transitioned(self, msg):
    """Handle story phase transition events."""
    try:
        event = json.loads(msg.data.decode())
        story_id = event.get("story_id")
        from_phase = event.get("from_phase")
        to_phase = event.get("to_phase")
        timestamp = event.get("timestamp")

        logger.info(
            f"Story transition: {story_id} from {from_phase} to {to_phase}"
        )

        # Invalidate context cache for this story
        if self.cache:
            try:
                pattern = f"context:{story_id}*"
                cursor = 0
                deleted_count = 0
                
                # Usar SCAN para encontrar y eliminar keys
                while True:
                    cursor, keys = await asyncio.to_thread(
                        self.cache.scan,  # ← self.cache es redis.Redis client
                        cursor=cursor,
                        match=pattern,
                        count=100
                    )
                    if keys:
                        deleted = await asyncio.to_thread(
                            self.cache.delete,
                            *keys
                        )
                        deleted_count += deleted
                    if cursor == 0:
                        break
                
                logger.info(
                    f"Invalidated {deleted_count} context cache entries for {story_id} "
                    f"(phase: {to_phase})"
                )
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")

        # Record phase transition in graph for history
        if self.graph:
            try:
                await asyncio.to_thread(
                    self.graph.upsert_entity,
                    label="PhaseTransition",
                    id=f"{story_id}:{timestamp}",
                    properties={
                        "story_id": story_id,
                        "from_phase": from_phase,
                        "to_phase": to_phase,
                        "timestamp": timestamp,
                    },
                )
                logger.info(f"✓ PhaseTransition recorded in Neo4j: {story_id} {from_phase}→{to_phase}")
            except Exception as e:
                logger.error(f"Failed to record transition in graph: {e}", exc_info=True)

        # Acknowledge message
        await msg.ack()
        logger.debug(f"✓ Processed story transition for {story_id}")

    except Exception as e:
        logger.error(
            f"Error handling story transition: {e}",
            exc_info=True,
        )
        # Negative acknowledge to retry
        await msg.nak()
```

---

## 🔍 ANÁLISIS DE CAUSA RAÍZ

### Hipótesis #1: `self.cache` es None

**Verificación necesaria**:
```python
logger.info(f"Cache available: {self.cache is not None}")
```

**Si es None**: El consumer se inicializa sin acceso al cliente Redis.

---

### Hipótesis #2: Pattern de keys no coincide

**Pattern usado**: `context:{story_id}*`

**Keys creadas en test**: `context:STRESS-NEO-0001`

**Verificación**:
```python
# En el handler, agregar log:
logger.info(f"Searching cache with pattern: {pattern}")
logger.info(f"Cursor: {cursor}, Keys found: {len(keys) if keys else 0}")
```

**Posible problema**: 
- Pattern correcto: `context:STRESS-NEO-0001*`
- Si busca `context:STRESS-NEO-0001*` y la key es exactamente `context:STRESS-NEO-0001`, el wildcard `*` al final puede no matchear

**Corrección necesaria**:
```python
# Opción 1: Sin wildcard si es key exacta
pattern = f"context:{story_id}"
keys = [pattern]
deleted = await asyncio.to_thread(self.cache.delete, *keys)

# Opción 2: Usar KEYS (no recomendado en producción)
keys = await asyncio.to_thread(self.cache.keys, f"context:{story_id}*")

# Opción 3: SCAN con pattern correcto
pattern = f"context:{story_id}*"
# ... (código actual está bien)
```

---

### Hipótesis #3: Excepción silenciada

**Verificación**: Buscar en logs:
```bash
kubectl logs -n swe-ai-fleet deployment/context | grep "Failed to invalidate cache"
```

**Si aparece**: Hay un error en `self.cache.scan()` o `self.cache.delete()`

---

## 🔧 DEBUGGING REQUERIDO

### Paso 1: Agregar logging detallado

```python
async def _handle_story_transitioned(self, msg):
    ...
    logger.info(f"Story transition: {story_id} from {from_phase} to {to_phase}")
    logger.info(f">>> Cache client available: {self.cache is not None}")
    logger.info(f">>> Cache client type: {type(self.cache)}")
    
    if self.cache:
        try:
            pattern = f"context:{story_id}*"
            logger.info(f">>> Searching cache with pattern: {pattern}")
            
            cursor = 0
            deleted_count = 0
            iteration = 0
            
            while True:
                iteration += 1
                logger.info(f">>> SCAN iteration {iteration}, cursor: {cursor}")
                
                cursor, keys = await asyncio.to_thread(
                    self.cache.scan,
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                
                logger.info(f">>> Found {len(keys) if keys else 0} keys, new cursor: {cursor}")
                
                if keys:
                    logger.info(f">>> Deleting keys: {keys}")
                    deleted = await asyncio.to_thread(
                        self.cache.delete,
                        *keys
                    )
                    deleted_count += deleted
                    logger.info(f">>> Deleted {deleted} keys")
                    
                if cursor == 0:
                    break
                    
                if iteration > 100:  # Safety limit
                    logger.error(">>> SCAN iteration limit reached!")
                    break
            
            logger.info(
                f"✅ Invalidated {deleted_count} context cache entries for {story_id}"
            )
```

---

### Paso 2: Verificar inicialización del cache client

**Archivo**: `services/context/server.py`

**Buscar**:
```python
planning_consumer = PlanningEventsConsumer(
    nc=nats_handler.nc,
    js=nats_handler.js,
    cache_service=redis_store.client,  # ← Verificar que esto NO es None
    graph_command=graph_command,
)
```

**Agregar log**:
```python
logger.info(f"Initializing planning consumer with cache_service: {redis_store.client}")
```

---

### Paso 3: Test manual de invalidación

```bash
# Crear key
kubectl exec -n swe-ai-fleet valkey-0 -- valkey-cli SET "context:TEST-123" "test_value"

# Verificar que existe
kubectl exec -n swe-ai-fleet valkey-0 -- valkey-cli GET "context:TEST-123"

# Publicar evento de transición
nats pub planning.story.transitioned '{
  "story_id": "TEST-123",
  "from_phase": "DRAFT",
  "to_phase": "BUILD",
  "timestamp": "2025-10-16T20:00:00Z"
}'

# Esperar 5 segundos
sleep 5

# Verificar si se eliminó
kubectl exec -n swe-ai-fleet valkey-0 -- valkey-cli GET "context:TEST-123"
# Esperado: (nil)
# Si devuelve valor: ❌ No se invalidó
```

---

## 📝 ESTADO DEL ISSUE

**Prioridad**: 🟡 Media

**Razones**:
- ✅ NO bloquea flujo principal (Neo4j funciona perfecto)
- ✅ NO causa pérdida de datos
- ⚠️ Puede causar datos stale en cache
- ⚠️ Afecta performance (no refresca contexto)

**Impacto**:
- Agents pueden recibir contexto desactualizado si está cacheado
- No afecta a Neo4j (source of truth)

**Workaround temporal**:
- Usar TTL corto en cache (1 hora ya configurado)
- Cache expira automáticamente

---

## 🎯 PRÓXIMOS PASOS

1. **Agregar logging detallado** en `_handle_story_transitioned()`
2. **Rebuild Context Service** con logs
3. **Test manual** de invalidación con 1 key
4. **Identificar causa raíz** (None, pattern, excepción)
5. **Implementar corrección**
6. **Re-test** con stress test

---

**Conclusión**: El sistema funciona perfectamente para Neo4j (100% datos guardados, orden FIFO). La invalidación de cache en ValKey es un issue de lógica de negocio menor que no afecta la funcionalidad principal.

**Documentado**: 2025-10-16 21:56  
**Próxima acción**: Agregar logging y test manual para identificar causa raíz

