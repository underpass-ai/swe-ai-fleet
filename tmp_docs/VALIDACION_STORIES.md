# Validación: Creación, Guardado y Listado de Stories

**Fecha**: 2025-01-XX
**Objetivo**: Validar que el flujo completo de Stories funciona correctamente entre planning-ui y planning service

---

## 📋 Flujo a Validar

1. **Listar Stories** (GET /api/stories)
2. **Crear Story** (POST /api/stories)
3. **Obtener Story** (GET /api/stories/[id])
4. **Verificar persistencia** (listar de nuevo para confirmar que se guardó)

---

## 🔍 Componentes Verificados

### Frontend (planning-ui)

✅ **API Routes**:
- `src/pages/api/stories/index.ts` - Listar y crear stories
- `src/pages/api/stories/[id].ts` - Obtener story individual

✅ **Request Builders**:
- `buildListStoriesRequest` - Implementado
- `buildCreateStoryRequest` - Implementado
- `buildGetStoryRequest` - Implementado

### Backend (planning service)

✅ **gRPC Handlers**:
- `create_story_handler.py` - Implementado
- `list_stories_handler.py` - Implementado
- `get_story_handler.py` - Implementado

✅ **Use Cases**:
- `CreateStoryUseCase` - Implementado
- `ListStoriesUseCase` - Implementado
- `GetStoryUseCase` - Implementado

✅ **Storage**:
- `StorageAdapter.save_story()` - Dual persistence (Neo4j + Valkey)
- `StorageAdapter.get_story()` - Desde Valkey
- `StorageAdapter.list_stories()` - Desde Valkey con filtros

---

## 🧪 Pruebas Manuales

### Prerequisitos

1. **Obtener un Epic ID existente**:
```bash
# Listar epics para obtener un epic_id
curl -k 'https://planning.underpassai.com/api/epics?project_id=PROJ-xxx' \
  -H 'accept: */*'
```

2. **Obtener un Project ID existente** (si no tienes epic_id):
```bash
# Listar projects
curl -k 'https://planning.underpassai.com/api/projects' \
  -H 'accept: */*'
```

### Test 1: Listar Stories (vacío inicial)

```bash
curl -k 'https://planning.underpassai.com/api/stories' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json'
```

**Resultado esperado**:
```json
{
  "stories": [],
  "total_count": 0,
  "success": true,
  "message": "Stories retrieved successfully"
}
```

### Test 2: Crear Story

```bash
curl -k -X POST 'https://planning.underpassai.com/api/stories' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
    "epic_id": "E-xxx",  # Reemplazar con epic_id real
    "title": "Test Story - Validación",
    "brief": "Esta es una story de prueba para validar el flujo completo",
    "created_by": "test-user"
  }'
```

**Resultado esperado**:
```json
{
  "story": {
    "story_id": "s-xxx",
    "epic_id": "E-xxx",
    "title": "Test Story - Validación",
    "brief": "Esta es una story de prueba para validar el flujo completo",
    "state": "DRAFT",
    "dor_score": 0,
    "created_by": "test-user",
    "created_at": "2025-01-XX...",
    "updated_at": "2025-01-XX..."
  },
  "success": true,
  "message": "Story created successfully"
}
```

**Guardar el `story_id` para el siguiente test**.

### Test 3: Obtener Story Individual

```bash
# Reemplazar s-xxx con el story_id obtenido en Test 2
curl -k 'https://planning.underpassai.com/api/stories/s-xxx' \
  -H 'accept: */*'
```

**Resultado esperado**:
```json
{
  "story": {
    "story_id": "s-xxx",
    "epic_id": "E-xxx",
    "title": "Test Story - Validación",
    "brief": "Esta es una story de prueba para validar el flujo completo",
    "state": "DRAFT",
    "dor_score": 0,
    "created_by": "test-user",
    "created_at": "2025-01-XX...",
    "updated_at": "2025-01-XX..."
  },
  "success": true,
  "message": "Story retrieved successfully"
}
```

### Test 4: Listar Stories (verificar persistencia)

```bash
curl -k 'https://planning.underpassai.com/api/stories' \
  -H 'accept: */*'
```

**Resultado esperado**:
```json
{
  "stories": [
    {
      "story_id": "s-xxx",
      "epic_id": "E-xxx",
      "title": "Test Story - Validación",
      "brief": "Esta es una story de prueba para validar el flujo completo",
      "state": "DRAFT",
      "dor_score": 0,
      "created_by": "test-user",
      "created_at": "2025-01-XX...",
      "updated_at": "2025-01-XX..."
    }
  ],
  "total_count": 1,
  "success": true,
  "message": "Stories retrieved successfully"
}
```

### Test 5: Filtrar Stories por Estado

```bash
curl -k 'https://planning.underpassai.com/api/stories?state=DRAFT' \
  -H 'accept: */*'
```

**Resultado esperado**: Solo stories con estado DRAFT.

---

## 🔍 Verificación en Backend

### Revisar Logs de Planning Service

```bash
# Ver logs de un pod de planning
kubectl logs -n swe-ai-fleet planning-f6ffb5f77-gsgst --tail=50 | grep -i story
```

**Buscar**:
- `CreateStory: epic_id=...`
- `Story saved (dual): s-xxx`
- `ListStories: state=...`
- `GetStory: story_id=...`

### Verificar en Valkey

```bash
# Conectar a Valkey pod
kubectl exec -it -n swe-ai-fleet valkey-0 -- redis-cli

# Verificar que la story está guardada
HGETALL planning:story:s-xxx

# Verificar índices
SMEMBERS planning:stories:all
SMEMBERS planning:stories:state:DRAFT
```

### Verificar en Neo4j

```bash
# Conectar a Neo4j pod
kubectl exec -it -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p <password>

# Verificar que el nodo existe
MATCH (s:Story {id: 's-xxx'}) RETURN s;
```

---

## ✅ Checklist de Validación

- [ ] **Listar Stories** funciona (GET /api/stories)
- [ ] **Crear Story** funciona (POST /api/stories)
- [ ] **Obtener Story** funciona (GET /api/stories/[id])
- [ ] **Persistencia en Valkey** verificada
- [ ] **Persistencia en Neo4j** verificada
- [ ] **Filtro por estado** funciona
- [ ] **Eventos NATS** publicados (opcional)
- [ ] **Logs sin errores** en planning service
- [ ] **Logs sin errores** en planning-ui

---

## 🐛 Problemas Conocidos

### Si CreateStory falla con "Epic not found"

**Causa**: El `epic_id` no existe en la base de datos.

**Solución**: Crear un Epic primero o usar un `epic_id` existente.

### Si GetStory retorna 404

**Causa**: El `story_id` no existe o está mal formateado.

**Solución**: Verificar que el `story_id` es correcto (formato: `s-xxx`).

### Si ListStories retorna vacío después de crear

**Causa**: Problema de persistencia o índice en Valkey.

**Solución**: Verificar logs de planning service y conexión a Valkey.

---

## 📝 Notas

- Los request builders usan `buildRequestInstance` para crear mensajes protobuf correctamente
- El handler `get_story_handler` retorna `Story` directamente (no `GetStoryResponse`)
- La API route de `[id].ts` maneja esto correctamente
- La persistencia es dual: Neo4j (grafo) + Valkey (detalles)



