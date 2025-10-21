# 🏛️ Hexagonal Architecture - Principios NO Negociables

**Fecha**: 20 de Octubre de 2025  
**Autor**: Tirso (Lead Architect)  
**Estado**: 📜 **DOCUMENTO NORMATIVO** - Cumplimiento Obligatorio

---

## ⚠️ IMPORTANTE: Esta Arquitectura Es de Libro

La arquitectura hexagonal implementada en este proyecto es **ejemplar** y **de libro de texto**. Ha sido cuidadosamente diseñada por el arquitecto del proyecto y debe ser **mantenida y cuidada** con el máximo rigor.

### 🎯 Propósito de Este Documento

Este documento establece los **principios NO negociables** que TODOS los desarrolladores deben seguir al trabajar en este proyecto. La arquitectura hexagonal no es opcional, es la base del proyecto.

---

## 📐 ¿Qué Es Arquitectura Hexagonal?

### Definición

Arquitectura Hexagonal (también conocida como **Ports & Adapters**) es un patrón arquitectónico que:

1. **Separa el dominio de negocio** de los detalles técnicos
2. **Invierte las dependencias** - todo apunta hacia el dominio
3. **Usa abstracciones (ports)** para comunicación entre capas
4. **Implementa adapters** que concretan los ports

### Diagrama Conceptual

```
┌─────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE                              │
│                   (Adapters - Driving)                          │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  gRPC Server, REST API, Event Handlers                    │ │
│  │  (Entry points - adaptan el mundo exterior al dominio)    │ │
│  └──────────────────────┬─────────────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          │ Llama a través de Ports
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION                                 │
│                  (Application Services)                         │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Use Cases (Deliberate, Orchestrate, etc.)                │ │
│  │  Application Services (AutoDispatchService)               │ │
│  │  (Orquestación de lógica de negocio)                     │ │
│  └──────────────────────┬─────────────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          │ Usa
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DOMAIN                                   │
│                   (Business Logic)                              │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Entities (OrchestratorStatistics, CouncilRegistry)       │ │
│  │  Value Objects (Role, TaskConstraints)                    │ │
│  │  Domain Services (Deliberate algorithm)                   │ │
│  │  Ports (Interfaces - MessagingPort, CouncilQueryPort)     │ │
│  └──────────────────────┬─────────────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          │ Implementado por
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE                              │
│                    (Adapters - Driven)                          │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  NATSMessagingAdapter, CouncilQueryAdapter                │ │
│  │  (Implementaciones concretas de infraestructura)          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎓 Principios Fundamentales (De Libro)

### 1. **Dependency Inversion**

```python
# ❌ MAL - Domain depende de Infrastructure
class DeliberateUseCase:
    def __init__(self):
        self.messaging = NATSClient()  # ← Dependencia directa de infraestructura
```

```python
# ✅ BIEN - Domain depende de abstracción
class DeliberateUseCase:
    def __init__(self, messaging: MessagingPort):  # ← Depende de Port (abstracción)
        self._messaging = messaging
```

**Regla**: El dominio NUNCA importa de infrastructure. Infrastructure implementa las interfaces (ports) definidas en domain.

---

### 2. **Ports & Adapters**

#### Port (Abstracción en Domain)

```python
# services/orchestrator/domain/ports/messaging_port.py

from abc import ABC, abstractmethod

class MessagingPort(ABC):
    """Port for messaging operations.
    
    This is an ABSTRACTION. Domain defines WHAT it needs,
    not HOW it's implemented.
    """
    
    @abstractmethod
    async def publish_event(self, event: DomainEvent) -> None:
        """Publish a domain event."""
        pass
    
    @abstractmethod
    async def subscribe(self, subject: str, handler: Callable) -> None:
        """Subscribe to events."""
        pass
```

#### Adapter (Implementación en Infrastructure)

```python
# services/orchestrator/infrastructure/adapters/nats_messaging_adapter.py

class NATSMessagingAdapter(MessagingPort):
    """Adapter implementing MessagingPort using NATS.
    
    This is an IMPLEMENTATION. Infrastructure decides HOW
    to implement the port.
    """
    
    def __init__(self, nats_client: NATS):
        self._nats = nats_client
    
    async def publish_event(self, event: DomainEvent) -> None:
        # NATS-specific implementation
        await self._nats.publish(...)
```

**Regla**: 
- **Ports** se definen en `domain/ports/`
- **Adapters** se implementan en `infrastructure/adapters/`
- Domain solo conoce Ports
- Infrastructure implementa Adapters

---

### 3. **Application Services (Facades)**

```python
# services/orchestrator/application/services/auto_dispatch_service.py

