# Planning UI - TODO Status

Este documento refleja el estado de los TODOs y tareas relacionadas con la finalización del Planning UI.

**Última actualización:** 2025-11-26

---

## ✅ Tareas Completadas

### 1. Dependencias e Infraestructura
- [x] **Instalar dependencias gRPC** (`@grpc/grpc-js`, `@grpc/proto-loader`)
  - Dependencias agregadas a `package.json`
  - Instalación verificada

- [x] **Generación de código gRPC desde .proto** (NUEVO)
  - Agregado `grpc-tools` como dev dependency
  - Script `scripts/generate-grpc.js` para generar código TypeScript/JavaScript
  - Código generado durante Docker build (antes de `npm run build`)
  - Genera `planning_pb.js` (mensajes) y `planning_grpc_pb.js` (cliente)
  - Cliente actualizado para usar código generado con fallback a proto-loader

- [x] **Configurar carga de protobuf** (Legacy - mantener para desarrollo)
  - Proto copiado al container en build time
  - Carga dinámica usando `@grpc/proto-loader` como fallback
  - Resolución de rutas para desarrollo, producción y container

### 2. Cliente gRPC
- [x] **Crear cliente gRPC reutilizable** (`src/lib/grpc-client.ts`)
  - Singleton pattern para reutilización
  - **Usa código generado desde .proto** (preferido)
  - Fallback a carga de protobuf en runtime (para desarrollo)
  - Mapeo de errores gRPC a códigos HTTP
  - Helper `promisifyGrpcCall` para wrappear callbacks
  - Función `isServiceError` para validación de errores
  - Configuración de keepalive para conexiones estables

- [x] **Actualizar configuración** (`src/lib/config.ts`)
  - Soporte para hostname sin protocolo HTTP
  - Extracción automática de hostname si viene con protocolo
  - Separación de hostname y puerto

### 3. Integración en Rutas API
- [x] **Rutas de Projects**
  - `GET /api/projects` - Listar proyectos
  - `POST /api/projects` - Crear proyecto
  - `GET /api/projects/[id]` - Obtener proyecto por ID

- [x] **Rutas de Epics**
  - `GET /api/epics` - Listar epics (con filtro por project_id)
  - `POST /api/epics` - Crear epic

- [x] **Rutas de Stories**
  - `GET /api/stories` - Listar stories (con filtro por state)
  - `POST /api/stories` - Crear story
  - `GET /api/stories/[id]` - Obtener story por ID
  - `POST /api/stories/[id]/transition` - Transición FSM de story

- [x] **Rutas de Tasks**
  - `GET /api/tasks` - Listar tasks (con filtros por story_id y status)

### 4. Build y Deployment
- [x] **Dockerfile actualizado**
  - Generación de código gRPC durante build (script `generate-grpc.js`)
  - Copia de código generado a imagen final (`gen/`)
  - Contexto de build configurado desde raíz del proyecto
  - Build exitoso verificado: código generado presente en imagen final
  - Push y deploy completados: versión con código generado desplegada

- [x] **Deployment Kubernetes actualizado**
  - Variables de entorno ajustadas (solo hostname, sin protocolo)
  - `PUBLIC_PLANNING_SERVICE_URL=planning.swe-ai-fleet.svc.cluster.local`
  - `PUBLIC_PLANNING_SERVICE_PORT=50054`

- [x] **Build de imagen Docker**
  - Imagen con generación de código gRPC construida exitosamente
  - Código generado verificado en imagen: `planning_pb.js` (239KB) y `planning_grpc_pb.js` (21KB)
  - Push al registry completado (2025-11-26)

- [x] **Deployment en Kubernetes**
  - Deployment actualizado con nueva imagen
  - 2 pods corriendo correctamente con código generado
  - API respondiendo correctamente
  - Sin errores en logs
  - Verificación de salud OK

