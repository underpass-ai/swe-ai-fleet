# Continuar Mañana - Task Derivation Service Migration

**Fecha:** 2025-11-14
**Estado Actual:** 🟡 Fase 1 Completada - Estructura Base Creada
**Próxima Sesión:** Continuar con Fase 2 (Domain Layer)

---

## ✅ Lo que se ha Completado Hoy

### Fase 1: Estructura Base ✅

1. **Estructura de directorios creada:**
   ```
   services/task-derivation/
   ├── task_derivation/
   │   ├── domain/
   │   │   ├── value_objects/task_derivation/
   │   │   └── events/
   │   ├── application/
   │   │   ├── ports/
   │   │   ├── usecases/
   │   │   └── services/
   │   └── infrastructure/
   │       ├── adapters/
   │       ├── consumers/
   │       └── mappers/
   ├── config/
   └── tests/
       ├── unit/
       └── integration/
   ```

2. **Archivos base creados:**
   - ✅ `README.md` - Documentación inicial
   - ✅ `MIGRATION_PLAN.md` - Plan de migración completo
   - ✅ `pyproject.toml` - Configuración del proyecto
   - ✅ `requirements.txt` - Dependencias básicas
   - ✅ Todos los `__init__.py` necesarios

3. **Documentación creada:**
   - ✅ `TASK_DERIVATION_SERVICE_PROPOSAL.md` (en Planning Service) - Propuesta arquitectónica completa
   - ✅ `PLANNING_SERVICE_STATE.md` (en Planning Service) - Estado actual de Planning Service

---

## 🎯 Próximos Pasos Inmediatos (Mañana)

### Fase 2: Domain Layer (Prioridad ALTA)

**Objetivo:** Mover los Value Objects de dominio desde Planning Service a Task Derivation Service.

**Tareas:**

1. **Mover `TaskNode`:**
   - **Origen:** `services/planning/planning/domain/value_objects/task_derivation/task_node.py`
   - **Destino:** `services/task-derivation/task_derivation/domain/value_objects/task_derivation/task_node.py`
   - **Acción:** Copiar archivo y actualizar imports

2. **Mover `DependencyGraph`:**
   - **Origen:** `services/planning/planning/domain/value_objects/task_derivation/dependency_graph.py`
   - **Destino:** `services/task-derivation/task_derivation/domain/value_objects/task_derivation/dependency_graph.py`
   - **Acción:** Copiar archivo y actualizar imports

3. **Mover `LLMPrompt`:**
   - **Origen:** `services/planning/planning/domain/value_objects/task_derivation/llm_prompt.py`
   - **Destino:** `services/task-derivation/task_derivation/domain/value_objects/task_derivation/llm_prompt.py`
   - **Acción:** Copiar archivo y actualizar imports

4. **Mover `TaskDerivationConfig`:**
   - **Origen:** `services/planning/planning/domain/value_objects/task_derivation/task_derivation_config.py`
   - **Destino:** `services/task-derivation/task_derivation/domain/value_objects/task_derivation/task_derivation_config.py`
   - **Acción:** Copiar archivo y actualizar imports

5. **Crear eventos de dominio:**
   - **Crear:** `task_derivation/domain/events/task_derivation_completed_event.py`
   - **Crear:** `task_derivation/domain/events/task_derivation_failed_event.py`

**Comandos útiles:**
```bash
# Copiar archivos
cp services/planning/planning/domain/value_objects/task_derivation/task_node.py \
   services/task-derivation/task_derivation/domain/value_objects/task_derivation/

cp services/planning/planning/domain/value_objects/task_derivation/dependency_graph.py \
   services/task-derivation/task_derivation/domain/value_objects/task_derivation/

cp services/planning/planning/domain/value_objects/task_derivation/llm_prompt.py \
   services/task-derivation/task_derivation/domain/value_objects/task_derivation/

cp services/planning/planning/domain/value_objects/task_derivation/task_derivation_config.py \
   services/task-derivation/task_derivation/domain/value_objects/task_derivation/
```