class AutoDispatchService:
    """Application Service that orchestrates use cases.
    
    This is the ORCHESTRATION layer between infrastructure
    and domain. It coordinates multiple use cases and ports.
    """
    
    def __init__(
        self,
        council_query: CouncilQueryPort,  # ← Port
        council_registry: CouncilRegistry,  # ← Domain entity
        stats: OrchestratorStatistics,  # ← Domain entity
        messaging: MessagingPort,  # ← Port
    ):
        # All dependencies injected via constructor
        pass
    
    async def dispatch_deliberations_for_plan(self, event: PlanApprovedEvent):
        # Orchestrates:
        # 1. Query via port
        # 2. Get from domain entity
        # 3. Create and execute use case
        # 4. Publish via port
        pass
```

**Regla**: 
- Application Services orquestan use cases
- NO contienen lógica de negocio
- Coordinan entre domain y infrastructure
- Simplifican la interface para handlers

---

### 4. **Clean Dependency Injection**

```python
# services/orchestrator/server.py (Composition Root)

async def serve_async():
    # 1. Create infrastructure adapters
    nats_adapter = NATSMessagingAdapter(nats_client)
    council_query_adapter = CouncilQueryAdapter(default_model="qwen")
    
    # 2. Create domain entities
    council_registry = CouncilRegistry()
    stats = OrchestratorStatistics()
    
    # 3. Create application services (inject dependencies)
    auto_dispatch_service = AutoDispatchService(
        council_query=council_query_adapter,  # Adapter
        council_registry=council_registry,  # Entity
        stats=stats,  # Entity
        messaging=nats_adapter,  # Adapter
    )
    
    # 4. Create handlers (inject services)
    planning_consumer = PlanningConsumer(
        council_query=council_query_adapter,
        messaging=nats_adapter,
        auto_dispatch_service=auto_dispatch_service,  # Service
    )
```

**Regla**: 
- Toda la inyección de dependencias ocurre en **UN solo lugar** (Composition Root)
- NO usar `new` dentro de clases (excepto value objects)
- NO usar imports dinámicos
- Todas las dependencias por constructor

---

## 🚫 Antipatrones - PROHIBIDOS

### ❌ 1. Dynamic Imports

```python
# ❌ PROHIBIDO
def handle_event(self, event):
    from services.orchestrator.application.usecases import DeliberateUseCase  # ← NO!
    use_case = DeliberateUseCase(...)
```

**Por qué está mal**:
- Rompe Dependency Inversion
- Acopla infrastructure con application
- Difícil de testear
- Oculta dependencias

**Cómo arreglarlo**:
- Inyectar use case o service por constructor
- Crear Application Service si hay orchestración compleja

---

### ❌ 2. God Classes

```python
# ❌ PROHIBIDO
class PlanningConsumer:
    async def handle_plan_approved(self, msg):
        # 100 líneas de lógica:
        # - Validación
        # - Query de councils
        # - Creación de use cases
        # - Ejecución de deliberaciones
        # - Publicación de eventos
        # ← Demasiadas responsabilidades!
```

**Por qué está mal**:
- Viola Single Responsibility Principle
- Difícil de testear
- Difícil de mantener

**Cómo arreglarlo**:
- Delegar a Application Service
- Handler solo consume y delega

---

### ❌ 3. Infrastructure en Domain

```python
# ❌ PROHIBIDO - services/orchestrator/domain/entities/statistics.py
import nats  # ← Domain NO debe importar infrastructure!

class OrchestratorStatistics:
    def publish_metrics(self):
        # Llamada directa a NATS
        await nats.publish(...)  # ← NO!
```

**Por qué está mal**:
- Domain acoplado a tecnología específica
- Imposible cambiar NATS sin tocar domain
- Viola Dependency Inversion

**Cómo arreglarlo**:
- Domain publica DomainEvents
- Infrastructure escucha y publica a NATS

---

### ❌ 4. Anemic Domain Model

```python
# ❌ PROHIBIDO
class TaskConstraints:
    rubric: dict
    architect_rubric: dict
    # ← Solo datos, sin comportamiento

class TaskConstraintsValidator:  # ← Lógica separada de datos
    def validate(self, constraints: TaskConstraints):
        # Validación aquí
```

**Por qué está mal**:
- Lógica de negocio fuera del dominio
- Datos y comportamiento separados
- No es orientado a objetos

**Cómo arreglarlo**:
- Mover comportamiento al entity/value object
```python
class TaskConstraints:
    def validate(self) -> bool:
        # Validación aquí
        pass
```

---

## ✅ Patrones Correctos - SEGUIR

### ✅ 1. Application Service Pattern

```python
# ✅ CORRECTO
class AutoDispatchService:
    """Orchestrates deliberation dispatch without business logic."""
    
    def __init__(
        self,
        council_query: CouncilQueryPort,
        council_registry: CouncilRegistry,
        stats: OrchestratorStatistics,
        messaging: MessagingPort,
    ):
        # Dependency Injection
        pass
    
    async def dispatch_deliberations_for_plan(self, event):
        # Orchestration (no business logic):
        # 1. Query via port
        # 2. Create use case
        # 3. Execute use case
        # 4. Publish via port
        pass
