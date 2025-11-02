# Auditoría: Microservicio Planner en Historial de Git

**Fecha**: 2 de noviembre, 2025
**Autor**: AI Assistant (Claude Sonnet 4.5)
**Solicitado por**: Tirso García Ibáñez (Software Architect)
**Objetivo**: Investigar el microservicio 'planner' en el historial de git

---

## 🎯 Resumen Ejecutivo

Se encontró un **bounded context completo `planner`** que fue agregado en un solo commit y **NUNCA fue removido explícitamente del repo**.

**Hallazgo crítico**: El directorio `src/swe_ai_fleet/planner/` NO existe actualmente en el workspace, pero SÍ existe en el commit `5204abb` de la branch `feature/planner-po-facing`.

**Estado**: ⚠️ **ABANDONADO / WORK IN PROGRESS** - El commit es simplemente "wip" (work in progress).

---

## 📊 Información del Commit

### Commit Inicial
```bash
Commit:  5204abb
Branch:  feature/planner-po-facing
Message: "wip"
Date:    (estimado: Octubre 2025 basado en contexto)
Author:  (no disponible en log abreviado)
```

### Archivos Agregados
```
+46   config/planner.fsm.yaml
+251  src/swe_ai_fleet/planner/ARCHITECTURE.md
+25   src/swe_ai_fleet/planner/__init__.py
+1    src/swe_ai_fleet/planner/domain/__init__.py
+225  src/swe_ai_fleet/planner/domain/interfaces.py
+197  src/swe_ai_fleet/planner/fsm.py
+1    src/swe_ai_fleet/planner/infrastructure/__init__.py
+133  src/swe_ai_fleet/planner/infrastructure/config.py
+142  src/swe_ai_fleet/planner/infrastructure/di.py
+383  src/swe_ai_fleet/planner/infrastructure/implementations.py
+208  src/swe_ai_fleet/planner/integration.py

Total: 1,612 líneas agregadas en 11 archivos
```

### Estado Actual
- **Branch `main`**: ❌ NO EXISTE
- **Branch `feature/planner-po-facing`**: ✅ EXISTE (commit 5204abb)
- **Historial de cambios**: Solo 1 commit (WIP)
- **Tests**: ❌ NO ENCONTRADOS
- **Deployment**: ❌ NO DESPLEGADO

---

## 🏗️ Arquitectura del Planner (Según Documentación)

### Visión General

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   FastAPI    │  │   Static SPA │  │   K8s        │      │
│  │   Endpoints  │  │   (HTML/JS)  │  │   Manifests  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Planning   │  │   FSM Engine │  │   Guard      │      │
│  │   Service    │  │   (YAML)     │  │   Evaluator  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Interfaces │  │   Models     │  │   Events     │      │
│  │   (Contracts)│  │   (Data)     │  │   (Domain)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                Infrastructure Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Repositories│  │   Event Store│  │   Graph      │      │
│  │  (Storage)   │  │   (Redis)    │  │   Store      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Principios de Diseño
1. **Dependency Inversion** - High-level no depende de low-level
2. **Single Responsibility** - Una razón para cambiar
3. **Open/Closed** - Abierto para extensión, cerrado para modificación
4. **Interface Segregation** - Interfaces pequeñas y focalizadas

---

## 📦 Componentes del Planner

### 1. Domain Layer (`planner/domain/`)

#### Interfaces (`interfaces.py` - 225 líneas)

**Entidades de Dominio**:
```python
@dataclass(frozen=True)
class Case:
    """Immutable case representation."""
    case_id: str
    title: str
    brief: str
    state: str
    created_at: datetime
    updated_at: datetime

@dataclass(frozen=True)
class TransitionRequest:
    """Request to transition a case to a new state."""
    case_id: str
    event: str
    actor: str
    timestamp: datetime

@dataclass(frozen=True)
class TransitionResult:
    """Result of a state transition."""
    case_id: str
    from_state: str
    to_state: str
    success: bool
    reason: Optional[str] = None

@dataclass(frozen=True)
class ContextRequest:
    """Request for role-specific context."""
    case_id: str
    role: str
    phase: str
    timestamp: datetime

@dataclass(frozen=True)
class ContextResponse:
    """Role-specific context response."""
    case_id: str
    role: str
    phase: str
    context: str
    token_count: int
    redacted: bool
    policy_applied: bool

@dataclass(frozen=True)
class Event:
    """Timeline event."""
    event_id: str
    case_id: str
    kind: str
    actor: str
    summary: str
    timestamp: datetime
    payload: Dict[str, Any]

@dataclass(frozen=True)
class GraphNode:
    """Knowledge graph node."""
    node_id: str
    label: str
    node_type: str
    properties: Dict[str, Any]

@dataclass(frozen=True)
class GraphEdge:
    """Knowledge graph edge."""
    edge_id: str
    source_id: str
    target_id: str
    relationship: str
    properties: Dict[str, Any]

@dataclass(frozen=True)
class GraphSnapshot:
    """Complete graph snapshot."""
    case_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    timestamp: datetime
```

