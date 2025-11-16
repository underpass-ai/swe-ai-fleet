# 📨 Events Architecture - Orchestrator Microservice

**Fecha**: 20 de Octubre de 2025  
**Propósito**: Clarificar INCOMING vs OUTGOING events (CRITICAL)

---

## 🎯 Problema: Dos Tipos de Eventos

El Orchestrator tiene **DOS jerarquías de eventos completamente diferentes**:

```
services/orchestrator/domain/
├── entities/
│   └── incoming_events.py        ← 🔵 INCOMING (de otros microservicios)
│
└── events/
    ├── domain_event.py            ← 🟢 OUTGOING (publicados por Orchestrator)
    ├── plan_approved_event.py     ← 🟢 Ejemplo DomainEvent
    ├── deliberation_completed_event.py
    └── ...
```

### ⚠️ **CONFUSIÓN COMÚN**:

Hay **DOS clases** llamadas `PlanApprovedEvent`:
1. `services/orchestrator/domain/entities/incoming_events.py` → **INCOMING**
2. `services/orchestrator/domain/events/plan_approved_event.py` → **OUTGOING**

**¡NO SON LA MISMA CLASE!** Tienen propósitos diferentes.

---

## 🔵 INCOMING Events (`domain/entities/incoming_events.py`)

### Propósito:
**Eventos RECIBIDOS de otros microservicios** (Planning Service, Context Service, etc.)

### Características:
- ✅ **NO heredan** de `DomainEvent`
- ✅ Son **dataclasses simples** (`@dataclass(frozen=True)`)
- ✅ Representan **datos de entrada** desde NATS
- ✅ Se deserializan con `.from_dict(nats_message_data)`
- ✅ Validación estricta en constructor
- ✅ **Inmutables** (frozen=True)

### Ejemplos:

```python
# services/orchestrator/domain/entities/incoming_events.py

@dataclass(frozen=True)
class PlanApprovedEvent:
    """Event RECEIVED when Planning Service approves a plan.
    
    Origin: Planning Service → NATS → Orchestrator
    Subject: planning.plan.approved
    
    This is an INCOMING event, NOT a DomainEvent.
    """
    story_id: str
    plan_id: str
    approved_by: str
    roles: list[str]
    timestamp: str
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanApprovedEvent:
        """Deserialize from NATS message."""
        # Validation logic
        return cls(...)

@dataclass(frozen=True)
class StoryTransitionedEvent:
    """Event RECEIVED when Planning Service transitions a story.
    
    Origin: Planning Service → NATS → Orchestrator
    Subject: planning.story.transitioned
    """
    story_id: str
    from_phase: str
    to_phase: str
    timestamp: str
```

### Cuándo Usar:
- ✅ En **consumers** (handlers que reciben de NATS)
- ✅ Para **deserializar mensajes** de otros servicios
- ✅ En **tests de integración** que simulan eventos externos

### Ejemplo de Uso:

```python
# services/orchestrator/infrastructure/handlers/planning_consumer.py

from services.orchestrator.domain.entities import PlanApprovedEvent  # ← INCOMING

async def _handle_plan_approved(self, msg):
    # Deserialize INCOMING event from Planning Service
    event_data = msg.data if isinstance(msg.data, dict) else json.loads(msg.data)
    event = PlanApprovedEvent.from_dict(event_data)
    
    # Process the external event
    logger.info(f"Received plan approval from Planning Service: {event.plan_id}")
```

---

## 🟢 OUTGOING Events (`domain/events/*.py`)

### Propósito:
**Eventos PUBLICADOS por el Orchestrator** hacia otros microservicios

### Características:
- ✅ **Heredan** de `DomainEvent` (abstract base class)
- ✅ Implementan DDD Event Sourcing pattern
- ✅ Tienen `event_type` property (para routing)
- ✅ Se serializan con `.to_dict()` antes de publicar
- ✅ Representan **domain events del Orchestrator**
- ✅ **Inmutables** (frozen=True)

### Base Class:

```python
# services/orchestrator/domain/events/domain_event.py

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class DomainEvent(ABC):
    """Abstract base class for all domain events.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Named in past tense (what happened)
    - Contains all data needed to understand what happened
    - Has event_type for routing/filtering
    """
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Return the event type identifier (e.g., 'orchestration.plan.approved')."""
        pass
    
    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization/publishing."""
        pass
```

### Ejemplos:

```python
# services/orchestrator/domain/events/plan_approved_event.py

from .domain_event import DomainEvent

@dataclass(frozen=True)
class PlanApprovedEvent(DomainEvent):
    """Event PUBLISHED when Orchestrator approves a plan internally.
    
    Origin: Orchestrator → NATS → Other Services
    Subject: orchestration.plan.approved
    
    This is an OUTGOING DomainEvent.
    """
    story_id: str
    plan_id: str
    approved_by: str
    roles: list[str]
    timestamp: str
    
    @property
    def event_type(self) -> str:
        return "orchestration.plan.approved"
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize for publishing to NATS."""
        return {
            "event_type": self.event_type,
            "story_id": self.story_id,
            "plan_id": self.plan_id,
            "approved_by": self.approved_by,
            "roles": self.roles,
            "timestamp": self.timestamp,
        }


# services/orchestrator/domain/events/deliberation_completed_event.py

@dataclass(frozen=True)
class DeliberationCompletedEvent(DomainEvent):
    """Event PUBLISHED when a deliberation finishes.
    
    Origin: Orchestrator → NATS → Planning/Monitoring Services
    Subject: orchestration.deliberation.completed
    """
    deliberation_id: str
    story_id: str
    task_id: str
    role: str
    num_proposals: int
    duration_ms: int
    timestamp: str
    
    @property
    def event_type(self) -> str:
        return "orchestration.deliberation.completed"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "deliberation_id": self.deliberation_id,
            "story_id": self.story_id,
            "task_id": self.task_id,
            "role": self.role,
            "num_proposals": self.num_proposals,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }
```

### Cuándo Usar:
- ✅ En **use cases** que publican eventos (DeliberateUseCase, etc.)
- ✅ Para **publicar eventos** a NATS via MessagingPort
- ✅ En **tests unitarios** de use cases

### Ejemplo de Uso:

```python
# services/orchestrator/application/usecases/deliberate_usecase.py

from services.orchestrator.domain.events import DeliberationCompletedEvent  # ← OUTGOING

class DeliberateUseCase:
    async def execute(self, council, role, task_description, ...):
        # Execute deliberation
        results = await council.execute(task_description, constraints)
        
        # Create OUTGOING domain event
        event = DeliberationCompletedEvent(
            deliberation_id=str(uuid.uuid4()),
            story_id=story_id,
            task_id=task_id,
            role=role,
            num_proposals=len(results),
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        # Publish to NATS for other services to consume
        if self._messaging:
            await self._messaging.publish_event(event)
```

---

## 🔄 Event Flow Completo

### Escenario: Plan Approval Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Planning Service (External)                                  │
│    • User approves plan in UI                                   │
│    • Planning creates plan.approved event                       │
│    • Publishes to NATS: planning.plan.approved                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ NATS Message
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Orchestrator: PlanningConsumer (INCOMING)                    │
│    from domain.entities import PlanApprovedEvent  # ← INCOMING  │
│                                                                  │
│    event = PlanApprovedEvent.from_dict(msg.data)                │
│    # Process: Trigger deliberations for each role               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ Calls DeliberateUseCase
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Orchestrator: DeliberateUseCase (OUTGOING)                   │
│    from domain.events import DeliberationCompletedEvent # OUTGOING│
│                                                                  │
│    results = await council.execute(...)                         │
│                                                                  │
│    event = DeliberationCompletedEvent(...)  # ← Create OUTGOING │
│    await messaging.publish_event(event)     # ← Publish to NATS │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ NATS Message
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Monitoring Service (External)                                │
│    • Consumes orchestration.deliberation.completed              │
│    • Updates dashboard with metrics                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Reglas de Oro

### 1. **INCOMING Events** (`domain/entities/incoming_events.py`)

| Aspecto | Valor |
|---------|-------|
| **Herencia** | ❌ NO hereda de DomainEvent |
| **Propósito** | Deserializar mensajes de otros servicios |
| **Dónde se usa** | Consumers (handlers) |
| **Método clave** | `.from_dict()` (deserialize) |
| **Dirección** | Otros Services → NATS → Orchestrator |

### 2. **OUTGOING Events** (`domain/events/*.py`)

| Aspecto | Valor |
|---------|-------|
| **Herencia** | ✅ Hereda de `DomainEvent` |
| **Propósito** | Publicar eventos del dominio |
| **Dónde se usa** | Use Cases |
| **Método clave** | `.to_dict()` (serialize) |
| **Dirección** | Orchestrator → NATS → Otros Services |

---

## 🚨 Errores Comunes

### ❌ Error 1: Usar DomainEvent en Consumer

```python
# ❌ MAL - No usar DomainEvent en consumer
from services.orchestrator.domain.events import PlanApprovedEvent  # OUTGOING

async def _handle_plan_approved(self, msg):
    event = PlanApprovedEvent.from_dict(msg.data)  # ❌ NO tiene from_dict!
```

**Fix**:
```python
# ✅ BIEN - Usar incoming event en consumer
from services.orchestrator.domain.entities import PlanApprovedEvent  # INCOMING

async def _handle_plan_approved(self, msg):
    event = PlanApprovedEvent.from_dict(msg.data)  # ✅ Tiene from_dict
```