### 5. Documentación
- [x] **README.md actualizado**
  - Estado de integración gRPC reflejado
  - Variables de entorno documentadas

- [x] **GRPC_INTEGRATION.md actualizado**
  - Estado completado documentado
  - Arquitectura y componentes documentados

---

## 🔄 Tareas Pendientes

### 1. Tests Unitarios - Planning UI
- [ ] **Tests para cliente gRPC** (`src/lib/grpc-client.ts`)
  - Test de inicialización del cliente
  - Test de carga de protobuf
  - Test de manejo de errores
  - Test de `isServiceError` helper
  - Test de `grpcErrorToHttpStatus` mapping
  - Mock de gRPC calls

- [ ] **Tests para rutas API**
  - Tests para cada ruta (projects, epics, stories, tasks)
  - Tests de casos exitosos
  - Tests de casos de error
  - Tests de validación de entrada
  - Mock del cliente gRPC

- [ ] **Cobertura objetivo**
  - ≥ 90% de cobertura de líneas y ramas
  - Tests de edge cases
  - Tests de integración (opcional)

### 2. Tests Unitarios - Planning Service (Cambios Realizados)
**Razón:** Se modificó código crítico que necesita validación con tests.

- [ ] **Tests para `StorageAdapter.list_projects()`**
  - Test que verifica que retorna lista vacía `[]` (no `None`)
  - Test que verifica el warning log cuando no está completamente implementado
  - Test de firma del método (limit, offset)
  - Ubicación: `services/planning/tests/unit/infrastructure/adapters/test_storage_adapter.py`

- [ ] **Tests para `ListProjectsUseCase.execute()`**
  - Test que verifica validación defensiva (None → lista vacía)
  - Test que verifica logging correcto
  - Test de propagación de errores de storage
  - Test con lista vacía vs lista con proyectos
  - Ubicación: `services/planning/tests/unit/application/usecases/test_list_projects_usecase.py`

- [ ] **Tests de integración para implementación futura**
  - Test que verifica persistencia real de Projects en Neo4j/Valkey
  - Test que verifica que `list_projects` retorna proyectos reales
  - Test de paginación (limit, offset)
  - Test de filtros por status (cuando se implemente)

**Nota:** Estos tests son críticos porque:
1. Validan que el fix actual funciona correctamente (no retorna `None`)
2. Proporcionan especificación para la implementación completa futura
3. Previenen regresiones cuando se implemente la persistencia completa

### 3. Mejoras Futuras
- [ ] **Real-time updates**
  - WebSocket o polling para actualizaciones en tiempo real
  - Integración con NATS para eventos

- [ ] **Manejo de errores mejorado**
  - Retry logic para conexiones gRPC
  - Circuit breaker pattern
  - Timeout handling más robusto

- [ ] **Optimizaciones**
  - Caching de respuestas frecuentes
  - Paginación mejorada en UI
  - Lazy loading de datos

### 4. Integración Completa con Planning Service
- [ ] **Implementación completa de `list_projects` en storage**
  - Persistencia de Projects en Neo4j (nodos y relaciones)
  - Persistencia de Projects en Valkey (detalles completos)
  - Query real que retorna proyectos almacenados
  - Soporte para filtros por status
  - Paginación funcional (limit, offset)

- [ ] **Tests de integración para nueva implementación**
  - Test E2E: crear proyecto → listar proyectos
  - Test de persistencia dual (Neo4j + Valkey)
  - Test de filtros y paginación
  - Verificar que todas las operaciones CRUD funcionan

**Archivos a modificar:**
- `services/planning/infrastructure/adapters/storage_adapter.py` (completar método `list_projects`)
- `services/planning/infrastructure/adapters/neo4j_adapter.py` (métodos para Projects)
- `services/planning/infrastructure/adapters/valkey_adapter.py` (métodos para Projects)

---

## 🐛 Problemas Conocidos

