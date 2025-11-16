# Session Rehydration - Diagrama de Secuencia

**Fecha**: November 8, 2025
**Componente**: SessionRehydrationApplicationService
**Propósito**: Ensamblar contexto completo para agentes basado en roles

---

## 🎯 Flujo Completo

```mermaid
sequenceDiagram
    participant Client as Cliente<br/>(gRPC Handler)
    participant AppService as SessionRehydration<br/>ApplicationService
    participant PlanningPort as PlanningReadPort<br/>(Redis/Valkey)
    participant GraphPort as DecisionGraphReadPort<br/>(Neo4j)
    participant Indexer as DataIndexer<br/>(Domain Service)
    participant Selector as DecisionSelector<br/>(Domain Service)
    participant Impact as ImpactCalculator<br/>(Domain Service)
    participant TokenCalc as TokenBudgetCalculator<br/>(Domain Service)
    participant Mapper as StoryHeaderMapper<br/>(Infrastructure)

    Note over Client,TokenCalc: STEP 1: Validation & Data Fetching

    Client->>AppService: rehydrate_session(req)
    activate AppService

    Note over AppService: Validate request
    AppService->>PlanningPort: get_case_spec(case_id)
    activate PlanningPort
    PlanningPort-->>AppService: StorySpec | None
    deactivate PlanningPort

    alt Story not found
        AppService-->>Client: ValueError("Story spec not found")
    end

    Note over AppService,GraphPort: STEP 2: Fetch from both data sources

    par Fetch from Neo4j
        AppService->>GraphPort: get_plan_by_case(case_id)
        activate GraphPort
        GraphPort-->>AppService: Plan
        deactivate GraphPort

        AppService->>GraphPort: list_decisions(case_id)
        activate GraphPort
        GraphPort-->>AppService: list[DecisionNode]
        deactivate GraphPort

        AppService->>GraphPort: list_decision_dependencies(case_id)
        activate GraphPort
        GraphPort-->>AppService: list[DecisionEdges]
        deactivate GraphPort

        AppService->>GraphPort: list_decision_impacts(case_id)
        activate GraphPort
        GraphPort-->>AppService: list[tuple[str, TaskNode]]
        deactivate GraphPort
    and Fetch from Redis
        AppService->>PlanningPort: get_plan_draft(case_id)
        activate PlanningPort
        PlanningPort-->>AppService: PlanVersion
        deactivate PlanningPort

        opt If include_timeline
            AppService->>PlanningPort: get_planning_events(case_id, count)
            activate PlanningPort
            PlanningPort-->>AppService: list[PlanningEvent]
            deactivate PlanningPort
        end
    end

    Note over AppService,Indexer: STEP 3: Index data for fast lookups

    AppService->>Indexer: index(plan, decisions, deps, impacts)
    activate Indexer
    Note over Indexer: Build indices:<br/>- tasks_by_role<br/>- decisions_by_id<br/>- dependencies_by_source<br/>- impacts_by_decision
    Indexer-->>AppService: IndexedStoryData
    deactivate Indexer

    Note over AppService,Mapper: STEP 4: Build common headers

    AppService->>Mapper: from_spec(spec)
    activate Mapper
    Mapper-->>AppService: StoryHeader (entity)
    deactivate Mapper

    Note over AppService: plan_header = PlanHeader.from_sources()

    Note over AppService,TokenCalc: STEP 5: Build pack for EACH role

    loop For each role in req.roles
        Note over AppService: Validate role (fail-fast)

        rect rgb(240, 240, 250)
            Note over AppService,TokenCalc: Build pack for role_enum

            Note over AppService: Filter tasks for role

            AppService->>Selector: select_for_role(tasks, impacts, decisions)
            activate Selector
            Note over Selector: Find decisions impacting<br/>this role's tasks
            Selector-->>AppService: list[DecisionNode]
            deactivate Selector

            Note over AppService: decision_relations = DecisionRelationList.build()

            AppService->>Impact: calculate_for_role(decisions, impacts, role)
            activate Impact
            Note over Impact: Filter impacted tasks<br/>for this role
            Impact-->>AppService: list[dict]
            deactivate Impact

            Note over AppService: milestones = MilestoneList.build()

            opt If include_summaries
                AppService->>PlanningPort: read_last_summary(case_id)
                activate PlanningPort
                PlanningPort-->>AppService: str | None
                deactivate PlanningPort
            end

            AppService->>TokenCalc: calculate(role, task_count, decision_count)
            activate TokenCalc
            Note over TokenCalc: base + bump based on<br/>role and context size
            TokenCalc-->>AppService: int (token budget)
            deactivate TokenCalc

            Note over AppService: Convert entities to dicts<br/>(legacy RoleContextFields)
            AppService->>Mapper: to_dict(story_header)
            activate Mapper
            Mapper-->>AppService: dict
            deactivate Mapper

            Note over AppService: Assemble RoleContextFields
            Note over AppService: packs[role_enum] = pack
        end
    end

    Note over AppService: STEP 6: Compute statistics
    Note over AppService: stats = RehydrationStats(...)

    Note over AppService: STEP 7: Assemble bundle
    Note over AppService: bundle = RehydrationBundle(...)

    Note over AppService,PlanningPort: STEP 8: Persist (optional)

    opt If persist_handoff_bundle
        AppService->>Mapper: to_dict(bundle)
        activate Mapper
        Mapper-->>AppService: dict
        deactivate Mapper

        AppService->>PlanningPort: save_handoff_bundle(case_id, dict, ttl)
        activate PlanningPort
        Note over PlanningPort: Store in Redis<br/>for debugging
        PlanningPort-->>AppService: void
        deactivate PlanningPort
    end

    AppService-->>Client: RehydrationBundle
    deactivate AppService
```

