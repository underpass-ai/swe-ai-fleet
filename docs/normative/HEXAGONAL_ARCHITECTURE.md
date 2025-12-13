# Hexagonal Architecture Principles

**Version**: 2025-10-28
**Status**: Normative (Mandatory)

This document defines the **HARD requirements** for all code in the SWE AI Fleet repository. We strictly follow **Domain-Driven Design (DDD)** and **Hexagonal Architecture (Ports & Adapters)**.

---

## 0. High-Priority Rules (The "Golden Rules")

1.  **Language**: All source code, docstrings, and comments MUST be in English.
2.  **Immutability**: Domain Entities and Value Objects MUST be `@dataclass(frozen=True)`.
3.  **No Reflection**: Never use `setattr`, `getattr`, `__dict__`, or dynamic mutation.
4.  **No Serialization in Domain**: DTOs and Entities must NOT have `to_dict()` or `from_dict()`. Use Mappers.
5.  **Fail Fast**: Validate in `__post_init__`. Raise exceptions immediately for invalid state.
6.  **Dependency Injection**: All dependencies must be injected via `__init__`. No global state.

---

## 1. Layering Model

We use a strict 3-layer model. Dependencies flow **inwards**.

### 1.1 Domain Layer (The Core)
**Path**: `service/domain/` or `core/context/domain/`

-   **Contains**: Entities, Value Objects, Domain Events, Pure Business Rules.
-   **Dependencies**: NONE. Zero imports from infrastructure or application.
-   **Rules**:
    -   Entities are frozen dataclasses.
    -   No IO, no DB, no HTTP.
    -   No framework dependencies (no Pydantic, no SQLAlchemy).

```python
@dataclass(frozen=True)
class AgentId:
    value: str
    def __post_init__(self):
        if not self.value: raise ValueError("Empty ID")
```

### 1.2 Application Layer (The Orchestrator)
**Path**: `service/application/`

-   **Contains**: Use Cases, Ports (Interfaces), DTOs.
-   **Dependencies**: Domain Layer.
-   **Rules**:
    -   Defines **Ports** (Abstract Base Classes/Protocols) for what it needs.
    -   Orchestrates domain objects to fulfill a user request.
    -   **NEVER** instantiates an adapter directly.

```python
class MessagingPort(Protocol):
    async def publish(self, event: DomainEvent): ...

class ExecuteTaskUseCase:
    def __init__(self, messaging: MessagingPort): ...
```

### 1.3 Infrastructure Layer (The Adapter)
**Path**: `service/infrastructure/`

-   **Contains**: Adapters (NATS, Neo4j, Redis), Mappers, Server entry points.
-   **Dependencies**: Application Layer, Domain Layer, External Libs.
-   **Rules**:
    -   Implements the Ports defined in Application.
    -   Handles all serialization/deserialization.
    -   Converts DB rows/JSON to Domain Entities via **Mappers**.

```python
class NatsMessagingAdapter(MessagingPort):
    async def publish(self, event): ...
```

---

## 2. DTOs & Mappers

### 2.1 DTOs
-   Simple dataclasses for input/output of Use Cases.
-   **NO** logic. **NO** serialization methods.

### 2.2 Mappers
-   Live in **Infrastructure**.
-   Convert between DTOs/Entities and Infrastructure formats (Dicts, Protobufs, DB Models).
-   **Explicit mapping only**. No reflection/automappers.

---

## 3. Testing Strategy

See **[Testing Architecture](../TESTING_ARCHITECTURE.md)** for details.

-   **Unit Tests**: Test Domain and Application in isolation. Mock all Ports.
-   **Integration Tests**: ⚠️ **Removed** - Will be reimplemented. Test Adapters against real infrastructure (Dockerized).
-   **E2E Tests**: ⚠️ **Removed** - Will be reimplemented. Test the full flow via public API.

---

## 4. Code Style & Conventions

-   **Type Hints**: Mandatory for all arguments and returns.
-   **Docstrings**: Required for public methods.
-   **Linter**: Ruff (strict settings).
-   **Formatter**: Ruff.

---

## 5. Self-Check Checklist

Before submitting a PR, verify:
- [ ] Did I pollute the Domain with infrastructure imports?
- [ ] Are my entities immutable (`frozen=True`)?
- [ ] Did I avoid `to_dict`/`from_dict` in domain objects?
- [ ] Did I use Dependency Injection for all external services?
- [ ] Do I have 90% coverage for new code?