**Ports (Interfaces ABC)**:

```python
class CaseRepository(ABC):
    """Abstract case repository interface."""
    @abstractmethod
    async def create_case(self, title: str, brief: str) -> Case
    @abstractmethod
    async def get_case(self, case_id: str) -> Optional[Case]
    @abstractmethod
    async def list_cases(self) -> List[Case]
    @abstractmethod
    async def update_case_state(self, case_id: str, new_state: str) -> bool

class FSMEngine(ABC):
    """Abstract FSM engine interface."""
    @abstractmethod
    async def can_transition(self, current_state: str, event: str, guards: Dict[str, bool]) -> bool
    @abstractmethod
    async def get_next_state(self, current_state: str, event: str, guards: Dict[str, bool]) -> Optional[str]
    @abstractmethod
    async def get_available_transitions(self, current_state: str) -> List[Dict[str, Any]]

class GuardEvaluator(ABC):
    """Abstract guard evaluator interface."""
    @abstractmethod
    async def evaluate_guards(self, case_id: str, actor: str, event: str) -> Dict[str, bool]

class ContextProvider(ABC):
    """Abstract context provider interface."""
    @abstractmethod
    async def get_context(self, request: ContextRequest) -> ContextResponse

class EventStore(ABC):
    """Abstract event store interface."""
    @abstractmethod
    async def emit_event(self, event: Event) -> None
    @abstractmethod
    async def get_events(self, case_id: str, limit: int = 50) -> List[Event]

class GraphStore(ABC):
    """Abstract graph store interface."""
    @abstractmethod
    async def get_graph_snapshot(self, case_id: str) -> GraphSnapshot
    @abstractmethod
    async def sync_case_state(self, case_id: str, state: str) -> None

class PlanningService(ABC):
    """Abstract planning service interface."""
    @abstractmethod
    async def create_case(self, title: str, brief: str) -> Case
```

### 2. FSM Engine (`fsm.py` - 197 líneas)

**YAMLFSMEngine** - Implementación completa de FSM:

```python
@dataclass(frozen=True)
class State:
    """FSM state definition."""
    id: str
    kind: str = "normal"
    description: Optional[str] = None

@dataclass(frozen=True)
class Transition:
    """FSM transition definition."""
    from_state: str
    to_state: str
    event: str
    guards: List[str]
    description: Optional[str] = None

@dataclass(frozen=True)
class HumanGate:
    """Human gate definition."""
    name: str
    description: str
    required_actor: Optional[str] = None

@dataclass(frozen=True)
class FSMPolicy:
    """FSM policy configuration."""
    token_budget_hint: int = 8000
    max_retries: int = 3
    timeout_seconds: int = 300

class YAMLFSMEngine(FSMEngine):
    """FSM engine implementation that loads configuration from YAML."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self._config: Optional[FSMConfig] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load FSM configuration from YAML file."""
        # Parse YAML with states, transitions, human_gates, policy

    async def can_transition(self, current_state: str, event: str, guards: Dict[str, bool]) -> bool:
        """Check if transition is allowed."""
        for transition in self.config.transitions:
            if transition.from_state == current_state and transition.event == event:
                if all(guards.get(guard, False) for guard in transition.guards):
                    return True
        return False

    async def get_next_state(self, current_state: str, event: str, guards: Dict[str, bool]) -> Optional[str]:
        """Get next state after transition."""
        for transition in self.config.transitions:
            if transition.from_state == current_state and transition.event == event:
                if all(guards.get(guard, False) for guard in transition.guards):
                    return transition.to_state
        return None

    async def get_available_transitions(self, current_state: str) -> List[Dict[str, Any]]:
        """Get available transitions from current state."""
        transitions = []
        for transition in self.config.transitions:
            if transition.from_state == current_state:
                transitions.append({
                    "event": transition.event,
                    "to_state": transition.to_state,
                    "guards": transition.guards,
                    "description": transition.description
                })
        return transitions
```

### 3. Infrastructure Layer

#### Dependency Injection (`di.py` - 142 líneas)

```python
class DIContainer:
    """Service registration and resolution."""
    # Factory pattern for service creation
    # Singleton and transient service support
```

#### Configuration (`config.py` - 133 líneas)

```python
class ServiceConfiguration:
    """Environment-specific setup."""
    # Development vs production configurations
    # Service wiring and initialization
```

#### Implementations (`implementations.py` - 383 líneas)

