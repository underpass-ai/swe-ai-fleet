# Task Derivation Service

**Bounded Context:** Task Derivation
**Pattern:** DDD + Hexagonal Architecture
**Version:** v0.1.0
**Status:** 🚧 En desarrollo

---

## 🎯 Responsibility

**Task Derivation Service** es responsable de derivar tareas automáticamente desde un Plan aprobado usando LLM (vLLM).

**Core Responsibilities:**
1. Escuchar eventos `task.derivation.requested` (de Planning Service)
2. Obtener Plan de Planning Service (gRPC)
3. Obtener contexto rehidratado de Context Service (gRPC)
4. Construir prompt LLM
5. Enviar a Ray Executor para ejecución en vLLM
6. Procesar resultados del LLM
7. Crear tasks vía Planning Service (gRPC)
8. Publicar eventos de resultado

**NO es responsable de:**
- ❌ Persistir tasks (Planning Service lo hace)
- ❌ Gestionar ciclo de vida de historias (Planning Service)
- ❌ Validar permisos RBAC (Workflow Service)
- ❌ Ejecutar tasks (Orchestrator/Workflow)

---

## 🏗 Architecture

```
task_derivation/
├── domain/
│   ├── value_objects/
│   │   ├── content/        # Title, TaskDescription, DependencyReason
│   │   ├── identifiers/    # PlanId, StoryId, TaskId
│   │   ├── task_attributes/# Duration, Priority
│   ├── value_objects/
│   │   └── task_derivation/
│   │       ├── task_node.py
│   │       ├── dependency_graph.py
│   │       ├── llm_prompt.py
│   │       └── task_derivation_config.py
│   │       └── task_derivation_status.py
│   └── events/
│       ├── task_derivation_completed_event.py
│       └── task_derivation_failed_event.py
├── application/
│   ├── ports/
│   │   ├── planning_port.py
│   │   ├── context_port.py
│   │   ├── ray_executor_port.py
│   │   └── messaging_port.py
│   ├── usecases/
│   │   ├── derive_tasks_usecase.py
│   │   └── process_task_derivation_result_usecase.py
│   └── services/
│       └── task_derivation_service.py
└── infrastructure/
    ├── adapters/
    │   ├── planning_service_adapter.py
    │   ├── context_service_adapter.py
    │   ├── ray_executor_adapter.py
    │   └── nats_messaging_adapter.py
    ├── consumers/
    │   ├── task_derivation_request_consumer.py
    │   └── task_derivation_result_consumer.py
    └── mappers/
        └── llm_task_derivation_mapper.py
```

### Domain Layer Highlights

- **Value Objects:** Task derivation reuses strict VOs (identifiers, content, task attributes) to ensure immutability and validation across services. `TaskNode`, `DependencyGraph`, `LLMPrompt`, and `TaskDerivationConfig` encapsulate all derivation logic with Tell-Don't-Ask behavior.
- **Status Enum:** `TaskDerivationStatus` (StrEnum) constrains derivation outcomes to `SUCCESS` or `FAILED`, eliminating ad-hoc strings.
- **Domain Events:** `TaskDerivationCompletedEvent` and `TaskDerivationFailedEvent` broadcast immutable facts, enforcing timezone-aware timestamps, non-negative task counts, and mandatory failure reasons.

---

## 📡 Integration

### Consumes (NATS Events)

| Event | Subject | Purpose |
|-------|---------|---------|
| **task.derivation.requested** | `task.derivation.requested` | Trigger task derivation |
| **agent.response.completed** | `agent.response.completed` | Process LLM results |

### Produces (NATS Events)

| Event | Subject | Purpose |
|-------|---------|---------|
| **task.derivation.completed** | `task.derivation.completed` | Notify derivation success |
| **task.derivation.failed** | `task.derivation.failed` | Notify derivation failure |

### External Dependencies & Specs

| Adapter | Status | Spec |
|---------|--------|------|
| PlanningServiceAdapter | Pending | `specs/fleet/task_derivation/v1/task_derivation.proto` |
| ContextServiceAdapter | Pending | `specs/fleet/context/v1/context.proto` |
| RayExecutorAdapter | Pending | `specs/fleet/ray_executor/v1/ray_executor.proto` |

> All adapters will use dedicated gRPC mappers (proto ↔ domain VOs) to keep serialization out of the domain layer.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- NATS JetStream
- Planning Service (gRPC)
- Context Service (gRPC)
- Ray Executor (gRPC)

### Installation

```bash
cd services/task-derivation
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configuration

Copy `config/task_derivation.yaml` and configure:
- LLM model settings
- Task derivation constraints
- Retry strategy

### Running

```bash
python server.py
```

---

## 📚 Documentation

- `TASK_DERIVATION_SERVICE_PROPOSAL.md` - Propuesta arquitectónica completa
- `ARCHITECTURE.md` - Arquitectura detallada (pendiente)

---

**Status:** 🚧 En desarrollo - Migración desde Planning Service

