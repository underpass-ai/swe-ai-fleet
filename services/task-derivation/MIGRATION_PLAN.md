# Plan de Migración: Task Derivation Service

**Fecha Inicio:** 2025-11-14
**Estado:** 🚧 En progreso

---

## 📋 Fase 1: Estructura Base (Día 1)

### ✅ Completado
- [x] Crear estructura de directorios
- [x] Crear archivos `__init__.py` base
- [x] Crear README.md

### 🔄 En Progreso
- [ ] Crear `pyproject.toml` o `setup.py`
- [ ] Configurar dependencias básicas

---

## 📋 Fase 2: Domain Layer (Día 1-2)

### Tareas
- [x] Mover `TaskNode` desde Planning Service
- [x] Mover `DependencyGraph` desde Planning Service
- [x] Mover `LLMPrompt` desde Planning Service
- [x] Mover `TaskDerivationConfig` desde Planning Service
- [x] Crear `TaskDerivationCompletedEvent`
- [x] Crear `TaskDerivationFailedEvent`

### Archivos Origen (Planning Service)
- `planning/domain/value_objects/task_derivation/task_node.py`
- `planning/domain/value_objects/task_derivation/dependency_graph.py`
- `planning/domain/value_objects/task_derivation/llm_prompt.py`
- `planning/domain/value_objects/task_derivation/task_derivation_config.py`

### Archivos Destino (Task Derivation Service)
- `task_derivation/domain/value_objects/task_derivation/task_node.py`
- `task_derivation/domain/value_objects/task_derivation/dependency_graph.py`
- `task_derivation/domain/value_objects/task_derivation/llm_prompt.py`
- `task_derivation/domain/value_objects/task_derivation/task_derivation_config.py`
- `task_derivation/domain/events/task_derivation_completed_event.py`
- `task_derivation/domain/events/task_derivation_failed_event.py`

---

## 📋 Fase 3: Application Layer - Ports (Día 2)

### Tareas
- [ ] Crear `PlanningPort` (gRPC client interface)
- [ ] Crear `ContextPort` (gRPC client interface)
- [ ] Crear `RayExecutorPort` (gRPC client interface)
- [ ] Crear `MessagingPort` (NATS interface)

### Archivos
- `task_derivation/application/ports/planning_port.py`
- `task_derivation/application/ports/context_port.py`
- `task_derivation/application/ports/ray_executor_port.py`
- `task_derivation/application/ports/messaging_port.py`

---

## 📋 Fase 4: Infrastructure Layer - Adapters (Día 2-3)

### Tareas
- [ ] Crear `PlanningServiceAdapter` (gRPC client)
- [ ] Crear `ContextServiceAdapter` (gRPC client)
- [ ] Crear `RayExecutorAdapter` (gRPC client)
- [ ] Crear `NATSMessagingAdapter` (NATS client)
- [ ] Mover `LLMTaskDerivationMapper` desde Planning Service

### Archivos Origen (Planning Service)
- `planning/infrastructure/mappers/llm_task_derivation_mapper.py`
- `planning/infrastructure/adapters/ray_executor_adapter.py`
- `planning/infrastructure/adapters/context_service_adapter.py`

### Archivos Destino (Task Derivation Service)
- `task_derivation/infrastructure/adapters/planning_service_adapter.py`
- `task_derivation/infrastructure/adapters/context_service_adapter.py`
- `task_derivation/infrastructure/adapters/ray_executor_adapter.py`
- `task_derivation/infrastructure/adapters/nats_messaging_adapter.py`
- `task_derivation/infrastructure/mappers/llm_task_derivation_mapper.py`

---

## 📋 Fase 5: Application Layer - Use Cases (Día 3-4)

### Tareas
- [ ] Crear `DeriveTasksUseCase`
- [ ] Crear `ProcessTaskDerivationResultUseCase`
- [ ] Crear `TaskDerivationService` (application service)

### Archivos Origen (Planning Service)
- `planning/application/usecases/derive_tasks_from_plan_usecase.py`
- `planning/application/services/task_derivation_result_service.py`

### Archivos Destino (Task Derivation Service)
- `task_derivation/application/usecases/derive_tasks_usecase.py`
- `task_derivation/application/usecases/process_task_derivation_result_usecase.py`
- `task_derivation/application/services/task_derivation_service.py`

---

## 📋 Fase 6: Infrastructure Layer - Consumers (Día 4)

### Tareas
- [ ] Crear `TaskDerivationRequestConsumer`
- [ ] Crear `TaskDerivationResultConsumer`

### Archivos Origen (Planning Service)
- `planning/infrastructure/consumers/plan_approved_consumer.py` (parcial)
- `planning/infrastructure/consumers/task_derivation_result_consumer.py`

### Archivos Destino (Task Derivation Service)
- `task_derivation/infrastructure/consumers/task_derivation_request_consumer.py`
- `task_derivation/infrastructure/consumers/task_derivation_result_consumer.py`

---

## 📋 Fase 7: Configuration (Día 4)

### Tareas
- [ ] Mover `config/task_derivation.yaml` a Task Derivation Service
- [ ] Crear `ConfigurationPort` y adapter

### Archivos Origen
- `config/task_derivation.yaml`

### Archivos Destino
- `task_derivation/config/task_derivation.yaml`

---

## 📋 Fase 8: Planning Service Updates (Día 5)

### Tareas
- [ ] Crear `RequestTaskDerivationUseCase` en Planning Service
- [ ] Simplificar `PlanApprovedConsumer` (solo publicar evento)
- [ ] Remover componentes de Task Derivation de Planning Service
- [ ] Actualizar imports y dependencias

### Archivos a Modificar (Planning Service)
- `planning/application/usecases/request_task_derivation_usecase.py` (nuevo)
- `planning/infrastructure/consumers/plan_approved_consumer.py` (simplificar)
- `planning/server.py` (actualizar)

### Archivos a Remover (Planning Service)
- `planning/application/usecases/derive_tasks_from_plan_usecase.py`
- `planning/application/services/task_derivation_result_service.py`
- `planning/infrastructure/consumers/task_derivation_result_consumer.py`
- `planning/infrastructure/adapters/ray_executor_adapter.py`
- `planning/infrastructure/adapters/context_service_adapter.py`
- `planning/infrastructure/mappers/llm_task_derivation_mapper.py`
- `planning/domain/value_objects/task_derivation/` (todo)

---

## 📋 Fase 9: Infrastructure & Deployment (Día 5-6)

### Tareas
- [ ] Configurar eventos NATS
- [ ] Crear gRPC endpoints en Planning Service (si no existen)
- [ ] Crear Dockerfile para Task Derivation Service
- [ ] Crear deployment K8s
- [ ] Configurar monitoring y logging

---

## 📋 Fase 10: Testing (Día 6-7)

### Tareas
- [ ] Mover tests unitarios desde Planning Service
- [ ] Crear tests de integración
- [ ] Crear tests E2E
- [ ] Validar flujo completo

---

## 📋 Fase 11: Documentation (Día 7)

### Tareas
- [ ] Crear ARCHITECTURE.md para Task Derivation Service
- [ ] Actualizar documentación de Planning Service
- [ ] Actualizar README.md principal

---

## ✅ Checklist Final

- [ ] Todos los componentes movidos
- [ ] Tests pasando
- [ ] Documentación actualizada
- [ ] Deployment configurado
- [ ] Validación en ambiente de desarrollo
- [ ] Validación en producción

---

**Última actualización:** 2025-11-14