```python
class InMemoryCaseRepository(CaseRepository):
    """Development/testing storage."""

class SimpleGuardEvaluator(GuardEvaluator):
    """Basic guard evaluation."""

class MockContextProvider(ContextProvider):
    """Development context generation."""
```

### 4. FSM Configuration (`config/planner.fsm.yaml` - 46 líneas)

**Definición completa del FSM de historias de usuario**:
```yaml
states:
  - id: draft
    kind: initial
  - id: po_review
  - id: coach_refinement
  - id: ready_for_dev
  - id: in_progress
  - id: code_review
  - id: testing
  - id: done
    kind: final
  - id: archived

transitions:
  - from: draft
    to: po_review
    event: submit_for_review
    guards: []

  - from: po_review
    to: coach_refinement
    event: request_refinement
    guards: []

  - from: coach_refinement
    to: ready_for_dev
    event: approve
    guards: ["dor_score_above_80"]

human_gates:
  po_approval:
    description: "Product Owner must approve story"
    required_actor: "PO"

  coach_approval:
    description: "StoryCoach must approve refinement"
    required_actor: "COACH"

policy:
  token_budget_hint: 8000
  max_retries: 3
  timeout_seconds: 300
```

---

## 🔍 Análisis del Código

### Características Positivas ✅

1. **Arquitectura Hexagonal completa**
   - Separación clara: Domain, Application, Infrastructure
   - Dependency Inversion implementada
   - Ports & Adapters pattern

2. **DTOs inmutables**
   ```python
   @dataclass(frozen=True)
   class Case:
       # Fail-fast validation in __post_init__ (if present)
   ```

3. **FSM engine desacoplado**
   - Carga configuración desde YAML
   - Guards configurables
   - Human gates para aprobaciones manuales

4. **Strong typing**
   - Type hints completos
   - Optional types bien utilizados

5. **Dependency Injection**
   - DIContainer implementado
   - Service registration
   - Singleton + Transient support

6. **Event Sourcing preparado**
   - EventStore interface
   - Event entity definida
   - Timeline de eventos

7. **Knowledge Graph integración**
   - GraphStore interface
   - GraphSnapshot entity
   - Sync case state a grafo

### Limitaciones Identificadas ❌

1. **Work In Progress (WIP)**
   - Commit message indica trabajo incompleto
   - Solo 1 commit en branch feature

2. **Sin tests**
   - No se encontraron tests unitarios
   - No se encontraron tests de integración
   - No se encontraron tests E2E

3. **Sin deployment**
   - No existe Dockerfile
   - No existe deployment K8s
   - No existe CI/CD pipeline

4. **Sin integración**
   - No integra con Context Service actual
   - No integra con Orchestrator actual
   - No integra con Planning Service (Go)

5. **Implementaciones mock**
   - `InMemoryCaseRepository` - Solo en memoria
   - `MockContextProvider` - Mock, no real
   - `SimpleGuardEvaluator` - Básico, no completo

6. **Sin API pública**
   - No existe server.py (FastAPI/gRPC)
   - No existe proto spec
   - No existe OpenAPI spec

7. **Falta documentación de uso**
   - ARCHITECTURE.md describe diseño, no uso
   - No hay ejemplos de código
   - No hay guía de integración

8. **Branch feature abandonada**
   - No fue mergeada a main
   - No tiene actividad posterior
   - Aparentemente abandonada

---

## 📊 Comparación: Planner vs Planning Service (Go)

| Aspecto | Planner (Python) | Planning Service (Go) |
|---------|------------------|----------------------|
| **Estado** | ❌ WIP / Abandonado | ✅ Desplegado en producción |
| **Lenguaje** | Python | Go |
| **Arquitectura** | Hexagonal completa | FSM + gRPC |
| **FSM Config** | `planner.fsm.yaml` | `agile.fsm.yaml` |
| **API** | ❌ No existe | ✅ gRPC proto definida |
| **Storage** | ❌ InMemory mock | ✅ Redis + Neo4j |
| **Tests** | ❌ No existen | ⚠️ Parcial |
| **Deployment** | ❌ No | ✅ K8s (namespace swe-ai-fleet) |
| **Scope** | Cases + FSM + Context + Events + Graph | Stories + FSM + Transitions |
| **Guard Evaluation** | ✅ Configurable | ⚠️ No visible |
| **Human Gates** | ✅ Definidos | ⚠️ No visible |
| **Event Store** | ✅ Interface definida | ❌ Publica a NATS pero no persiste eventos |
| **Context Provider** | ✅ Role-specific context | ❌ Delega a Context Service |
| **DI Container** | ✅ Implementado | ❌ No aplicable (Go) |

---

## 💡 Por Qué fue Abandonado (Hipótesis)