**Después de copiar:**
- Actualizar imports en cada archivo (cambiar `planning.domain` → `task_derivation.domain`)
- Verificar que no hay dependencias de Planning Service
- Ejecutar tests si existen

---

## 📋 Checklist Completo de Migración

### ✅ Completado
- [x] Estructura de directorios
- [x] Archivos `__init__.py`
- [x] `pyproject.toml`
- [x] `requirements.txt`
- [x] `README.md`
- [x] `MIGRATION_PLAN.md`

### 🔄 En Progreso
- [ ] **Fase 2: Domain Layer** ← **PRÓXIMO**

### ⏳ Pendiente

**Fase 3: Application Layer - Ports**
- [ ] Crear `PlanningPort` (gRPC client interface)
- [ ] Crear `ContextPort` (gRPC client interface)
- [ ] Crear `RayExecutorPort` (gRPC client interface)
- [ ] Crear `MessagingPort` (NATS interface)

**Fase 4: Infrastructure Layer - Adapters**
- [ ] Crear `PlanningServiceAdapter` (gRPC client)
- [ ] Crear `ContextServiceAdapter` (gRPC client)
- [ ] Crear `RayExecutorAdapter` (gRPC client)
- [ ] Crear `NATSMessagingAdapter` (NATS client)
- [ ] Mover `LLMTaskDerivationMapper`

**Fase 5: Application Layer - Use Cases**
- [ ] Crear `DeriveTasksUseCase`
- [ ] Crear `ProcessTaskDerivationResultUseCase`
- [ ] Crear `TaskDerivationService` (application service)

**Fase 6: Infrastructure Layer - Consumers**
- [ ] Crear `TaskDerivationRequestConsumer`
- [ ] Crear `TaskDerivationResultConsumer`

**Fase 7: Configuration**
- [ ] Mover `config/task_derivation.yaml`

**Fase 8: Planning Service Updates**
- [ ] Crear `RequestTaskDerivationUseCase`
- [ ] Simplificar `PlanApprovedConsumer`
- [ ] Remover componentes de Task Derivation

**Fase 9: Infrastructure & Deployment**
- [ ] Configurar eventos NATS
- [ ] Crear gRPC endpoints en Planning Service
- [ ] Crear Dockerfile
- [ ] Crear deployment K8s

**Fase 10: Testing**
- [ ] Mover tests unitarios
- [ ] Crear tests de integración
- [ ] Crear tests E2E

**Fase 11: Documentation**
- [ ] Crear ARCHITECTURE.md
- [ ] Actualizar documentación de Planning Service

---

## 📚 Archivos de Referencia Importantes

### Documentación Principal
- **Propuesta Arquitectónica:** `services/planning/docs/TASK_DERIVATION_SERVICE_PROPOSAL.md`
- **Plan de Migración:** `services/task-derivation/MIGRATION_PLAN.md`
- **Estado Planning Service:** `services/planning/docs/PLANNING_SERVICE_STATE.md`

### Archivos Origen (Planning Service)

**Domain VOs:**
- `services/planning/planning/domain/value_objects/task_derivation/task_node.py`
- `services/planning/planning/domain/value_objects/task_derivation/dependency_graph.py`
- `services/planning/planning/domain/value_objects/task_derivation/llm_prompt.py`
- `services/planning/planning/domain/value_objects/task_derivation/task_derivation_config.py`

**Application Layer:**
- `services/planning/planning/application/usecases/derive_tasks_from_plan_usecase.py`
- `services/planning/planning/application/services/task_derivation_result_service.py`

**Infrastructure Layer:**
- `services/planning/planning/infrastructure/consumers/plan_approved_consumer.py`
- `services/planning/planning/infrastructure/consumers/task_derivation_result_consumer.py`
- `services/planning/planning/infrastructure/adapters/ray_executor_adapter.py`
- `services/planning/planning/infrastructure/adapters/context_service_adapter.py`
- `services/planning/planning/infrastructure/mappers/llm_task_derivation_mapper.py`