### 1. Planning Service - `list_projects` retorna `None`
**Estado:** ✅ Fix implementado y desplegado

### 2. Planning Service - Error `topic` vs `subject` en `publish_event`
**Estado:** ✅ Fix implementado y desplegado (2025-11-26 10:13)

### 3. Planning Service - Métodos de storage para Projects NO implementados ⚠️
**Error observado:** "Failed to load project: Not Found" cuando intentas acceder a un proyecto después de crearlo.

**Causa raíz:**
- `StorageAdapter.get_project()` **NO está implementado** - El protocolo `StoragePort` lo define, pero el adapter no lo implementa
- `StorageAdapter.save_project()` **NO está implementado** - Los proyectos se crean pero NO se persisten
- `StorageAdapter.list_projects()` solo retorna lista vacía (es un stub con TODO)

**Evidencia en código:**
- `services/planning/infrastructure/adapters/storage_adapter.py` solo tiene métodos para Stories
- No hay `get_project()` ni `save_project()` implementados
- Logs muestran: `Project not found: PROJ-e5a8c267-a03f-4fae-b699-3a5d77427585`

**Solución necesaria:**
1. Crear `ProjectValkeyMapper` (similar a `StoryValkeyMapper`)
2. Agregar keys para projects en `ValkeyKeys`:
   - `planning:project:{project_id}` → Hash con detalles del proyecto
   - `planning:projects:all` → Set con todos los project IDs
3. Implementar `save_project()` y `get_project()` en `StorageAdapter`
4. Implementar `list_projects()` correctamente (actualmente solo retorna `[]`)

**Prioridad:** 🔴 **ALTA** - Los proyectos no se pueden recuperar después de crearse

**Estado:** ✅ **IMPLEMENTADO** (2025-11-26)

**Solución implementada:**
1. ✅ Creado `ProjectValkeyMapper` (`services/planning/infrastructure/mappers/project_valkey_mapper.py`)
   - Similar a `StoryValkeyMapper` para mantener consistencia
   - Métodos `to_dict()` y `from_dict()` para conversión Domain ↔ Valkey
   - Manejo de keys bytes y strings (Valkey puede devolver ambos)

2. ✅ Agregado keys para projects en `ValkeyKeys`:
   - `project_hash(project_id)` → `planning:project:{project_id}`
   - `all_projects()` → `planning:projects:all`

3. ✅ Implementado en `ValkeyStorageAdapter`:
   - `save_project()` - Persiste proyecto en hash + agrega a set
   - `get_project()` - Recupera proyecto por ID
   - `list_projects()` - Lista proyectos con paginación

4. ✅ Implementado en `StorageAdapter`:
   - `save_project()` - Delega a ValkeyStorageAdapter
   - `get_project()` - Delega a ValkeyStorageAdapter
   - `list_projects()` - Delega a ValkeyStorageAdapter (eliminado stub)

**Próximos pasos:**
- [x] Rebuild y deploy del Planning Service ✅ (2025-11-26 - v2.0.1)
- [x] Verificar que crear proyectos funciona y se persisten ✅ (verificado)
- [x] Verificar que listar proyectos funciona ✅ (verificado - retorna proyectos)
- [x] Verificar que obtener proyecto por ID funciona ✅ (verificado - funciona correctamente)

**Fix adicional aplicado:**
- `ResponseMapper.project_response()` ahora incluye campos `success` y `message` en la respuesta
- Handler `get_project_handler` actualizado para usar mapper completo

**Ubicación del bug:**
- `services/planning/application/usecases/create_project_usecase.py`
- `services/planning/application/usecases/create_epic_usecase.py`
- `services/planning/application/usecases/create_task_usecase.py`
- `services/planning/application/usecases/derive_tasks_from_plan_usecase.py`
- `services/planning/application/services/task_derivation_result_service.py`