---

## 📊 Datos de Entrada y Salida

### Input: RehydrationRequest
```python
@dataclass
class RehydrationRequest:
    case_id: str              # Story ID
    roles: list[str]          # Roles to build context for
    include_timeline: bool    # Include planning events?
    timeline_events: int      # Max events to fetch
    include_summaries: bool   # Include last summary?
    persist_handoff_bundle: bool
    ttl_seconds: int
```

### Output: RehydrationBundle
```python
@dataclass(frozen=True)
class RehydrationBundle:
    story_id: StoryId
    generated_at_ms: int
    packs: dict[Role, RoleContextFields]  # One pack per role
    stats: RehydrationStats
```

---

## 🔄 Flujo por Rol

Para CADA rol solicitado, se ejecuta este subflujo:

```mermaid
graph TD
    A[Role String] -->|Convert| B[Role Enum]
    B -->|Filter| C[Tasks for this role]
    C -->|Select| D[Relevant Decisions]
    D -->|Build| E[Decision Relations]
    D -->|Calculate| F[Impacted Tasks]
    C -->|Count| G[Token Budget]
    D -->|Count| G

    C --> H[RoleContextFields]
    D --> H
    E --> H
    F --> H
    G --> H

    I[Story Header] --> H
    J[Plan Header] --> H
    K[Milestones] --> H
    L[Last Summary] --> H

    style B fill:#90EE90
    style H fill:#FFD700
```

---

## 🎯 Responsabilidades por Componente

### SessionRehydrationApplicationService
- **Tipo**: Application Service (Orchestrator)
- **Responsabilidad**: Coordinar flujo completo
- **NO hace**: Lógica de negocio (delegada a Domain Services)

### Domain Services (Stateless)
1. **DataIndexer**: Indexar datos para O(1) lookup
2. **DecisionSelector**: Seleccionar decisiones relevantes para rol
3. **ImpactCalculator**: Calcular impactos de decisiones
4. **TokenBudgetCalculator**: Calcular presupuesto de tokens

### Ports (Interfaces)
1. **PlanningReadPort**: Leer specs, plans, eventos (Redis)
2. **DecisionGraphReadPort**: Leer decisiones, impactos (Neo4j)

### Mappers (Infrastructure)
- **StoryHeaderMapper**: spec → StoryHeader entity
- **RehydrationBundleMapper**: bundle → dict (para persistencia)

---

## ⚡ Optimizaciones Posibles

### 1. Paralelización
```python
# ACTUAL: Secuencial
decisions = self.graph_store.list_decisions(case_id)
impacts = self.graph_store.list_decision_impacts(case_id)

# OPTIMIZADO: Paralelo (asyncio)
decisions, impacts = await asyncio.gather(
    self.graph_store.list_decisions_async(case_id),
    self.graph_store.list_decision_impacts_async(case_id),
)
```

### 2. Caché por Rol
```python
# Key incluye role para diferentes vistas
cache_key = f"rehydration:{story_id}:{role}:v{version}"
```

### 3. Lazy Loading
```python
# No cargar timeline si no se solicita
if req.include_timeline:
    events = self.planning_store.get_planning_events(...)
```

---

## 🔍 Puntos de Extensión para RBAC L3

### 1. Filtrado por Rol (Antes de Step 5)
```python
# Aplicar RoleVisibilityPolicy AQUÍ
filtered_data = visibility_policy.filter(indexed_data, role)
```

### 2. Column-Level Filtering (Dentro de Step 5)
```python
# Aplicar ColumnFilterService AQUÍ
filtered_header = column_filter.filter_fields(story_header, role)
```

### 3. Audit Trail (Después de Step 7)
```python
# Registrar acceso a datos AQUÍ
audit_logger.log_data_access(user=req.user_id, role=role, story_id=req.case_id)
```

---

## 🧪 Testing Strategy

### Unit Tests (Domain Services)
```python
def test_decision_selector_selects_relevant_decisions():
    selector = DecisionSelector(fallback_count=3)
    # NO mocks needed - pure logic
    result = selector.select_for_role(tasks, impacts, decisions_by_id, all_decisions)
    assert len(result) == 2
```

### Integration Tests (Application Service)
```python
@pytest.mark.asyncio
async def test_rehydrate_session_e2e():
    # Mock ports
    planning_port = AsyncMock(spec=PlanningReadPort)
    graph_port = AsyncMock(spec=DecisionGraphReadPort)

    # Real domain services (NO mocks)
    service = SessionRehydrationApplicationService(
        planning_store=planning_port,
        graph_store=graph_port,
        token_calculator=TokenBudgetCalculator(),
        decision_selector=DecisionSelector(),
        impact_calculator=ImpactCalculator(),
        data_indexer=DataIndexer(),
    )

    bundle = await service.rehydrate_session(req)
    assert bundle.story_id == expected_story_id
```

---

## 📈 Métricas de Performance

| Métrica | Target | Actual | Status |
|---------|--------|--------|--------|
| Total time | < 200ms | TBD | ⏳ |
| Neo4j queries | < 50ms | TBD | ⏳ |
| Redis queries | < 10ms | TBD | ⏳ |
| Indexing | < 20ms | TBD | ⏳ |
| Per-role assembly | < 30ms | TBD | ⏳ |

---

## 🔗 Referencias

- `core/context/application/session_rehydration_service.py`
- `core/context/domain/services/` (4 domain services)
- `core/context/ports/` (2 ports)
- `docs/architecture/CONTEXT_REHYDRATION_FLOW.md`