**Configuration:**
- `config/task_derivation.yaml`

### Archivos Destino (Task Derivation Service)

**Domain VOs:**
- `services/task-derivation/task_derivation/domain/value_objects/task_derivation/task_node.py`
- `services/task-derivation/task_derivation/domain/value_objects/task_derivation/dependency_graph.py`
- `services/task-derivation/task_derivation/domain/value_objects/task_derivation/llm_prompt.py`
- `services/task-derivation/task_derivation/domain/value_objects/task_derivation/task_derivation_config.py`

**Application Layer:**
- `services/task-derivation/task_derivation/application/usecases/derive_tasks_usecase.py`
- `services/task-derivation/task_derivation/application/usecases/process_task_derivation_result_usecase.py`
- `services/task-derivation/task_derivation/application/services/task_derivation_service.py`

**Infrastructure Layer:**
- `services/task-derivation/task_derivation/infrastructure/consumers/task_derivation_request_consumer.py`
- `services/task-derivation/task_derivation/infrastructure/consumers/task_derivation_result_consumer.py`
- `services/task-derivation/task_derivation/infrastructure/adapters/planning_service_adapter.py`
- `services/task-derivation/task_derivation/infrastructure/adapters/context_service_adapter.py`
- `services/task-derivation/task_derivation/infrastructure/adapters/ray_executor_adapter.py`
- `services/task-derivation/task_derivation/infrastructure/adapters/nats_messaging_adapter.py`
- `services/task-derivation/task_derivation/infrastructure/mappers/llm_task_derivation_mapper.py`

**Configuration:**
- `services/task-derivation/config/task_derivation.yaml`

---

## 🔍 Decisiones Arquitectónicas Clave

### 1. Comunicación entre Servicios

**Planning Service → Task Derivation Service:**
- ✅ **Event-Driven (NATS):** `task.derivation.requested`
- Payload: `{plan_id, story_id, roles, requested_by, timestamp}`

**Task Derivation Service → Planning Service:**
- ✅ **Síncrono (gRPC):** `GetPlan(plan_id)`, `CreateTask(request)`
- Planning Service mantiene control de datos

**Task Derivation Service → Context Service:**
- ✅ **Síncrono (gRPC):** `GetContext(story_id, role, phase)`

**Task Derivation Service → Ray Executor:**
- ✅ **Síncrono (gRPC):** `SubmitTaskDerivation(prompt, role)`

### 2. Eventos Nuevos

**`task.derivation.requested`:**
- Publicado por: Planning Service
- Consumido por: Task Derivation Service
- Propósito: Trigger derivación

**`task.derivation.completed`:**
- Publicado por: Task Derivation Service
- Consumido por: Planning Service, Monitoring
- Propósito: Notificar éxito

**`task.derivation.failed`:**
- Publicado por: Task Derivation Service
- Consumido por: Planning Service, PO-UI
- Propósito: Notificar fallo

### 3. Responsabilidades

**Planning Service:**
- ✅ Solo publica evento `task.derivation.requested`
- ✅ Crea `RequestTaskDerivationUseCase` (muy simple)
- ✅ Simplifica `PlanApprovedConsumer`

**Task Derivation Service:**
- ✅ Escucha `task.derivation.requested`
- ✅ Obtiene Plan de Planning Service (gRPC)
- ✅ Obtiene Context de Context Service (gRPC)
- ✅ Envía a Ray Executor
- ✅ Procesa resultados
- ✅ Crea tasks vía Planning Service (gRPC)
- ✅ Publica eventos de resultado

---

## ⚠️ Consideraciones Importantes

### 1. Dependencias entre VOs

Al mover los VOs, verificar que:
- `TaskNode` no depende de entidades de Planning Service
- `DependencyGraph` no depende de entidades de Planning Service
- `LLMPrompt` no depende de entidades de Planning Service
- `TaskDerivationConfig` no depende de entidades de Planning Service