```

**Por qué es correcto**:
- Separa orchestración de lógica de negocio
- Dependency Injection clara
- Testeable (mock ports)
- Single Responsibility

---

### ✅ 2. Port/Adapter Pattern

```python
# ✅ CORRECTO - Domain define port
class CouncilQueryPort(ABC):
    @abstractmethod
    def has_council(self, role: str, registry: CouncilRegistry) -> bool:
        pass

# ✅ CORRECTO - Infrastructure implementa adapter
class CouncilQueryAdapter(CouncilQueryPort):
    def has_council(self, role: str, registry: CouncilRegistry) -> bool:
        try:
            return registry.has_council(role)
        except Exception:
            return False
```

**Por qué es correcto**:
- Domain define interfaz (WHAT)
- Infrastructure implementa (HOW)
- Dependency Inversion respetada
- Fácil cambiar implementación

---

### ✅ 3. Domain Events

```python
# ✅ CORRECTO - Domain publica eventos
@dataclass(frozen=True)
class DeliberationCompletedEvent(DomainEvent):
    deliberation_id: str
    story_id: str
    role: str
    timestamp: str
    
    @property
    def event_type(self) -> str:
        return "orchestration.deliberation.completed"

# ✅ CORRECTO - Use case publica via port
class DeliberateUseCase:
    async def execute(self, ...):
        results = await council.execute(...)
        
        # Publish domain event via port
        event = DeliberationCompletedEvent(...)
        await self._messaging.publish_event(event)
```

**Por qué es correcto**:
- Domain events son parte del domain
- Publicación via port (abstracción)
- Desacoplamiento entre servicios

---

## 📋 Checklist para Pull Requests

Antes de hacer merge, verificar:

### Domain Layer
- [ ] ❌ NO importa de `infrastructure`
- [ ] ❌ NO importa de `application` (excepto types)
- [ ] ✅ Define ports (interfaces) para dependencias externas
- [ ] ✅ Entities tienen comportamiento, no solo datos
- [ ] ✅ Value Objects son inmutables
- [ ] ✅ Domain Events heredan de `DomainEvent`

### Application Layer
- [ ] ❌ NO importa de `infrastructure`
- [ ] ✅ Use Cases dependen de ports, no adapters
- [ ] ✅ Application Services solo orquestan, no lógica de negocio
- [ ] ✅ Todas las dependencias por constructor

### Infrastructure Layer
- [ ] ✅ Adapters implementan ports
- [ ] ✅ Handlers delegan a Application Services
- [ ] ❌ NO dynamic imports
- [ ] ✅ Dependency Injection en Composition Root

### Tests
- [ ] ✅ Mockean ports, no implementaciones
- [ ] ✅ Verifican behavior, no implementation
- [ ] ✅ Tests de domain sin infrastructure
- [ ] ✅ Tests de infrastructure con testcontainers si necesario

---

## 📚 Estructura de Directorios (Referencia)

```
services/orchestrator/
├── domain/                          # 🔵 DOMAIN (Core Business Logic)
│   ├── entities/                    # Entities con comportamiento
│   │   ├── orchestrator_statistics.py
│   │   ├── council_registry.py
│   │   └── incoming_events.py       # Events from other services
│   ├── events/                      # Domain Events (outgoing)
│   │   ├── domain_event.py          # Base class
│   │   ├── deliberation_completed_event.py
│   │   └── plan_approved_event.py
│   ├── ports/                       # Interfaces (contracts)
│   │   ├── messaging_port.py
│   │   ├── council_query_port.py
│   │   └── deliberation_tracker_port.py
│   └── value_objects/               # Immutable values
│       ├── role.py
│       └── agent_type.py
│
├── application/                     # 🟡 APPLICATION (Orchestration)
│   ├── usecases/                    # Use cases (business flows)
│   │   ├── deliberate_usecase.py
│   │   ├── create_council_usecase.py
│   │   └── list_councils_usecase.py
│   └── services/                    # Application Services (facades)
│       └── auto_dispatch_service.py # ← Orchestrates use cases
│
├── infrastructure/                  # 🟢 INFRASTRUCTURE (Technical Details)
│   ├── adapters/                    # Port implementations
│   │   ├── nats_messaging_adapter.py
│   │   ├── council_query_adapter.py
│   │   └── environment_configuration_adapter.py
│   ├── handlers/                    # Event handlers (entry points)
│   │   ├── planning_consumer.py     # ← Delegates to services
│   │   ├── context_consumer.py
│   │   └── agent_response_consumer.py
│   ├── mappers/                     # DTO ↔ Domain mappers
│   │   ├── council_info_mapper.py
│   │   └── deliberation_status_mapper.py
│   └── dto/                         # gRPC/REST DTOs
│       └── orchestrator_dto.py
│
├── server.py                        # 🔧 COMPOSITION ROOT
└── tests/                           # 🧪 TESTS (by layer)
    ├── domain/
    ├── application/
    └── infrastructure/