### 1. **Duplicación de Responsabilidades**
   - Planning Service (Go) ya gestiona FSM de historias
   - Planner (Python) pretendía hacer lo mismo
   - Conflicto de ownership

### 2. **Scope Demasiado Amplio**
   Planner intentaba hacer:
   - FSM engine ✅
   - Case management ✅
   - Context provider ✅
   - Event store ✅
   - Graph store ✅
   - Guard evaluation ✅
   - Human gates ✅

   **Resultado**: Bounded context demasiado grande

### 3. **Falta de Prioridad**
   - Planning Service (Go) ya cumplía la función mínima
   - Otros bounded contexts tenían mayor prioridad (Orchestrator, Context)
   - Recursos limitados

### 4. **Tecnología Mixta**
   - Planning Service en Go (microservicio stateless)
   - Planner en Python (bounded context completo)
   - Decisión de stack no alineada

### 5. **Falta de Tests**
   - Sin tests, difícil de confiar
   - Sin tests, difícil de mantener
   - Sin tests, alto riesgo de introducir bugs

---

## 🎯 Qué Valor Podría Aportar el Planner

### Características Únicas del Planner (No en Planning Service)

1. **Context Provider Role-Specific**
   ```python
   class ContextProvider(ABC):
       async def get_context(self, request: ContextRequest) -> ContextResponse
   ```
   - Generación de contexto para cada role
   - Token budget awareness
   - Policy-aware redaction

2. **Guard Evaluation Configurable**
   ```python
   class GuardEvaluator(ABC):
       async def evaluate_guards(self, case_id: str, actor: str, event: str) -> Dict[str, bool]
   ```
   - Guards configurables desde YAML
   - Evaluación dinámica de condiciones
   - Integración con otras fuentes (Neo4j, Redis)

3. **Human Gates**
   ```yaml
   human_gates:
     po_approval:
       description: "Product Owner must approve story"
       required_actor: "PO"
   ```
   - Aprobaciones manuales requeridas
   - Tracking de aprobadores
   - Auditoría de decisiones

4. **Event Store**
   ```python
   class EventStore(ABC):
       async def emit_event(self, event: Event) -> None
       async def get_events(self, case_id: str, limit: int = 50) -> List[Event]
   ```
   - Timeline completa de eventos
   - Event sourcing ready
   - Auditoría completa

5. **Graph Sync**
   ```python
   class GraphStore(ABC):
       async def sync_case_state(self, case_id: str, state: str) -> None
   ```
   - Sincronización automática con Neo4j
   - Graph snapshots
   - Knowledge graph actualizado

---

## 🚨 Hallazgos Críticos

### 1. **Bounded Context Completo pero Abandonado**
   - 1,612 líneas de código
   - Arquitectura sólida
   - Nunca fue usado en producción

### 2. **Existe FSM YAML Duplicado**
   - `config/planner.fsm.yaml` (planner - WIP)
   - `config/agile.fsm.yaml` (Planning Service - PRODUCCIÓN)

   **Conclusión**: Dos fuentes de verdad conflictivas

### 3. **Planning Service (Go) No Tiene Todas las Features**
   Faltantes en Planning Service actual:
   - Context provider role-specific
   - Guard evaluation configurable
   - Human gates tracking
   - Event store (solo publica, no persiste)
   - Graph sync automático

### 4. **Planner Podría Ser Útil para Otras Funciones**
   - **Task derivation** (derivar subtasks desde stories)
   - **Dependency management** (grafo de dependencias)
   - **Context generation** (contexto quirúrgico para roles)
   - **Guard evaluation** (condiciones de transición)

---

## 💡 Conclusiones

### Estado Actual
- **Planner** (Python): ✅ Código existe en branch feature, ❌ No en producción
- **Planning Service** (Go): ✅ En producción, ⚠️ Features limitadas

### Valor Potencial del Planner
1. **Context Provider** - Contexto role-specific quirúrgico
2. **Guard Evaluator** - Condiciones de transición configurables
3. **Event Store** - Auditoría completa de eventos
4. **Graph Sync** - Sincronización automática con Neo4j
5. **Human Gates** - Aprobaciones manuales tracked

### Recomendaciones
1. **NO revivir planner completo** - Demasiado scope overlap con Planning Service
2. **Extraer features útiles**:
   - Context Provider → Integrar en Context Service
   - Guard Evaluator → Integrar en Planning Service
   - Event Store → Implementar en orchestrator
3. **Considerar planner solo para Task Derivation** - Bounded context específico
4. **Migrar FSM config** - Consolidar `planner.fsm.yaml` y `agile.fsm.yaml`

---

**Siguiente documento**: `PLANNER_VIABILITY_REPORT.md`