**Si hay dependencias:**
- Extraer a Value Objects compartidos (si aplica)
- O crear nuevos VOs en Task Derivation Service

### 2. Imports a Actualizar

Al mover archivos, actualizar imports:
- `from planning.domain...` → `from task_derivation.domain...`
- Verificar imports de Value Objects relacionados
- Verificar imports de tipos (datetime, etc.)

### 3. Tests

**Al mover VOs:**
- Mover tests correspondientes desde Planning Service
- Actualizar imports en tests
- Verificar que tests pasan

**Tests a mover:**
- `services/planning/tests/unit/domain/test_dependency_graph.py`
- Tests relacionados con `TaskNode` (si existen)

### 4. Configuración

**Al mover `task_derivation.yaml`:**
- Verificar paths relativos
- Actualizar referencias en código
- Crear `ConfigurationPort` y adapter si es necesario

---

## 🚀 Comandos Útiles para Mañana

### Setup del Entorno

```bash
# Activar venv
cd /home/tirso/ai/developents/swe-ai-fleet
source .venv/bin/activate

# Instalar Task Derivation Service (cuando esté listo)
cd services/task-derivation
pip install -e .
```

### Verificar Estructura

```bash
# Ver estructura creada
cd services/task-derivation
find . -type f -name "*.py" | head -20

# Verificar imports (después de mover archivos)
grep -r "from planning" task_derivation/
```

### Tests

```bash
# Ejecutar tests (cuando estén movidos)
cd services/task-derivation
pytest tests/ -v

# Con cobertura
pytest tests/ --cov=task_derivation --cov-report=html
```

### Linting

```bash
# Lint del código
cd services/task-derivation
ruff check . --fix
```

---

## 📝 Notas Adicionales

### Estado Actual de Planning Service

- ✅ Planning Service tiene Task Derivation implementado pero no confiable
- ✅ Usuario decidió extraer Task Derivation a servicio dedicado
- ✅ Estructura base del nuevo servicio creada
- ⏳ Pendiente: Migrar componentes

### Prioridades

1. **ALTA:** Mover Domain VOs (Fase 2)
2. **ALTA:** Crear Ports (Fase 3)
3. **MEDIA:** Crear Adapters (Fase 4)
4. **MEDIA:** Crear Use Cases (Fase 5)
5. **MEDIA:** Crear Consumers (Fase 6)
6. **BAJA:** Configuration, Deployment, Tests (Fases 7-11)

### Riesgos Identificados

1. **Dependencias circulares:** Verificar que VOs no dependan de Planning Service
2. **Tests rotos:** Actualizar imports en tests después de mover archivos
3. **Configuración:** Verificar paths y referencias en YAML
4. **gRPC endpoints:** Verificar que Planning Service tiene endpoints necesarios

---

## 🎯 Objetivo del Día (Mañana)

**Completar Fase 2: Domain Layer**

1. Mover los 4 VOs principales (TaskNode, DependencyGraph, LLMPrompt, TaskDerivationConfig)
2. Crear eventos de dominio (TaskDerivationCompletedEvent, TaskDerivationFailedEvent)
3. Actualizar imports
4. Verificar que no hay dependencias de Planning Service
5. Mover tests correspondientes
6. Ejecutar tests y verificar que pasan

**Tiempo estimado:** 2-3 horas

---

## 📞 Referencias Rápidas

**Documentos clave:**
- `services/planning/docs/TASK_DERIVATION_SERVICE_PROPOSAL.md` - Propuesta completa
- `services/task-derivation/MIGRATION_PLAN.md` - Plan detallado
- `services/planning/docs/PLANNING_SERVICE_STATE.md` - Estado actual

**Comandos git útiles:**
```bash
# Ver cambios
git status

# Ver diferencias
git diff

# Commit incremental (recomendado)
git add services/task-derivation/
git commit -m "feat: Create Task Derivation Service structure"
```

---

**Última actualización:** 2025-11-14
**Próxima sesión:** Continuar con Fase 2 (Domain Layer)