```

---

## 🎯 Beneficios de Esta Arquitectura

### 1. **Testability** (Probabilidad)
- Unit tests sin dependencias externas
- Mock ports, no implementaciones
- Tests rápidos (<0.01s por test)

### 2. **Maintainability** (Mantenibilidad)
- Cambios localizados
- Bajo acoplamiento
- Alta cohesión

### 3. **Flexibility** (Flexibilidad)
- Fácil cambiar NATS por RabbitMQ
- Fácil cambiar Neo4j por PostgreSQL
- Fácil agregar nuevos adapters

### 4. **Clarity** (Claridad)
- Estructura predecible
- Responsabilidades claras
- Fácil onboarding

---

## 🔍 Ejemplos Reales en Este Proyecto

### Ejemplo 1: AutoDispatchService

**Por qué es ejemplar**:
- ✅ Application Service (orchestration)
- ✅ Dependency Injection via constructor
- ✅ Usa ports, no adapters
- ✅ No tiene lógica de negocio
- ✅ Retorna datos estructurados

### Ejemplo 2: PlanningConsumer

**Por qué es ejemplar**:
- ✅ Handler delega a service
- ✅ 10 líneas vs 70 líneas originales
- ✅ Single Responsibility (consume eventos)
- ✅ No conoce detalles de deliberación

### Ejemplo 3: CouncilQueryPort/Adapter

**Por qué es ejemplar**:
- ✅ Port define interfaz en domain
- ✅ Adapter implementa en infrastructure
- ✅ Domain no conoce CouncilRegistry implementation
- ✅ Fácil mockear en tests

---

## ⚖️ Cuando Romper las Reglas

### Regla General: **NUNCA**

Estas no son "guidelines", son **principios arquitectónicos fundamentales**.

### Excepción ÚNICA:

Si hay una razón **técnica documentada y aprobada por el arquitecto**, se puede considerar.

**Proceso**:
1. Documentar el problema
2. Proponer alternativa
3. Discutir con el equipo
4. Obtener aprobación del arquitecto (Tirso)
5. Documentar la decisión en ADR (Architecture Decision Record)

**Ejemplo válido**: Performance crítico medido y documentado

**Ejemplos NO válidos**:
- "Es más rápido así"
- "No entiendo hexagonal"
- "Es mucho código"

---

## 📖 Recursos para Aprender

### Libros
1. **"Hexagonal Architecture Explained"** - Juan Manuel Garrido
2. **"Clean Architecture"** - Robert C. Martin
3. **"Domain-Driven Design"** - Eric Evans

### Artículos
1. **"Hexagonal Architecture"** - Alistair Cockburn (original)
2. **"Ports and Adapters Pattern"** - Martin Fowler

### En Este Repositorio
1. `CLEAN_ARCHITECTURE_REFACTOR_20251020.md` - Refactor completo documentado
2. `ARCHITECTURE_CORE_VS_MICROSERVICES.md` - Separación Core vs MS
3. `EVENTS_ARCHITECTURE.md` - INCOMING vs OUTGOING events
4. `ORCHESTRATOR_HEXAGONAL_CODE_ANALYSIS.md` - Análisis completo

---

## 🎊 Conclusión

> **Esta arquitectura es de LIBRO. No es negociable. Es la base del proyecto.**

### Compromiso del Equipo:

1. **LEER** este documento antes de hacer cambios
2. **SEGUIR** los principios sin excepción
3. **REVISAR** PRs con estos criterios
4. **RECHAZAR** PRs que violen estos principios
5. **EDUCAR** a nuevos miembros del equipo

### Responsabilidad del Arquitecto:

- Mantener esta documentación actualizada
- Revisar arquitectura en cada PR importante
- Educar al equipo
- Proteger la integridad arquitectónica

---

## ✍️ Firma del Arquitecto

**Tirso** - Lead Architect  
*Esta arquitectura hexagonal es el resultado de años de experiencia y debe ser respetada y mantenida. Es lo que hace que este proyecto sea excepcional.*

---

## 📅 Historial de Revisiones

| Fecha | Versión | Cambios |
|-------|---------|---------|
| 2025-10-20 | 1.0 | Documento inicial - Principios fundamentales |

---

**Este documento es normativo. Su cumplimiento es obligatorio para todos los contribuidores.**