**Descripción:**
- Los use cases llamaban a `messaging.publish_event(topic=...)` pero el puerto `MessagingPort` y el adaptador `NATSMessagingAdapter` esperan `subject=...`
- Esto causaba error: `TypeError: NATSMessagingAdapter.publish_event() got an unexpected keyword argument 'topic'`
- El error se manifestaba al crear proyectos, epics, tasks, etc.

**Solución implementada:**
- Cambiado `topic=` por `subject=` en todas las llamadas a `publish_event()`
- Archivos corregidos:
  - `create_project_usecase.py`: `subject="planning.project.created"`
  - `create_epic_usecase.py`: `subject="planning.epic.created"`
  - `create_task_usecase.py`: `subject="planning.task.created"`
  - `derive_tasks_from_plan_usecase.py`: `subject="task.derivation.requested"`
  - `task_derivation_result_service.py`: `subject=...` (2 lugares)

**Próximos pasos:**
- [x] Rebuild de imagen del Planning Service ✅
- [x] Push al registry ✅
- [x] Update deployment en Kubernetes ✅
- [x] Verificar que crear proyectos funciona sin error ✅
  - Logs confirman: `Event published: subject=planning.project.created, seq=1, stream=PLANNING_EVENTS`
  - Sin errores de `TypeError` relacionados con `topic`

**Ubicación del bug:**
- `services/planning/infrastructure/adapters/storage_adapter.py`
- `services/planning/application/usecases/list_projects_usecase.py`

**Descripción:**
- El Planning Service tenía un bug crítico donde el método `list_projects()` no estaba implementado en `StorageAdapter`
- Al llamar al método, Python retornaba implícitamente `None` en lugar de una lista vacía `[]`
- Esto causaba error en el use case: `TypeError: object of type 'NoneType' has no len()`
- El error se propagaba al handler gRPC y retornaba código `13 INTERNAL` al cliente

**Síntomas:**
- Cualquier llamada a `ListProjects` desde planning-ui fallaba
- Logs del Planning Service mostraban: `object of type 'NoneType' has no len()`
- planning-ui recibía error gRPC `13 INTERNAL` sin detalles útiles

**Solución implementada:**

1. **Implementación de `list_projects` en `StorageAdapter`:**
   ```python
   async def list_projects(self, limit: int = 100, offset: int = 0) -> list[Project]:
       """
       List all projects with pagination.

       TODO: Implement full storage integration (Neo4j/Valkey).
       For now, returns empty list to prevent NoneType errors.
       """
       logger.warning(
           "list_projects not fully implemented - returning empty list. "
           "Full storage integration pending."
       )
       return []
   ```

2. **Validación defensiva en `ListProjectsUseCase`:**
   ```python
   projects = await self._storage.list_projects(limit=limit, offset=offset)

   # Fail-fast: Ensure projects is never None (defensive programming)
   if projects is None:
       logger.warning("Storage returned None for list_projects, returning empty list")
       projects = []
   ```

**Archivos modificados:**
- `services/planning/infrastructure/adapters/storage_adapter.py` (líneas 208-233)
- `services/planning/application/usecases/list_projects_usecase.py` (líneas 36-40)

**Próximos pasos:**
- [ ] Rebuild de imagen del Planning Service
- [ ] Push al registry
- [ ] Update deployment en Kubernetes
- [ ] Verificar que el fix funciona (planning-ui puede listar proyectos sin error)
- [ ] Implementar persistencia completa de Projects (Neo4j/Valkey) para retornar proyectos reales

**Nota:** La solución actual retorna lista vacía, lo que permite que planning-ui funcione sin errores, pero no retorna proyectos reales. La implementación completa de storage está pendiente (ver TODO en código).

---

## 📝 Notas Técnicas

### Arquitectura
- **Cliente gRPC:** Singleton pattern con cache
- **Código generado:** TypeScript/JavaScript generado desde .proto durante build
- **Fallback:** Carga dinámica en runtime usando proto-loader (desarrollo)
- **Manejo de errores:** Mapeo de códigos gRPC a HTTP