---

### ❌ Error 2: Publicar Incoming Event

```python
# ❌ MAL - No publicar incoming event
from services.orchestrator.domain.entities import PlanApprovedEvent  # INCOMING

async def execute(self, ...):
    event = PlanApprovedEvent(...)
    await messaging.publish_event(event)  # ❌ No es DomainEvent!
```

**Fix**:
```python
# ✅ BIEN - Publicar DomainEvent
from services.orchestrator.domain.events import DeliberationCompletedEvent  # OUTGOING

async def execute(self, ...):
    event = DeliberationCompletedEvent(...)
    await messaging.publish_event(event)  # ✅ Es DomainEvent
```

---

### ❌ Error 3: Confundir Imports en Tests

```python
# ❌ MAL - Usar evento incorrecto en test
from services.orchestrator.domain.events import PlanApprovedEvent  # OUTGOING

def test_planning_consumer():
    event = PlanApprovedEvent(...)  # ❌ Este es OUTGOING, consumer necesita INCOMING
    await consumer._handle_plan_approved(mock_msg)
```

**Fix**:
```python
# ✅ BIEN - Usar incoming event en test de consumer
from services.orchestrator.domain.entities import PlanApprovedEvent  # INCOMING

def test_planning_consumer():
    event = PlanApprovedEvent(...)  # ✅ Este es INCOMING
    mock_msg.data = event.to_dict()
    await consumer._handle_plan_approved(mock_msg)
```

---

## 📊 Tabla de Referencia Rápida

| Evento | Ubicación | Tipo | Usa en | Métodos |
|--------|-----------|------|--------|---------|
| `PlanApprovedEvent` | `entities/incoming_events.py` | INCOMING | Consumers | `.from_dict()` |
| `PlanApprovedEvent` | `events/plan_approved_event.py` | OUTGOING | Use Cases | `.to_dict()`, `.event_type` |
| `StoryTransitionedEvent` | `entities/incoming_events.py` | INCOMING | Consumers | `.from_dict()` |
| `DeliberationCompletedEvent` | `events/` | OUTGOING | Use Cases | `.to_dict()`, `.event_type` |
| `AgentResponseEvent` | `entities/incoming_events.py` | INCOMING | Consumers | `.from_dict()` |

---

## 🎯 Checklist para Developers

Cuando trabajes con eventos:

### Si estás en un **Consumer** (handler):
- [ ] Importar de `domain.entities` (INCOMING)
- [ ] Deserializar con `.from_dict(msg.data)`
- [ ] Procesar evento externo
- [ ] Publicar DomainEvents si es necesario (via use cases)

### Si estás en un **Use Case**:
- [ ] Importar de `domain.events` (OUTGOING)
- [ ] Crear instancia de DomainEvent
- [ ] Serializar con `.to_dict()`
- [ ] Publicar via `MessagingPort.publish_event()`

### Si estás escribiendo **Tests**:
- [ ] ¿Test de consumer? → Usar INCOMING events
- [ ] ¿Test de use case? → Usar OUTGOING events (DomainEvents)
- [ ] Mock `MessagingPort` para verificar publicación

---

## 🏗️ Arquitectura Hexagonal Aplicada

```
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                        │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Use Cases (Orchestrate, Deliberate, etc.)             │ │
│  │ • Usan OUTGOING events (DomainEvents)                 │ │
│  │ • Publican via MessagingPort                          │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
          Publishes DomainEvents via Port
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                       │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Handlers/Consumers (PlanningConsumer, etc.)           │ │
│  │ • Reciben INCOMING events de NATS                     │ │
│  │ • Deserializan con from_dict()                        │ │
│  │ • Llaman Use Cases                                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Adapters (NATSMessagingAdapter)                       │ │
│  │ • Implementan MessagingPort                           │ │
│  │ • Serializan DomainEvents con to_dict()               │ │
│  │ • Publican a NATS                                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Conclusión

### La Verdad Absoluta:

1. **INCOMING Events** = De otros servicios hacia Orchestrator
   - No heredan DomainEvent
   - Se deserializan con `.from_dict()`
   - Ubicación: `domain/entities/incoming_events.py`

2. **OUTGOING Events** = De Orchestrator hacia otros servicios
   - Heredan `DomainEvent`
   - Se serializan con `.to_dict()`
   - Ubicación: `domain/events/*.py`

3. **Pueden tener el mismo nombre** pero son clases diferentes con propósitos diferentes

4. **Hexagonal Architecture**:
   - Consumers usan INCOMING (infrastructure → domain)
   - Use Cases usan OUTGOING (domain → infrastructure)

**¡Este patrón es CRÍTICO para mantener la separación de concerns en hexagonal architecture!**