### Variables de Entorno
```bash
PUBLIC_PLANNING_SERVICE_URL=planning.swe-ai-fleet.svc.cluster.local
PUBLIC_PLANNING_SERVICE_PORT=50054
```

**Importante:** El URL debe ser solo hostname (sin `http://` o `https://`)

### Estructura de Archivos
```
services/planning-ui/
├── src/
│   ├── lib/
│   │   ├── grpc-client.ts    # Cliente gRPC (usa código generado)
│   │   ├── config.ts          # Configuración
│   │   └── types.ts           # Type definitions
│   └── pages/
│       └── api/               # Rutas API (proxy gRPC)
├── scripts/
│   └── generate-grpc.js       # Script para generar código desde .proto
├── gen/                       # Código generado (no en git, generado en build)
│   └── fleet/planning/v2/
│       ├── planning_pb.js     # Mensajes protobuf
│       └── planning_grpc_pb.js # Cliente gRPC
├── Dockerfile                 # Genera código gRPC durante build
└── TODO.md                    # Este archivo
```

---

## 🎯 Próximos Pasos Prioritarios

1. **Implementar tests unitarios** (alta prioridad)
   - Cliente gRPC
   - Rutas API
   - Verificar cobertura ≥ 90%

2. **Rebuild/deploy Planning Service** (alta prioridad)
   - Aplicar fix de `list_projects` ✅ (completado y desplegado)
   - Aplicar fix de `publish_event` (topic → subject) ✅ (completado y desplegado)
   - Verificar que la integración funciona end-to-end ✅ (verificado - eventos publicándose correctamente)
   - Verificar que crear proyectos funciona sin error ✅ (verificado - eventos publicados a NATS)

3. **Mejoras de UX** (media prioridad)
   - Real-time updates
   - Manejo de errores en UI
   - Loading states

---

**Versión actual:** v0.1.4 (con generación de código gRPC - desplegado)
**Último deploy:** 2025-11-26 11:08
**Branch:** `feature/finalize-planning-ui`

---

## 📊 Resultados del Deploy (2025-11-26)

### Generación de Código gRPC
- ✅ Build exitoso con código generado desde `.proto`
- ✅ Archivos verificados en imagen:
  - `gen/fleet/planning/v2/planning_pb.js` (239 KB) - Mensajes protobuf
  - `gen/fleet/planning/v2/planning_grpc_pb.js` (21 KB) - Cliente gRPC
- ✅ Código copiado correctamente a imagen final en etapa de producción
- ✅ Script de generación: `scripts/generate-grpc.js` ejecutándose durante build

### Deploy y Verificación
- ✅ **Push al registry:** Completado exitosamente
  - Imagen: `registry.underpassai.com/swe-ai-fleet/planning-ui:latest`
  - Tamaño optimizado con multi-stage build
- ✅ **Deployment en Kubernetes:**
  - Deployment actualizado y rollout completado
  - 2/2 pods corriendo correctamente (nuevos pods con código generado)
  - Pods: `planning-ui-7dc6f66d84-f8tw7`, `planning-ui-7dc6f66d84-x6ckj`
  - Estado: `Running` y `Ready: true`
- ✅ **API funcionando:**
  - `GET /api/projects` → `{"projects":[],"total_count":0,"success":true}`
  - Respuesta correcta, sin errores
- ✅ **Logs verificados:**
  - Sin errores relacionados con gRPC o generación de código
  - Sin errores de carga de protobuf
  - Cliente gRPC usando código generado correctamente

### Arquitectura Final
- **Producción:** Usa código generado desde `.proto` (más eficiente)
- **Desarrollo:** Fallback a `proto-loader` si código generado no disponible
- **Build:** Código generado automáticamente durante Docker build
- **Runtime:** No necesita cargar `.proto` en runtime (mejor rendimiento)

