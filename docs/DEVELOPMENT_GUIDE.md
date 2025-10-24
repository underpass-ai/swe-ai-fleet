# Development Guide - SWE AI Fleet

## 🎯 Overview

This guide provides comprehensive development practices, patterns, and standards for contributing to SWE AI Fleet. It covers Domain-Driven Design (DDD) implementation, testing strategies, code quality standards, and best practices for maintaining a clean, maintainable codebase.

## 🏗️ Architecture Patterns

### Domain-Driven Design (DDD)

SWE AI Fleet follows DDD principles to create a clean, maintainable architecture with clear separation of concerns.

#### **Domain Objects**

Domain objects encapsulate business logic and represent core concepts:

```python
@dataclass(frozen=True)
class ContextSection:
    content: str
    section_type: str
    priority: int = 0

    def __str__(self) -> str:
        return self.content

@dataclass
class ContextSections:
    sections: list[ContextSection] = field(default_factory=list)

    def add_section(self, content: str, section_type: str, priority: int = 0) -> None:
        section = ContextSection(content=content, section_type=section_type, priority=priority)
        self.sections.append(section)

    def build_from_role_context_fields(
        self,
        role_context_fields: RoleContextFields,
        current_subtask_id: str | None = None
    ) -> None:
        """Build context sections from role context fields.
        
        This method inverts the control flow by having the domain object
        orchestrate the building of sections from the provided data.
        """
        # Domain logic implementation
```

#### **Ports and Adapters Pattern**

Clear interfaces separate business logic from infrastructure:

```python
class GraphAnalyticsReadPort(Protocol):
    """Read-only analytics queries over the decision graph."""
    
    def get_critical_decisions(self, case_id: str, limit: int = 10) -> list[CriticalNode]: ...
    def find_cycles(self, case_id: str, max_depth: int = 6) -> list[PathCycle]: ...
    def topo_layers(self, case_id: str) -> LayeredTopology: ...

class Neo4jGraphAnalyticsReadAdapter(GraphAnalyticsReadPort):
    """Analytics adapter using a thin Neo4jStore wrapper."""
    
    def __init__(self, store: Neo4jStore) -> None:
        self._store = store
```

#### **Use Cases**

Use cases encapsulate application business logic:

```python
class ImplementationReportUseCase:
    def __init__(
        self,
        planning_store: PlanningReadPort,
        analytics_port: GraphAnalyticsReadPort | None = None,
    ) -> None:
        self.store = planning_store
        self.analytics_port = analytics_port

    def generate(self, req: ReportRequest) -> Report:
        # Business logic implementation
        # Orchestrates domain objects and adapters
```

### Control Flow Inversion

The system uses control flow inversion to maintain clean architecture:

```python
# Before: External orchestration
def _build_context(role_context_fields: RoleContextFields) -> str:
    sections = []
    sections.append(_build_case_identification(role_context_fields))
    sections.append(_build_plan_rationale(role_context_fields))
    # ... more orchestration
    return "\n".join(sections)

# After: Domain object orchestration
def _build_context(role_context_fields: RoleContextFields) -> str:
    context_sections = ContextSections()
    context_sections.build_from_role_context_fields(role_context_fields)
    return context_sections.to_string()
```

## 🧪 Testing Strategy

### Test Organization

```
tests/
├── unit/                           # Unit tests
│   ├── test_context_assembler_unit.py
│   ├── test_prompt_scope_policy_unit.py
│   ├── test_reports_usecase_unit.py
│   └── test_neo4j_graph_analytics_read_adapter_unit.py
├── integration/                    # Integration tests
│   └── test_router_integration.py
└── e2e/                           # End-to-end tests
    ├── test_report_usecase_e2e.py
    ├── test_context_assembler_e2e.py
    └── test_session_rehydration_e2e.py
```

### Unit Testing Patterns

#### **Mock Setup**

```python
class _FakeStore:
    def __init__(self, results: dict[str, list[dict[str, Any]]]):
        self._results = results

    def query(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        # Route by unique RETURN signatures
        if "RETURN m.id AS id, 'Decision' AS label, toFloat(indeg) AS score" in cypher:
            return self._results.get("critical", [])
        # ... more routing logic
        return []

def _make(results: dict[str, list[dict[str, Any]]]) -> Neo4jGraphAnalyticsReadAdapter:
    return Neo4jGraphAnalyticsReadAdapter(_FakeStore(results))
```

#### **Test Structure**

```python
def test_critical_nodes_mapping():
    # Arrange
    adapter = _make({
        "critical": [
            {"id": "D2", "label": "Decision", "score": 3.0},
            {"id": "D1", "label": "Decision", "score": 1.0},
        ]
    })
    
    # Act
    lst = adapter.get_critical_decisions("C1", limit=10)
    
    # Assert
    assert [c.id for c in lst] == ["D2", "D1"]
    assert all(isinstance(x, CriticalNode) for x in lst)
```

#### **Edge Case Testing**

```python
def test_critical_nodes_empty():
    adapter = _make({"critical": []})
    lst = adapter.get_critical_decisions("C1", limit=10)
    assert lst == []

def test_layers_cycle_handling():
    # Graph with cycle: A -> B -> C -> A
    adapter = _make({
        "layers": [
            {
                "nodes": ["A", "B", "C"],
                "edges": [
                    {"src": "A", "dst": "B"},
                    {"src": "B", "dst": "C"},
                    {"src": "C", "dst": "A"},  # Creates cycle
                ],
            }
        ]
    })
    topo = adapter.topo_layers("C1")
    assert isinstance(topo, LayeredTopology)
    assert len(topo.layers) > 0
```

### Integration Testing

#### **E2E Test Patterns**

```python
def test_report_usecase_e2e_with_analytics():
    # Setup
    url = "redis://:swefleet-dev@localhost:6379/0"
    r: redis.Redis = redis.Redis.from_url(url, decode_responses=True)
    case_id = f"e2e-analytics-{int(time.time())}"
    _cleanup_case(r, case_id)
    
    # Seed data
    spec_doc = {...}
    r.set(_k_spec(case_id), json.dumps(spec_doc))
    
    # Build use case with analytics
    adapter = RedisPlanningReadAdapter(r)
    analytics_port = _make_analytics_port()
    usecase = ImplementationReportUseCase(adapter, analytics_port=analytics_port)
    
    # Execute
    report = usecase.generate(req)
    
    # Validate
    assert "Graph Analytics (Decisions)" in report.markdown
    analytics_port.get_critical_decisions.assert_called_once_with(case_id, limit=10)
```

## 📝 Code Quality Standards

### Ruff Configuration

The project uses Ruff for linting and formatting:

```toml
[tool.ruff]
target-version = "py313"
line-length = 110
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long, handled by black
    "B008",  # do not perform function calls in argument defaults
]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]
"tests/**/*" = ["B011"]
```

### Type Hints

Complete type hints throughout the codebase:

```python
from __future__ import annotations

from typing import Any, Protocol

class GraphAnalyticsReadPort(Protocol):
    def get_critical_decisions(self, case_id: str, limit: int = 10) -> list[CriticalNode]: ...
    def find_cycles(self, case_id: str, max_depth: int = 6) -> list[PathCycle]: ...
    def topo_layers(self, case_id: str) -> LayeredTopology: ...

def _make(results: dict[str, list[dict[str, Any]]]) -> Neo4jGraphAnalyticsReadAdapter:
    return Neo4jGraphAnalyticsReadAdapter(_FakeStore(results))
```

### Documentation Standards

#### **Docstrings**

```python
def build_from_role_context_fields(
    self,
    role_context_fields: RoleContextFields,
    current_subtask_id: str | None = None
) -> None:
    """Build context sections from role context fields.

    This method inverts the control flow by having the domain object
    orchestrate the building of sections from the provided data.

    Args:
        role_context_fields: The role context data to build sections from
        current_subtask_id: Optional current subtask ID for context filtering
    """
```

#### **Comments**

```python
# Use a subgraph of Decision nodes under the latest PlanVersion for this case.
q = (
    "MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(p:PlanVersion)\n"
    "WITH p ORDER BY coalesce(p.version,0) DESC LIMIT 1\n"
    # ... more query
)

# Kahn's algorithm
layers: list[list[str]] = []
remaining = set(node_set)
while remaining:
    layer = [n for n in remaining if indeg.get(n, 0) == 0]
    if not layer:
        # Cycle remainder: output them as the final layer deterministically
        layers.append(sorted(list(remaining)))
        break
```

## 🔧 Development Workflow

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/underpass-ai/swe-ai-fleet.git
cd swe-ai-fleet

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt
```

### Running Tests

**See**: [docs/TESTING.md](TESTING.md) - **Documento autoritativo único**

```bash
# Unit tests (fast, no infrastructure)
make test-unit

# Integration tests (with containers)
make test-integration

# E2E tests (requires K8s cluster)
make test-e2e

# All tests
make test-all

# Coverage is automatically generated with test-unit
```

**⚠️ IMPORTANTE**: Siempre usar Makefile, NO pytest directo.  
El Makefile maneja setup de protobuf, containers, y cleanup.

### Code Quality Checks

```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy src/swe_ai_fleet/

# Security checks
bandit -r src/swe_ai_fleet/
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

## 🚀 Adding New Features

### 1. Define Domain Objects

```python
@dataclass(frozen=True)
class NewFeature:
    id: str
    name: str
    data: dict[str, Any]

    def validate(self) -> bool:
        """Domain validation logic."""
        return len(self.name) > 0 and self.id is not None
```

### 2. Create Port Interface

```python
class NewFeaturePort(Protocol):
    def get_feature(self, feature_id: str) -> NewFeature | None: ...
    def save_feature(self, feature: NewFeature) -> bool: ...
```

### 3. Implement Adapter

```python
class NewFeatureAdapter(NewFeaturePort):
    def __init__(self, store: SomeStore) -> None:
        self._store = store

    def get_feature(self, feature_id: str) -> NewFeature | None:
        # Implementation
        pass

    def save_feature(self, feature: NewFeature) -> bool:
        # Implementation
        pass
```

### 4. Add Use Case

```python
class NewFeatureUseCase:
    def __init__(self, feature_port: NewFeaturePort) -> None:
        self.feature_port = feature_port

    def process_feature(self, feature_id: str) -> NewFeature:
        feature = self.feature_port.get_feature(feature_id)
        if not feature:
            raise ValueError("Feature not found")
        return feature
```

### 5. Write Tests

```python
def test_new_feature_processing():
    # Arrange
    feature_port = MagicMock()
    feature_port.get_feature.return_value = NewFeature(id="1", name="test", data={})
    usecase = NewFeatureUseCase(feature_port)
    
    # Act
    result = usecase.process_feature("1")
    
    # Assert
    assert result.id == "1"
    feature_port.get_feature.assert_called_once_with("1")
```

## 🔒 Security Best Practices

### Input Validation

```python
def validate_case_id(case_id: str) -> bool:
    """Validate case ID format."""
    if not case_id or not isinstance(case_id, str):
        return False
    # Add specific validation rules
    return len(case_id) > 0 and case_id.isalnum()

def get_critical_decisions(self, case_id: str, limit: int = 10) -> list[CriticalNode]:
    if not validate_case_id(case_id):
        raise ValueError("Invalid case ID")
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    # Implementation
```

### Parameter Binding

```python
# Good: Parameterized query
q = "MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(p:PlanVersion)"
recs = self._store.query(q, {"cid": case_id})

# Bad: String concatenation (vulnerable to injection)
q = f"MATCH (c:Case {{id:'{case_id}'}})-[:HAS_PLAN]->(p:PlanVersion)"
recs = self._store.query(q, {})
```

### Error Handling

```python
def safe_query(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Execute query with error handling."""
    try:
        return self._store.query(query, params)
    except Exception as e:
        logger.error(f"Query failed: {e}")
        # Return safe default or re-raise based on context
        return []
```

## 📊 Performance Considerations

### Query Optimization

```python
# Use indexes for frequently queried fields
CREATE INDEX case_id_index FOR (c:Case) ON (c.id);
CREATE INDEX decision_id_index FOR (d:Decision) ON (d.id);

# Limit result sets
RETURN m.id AS id, 'Decision' AS label, toFloat(indeg) AS score
ORDER BY score DESC LIMIT $limit

# Use parameterized queries for query plan caching
MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(p:PlanVersion)
```

### Caching Strategy

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_critical_decisions_cached(self, case_id: str, limit: int = 10) -> list[CriticalNode]:
    """Cached version of critical decisions query."""
    return self.get_critical_decisions(case_id, limit)
```

### Async Operations

```python
import asyncio
from typing import AsyncGenerator

async def get_analytics_async(self, case_id: str) -> AsyncGenerator[CriticalNode, None]:
    """Async generator for analytics results."""
    # Implementation with async database operations
    pass
```

## 🤝 Contributing Guidelines

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-analytics-feature
   ```

2. **Make Changes**
   - Follow DDD patterns
   - Add comprehensive tests
   - Update documentation

3. **Run Quality Checks**
   ```bash
   ruff check . --fix
   make test-unit
   make test-integration  # Si cambios en adapters
   ```
   
   **Ver**: [docs/TESTING_ARCHITECTURE.md](TESTING_ARCHITECTURE.md) para testing completo.

4. **Create Pull Request**
   - Clear description of changes
   - Link to related issues
   - Include test results

### Code Review Checklist

- [ ] Follows DDD patterns
- [ ] Includes comprehensive tests
- [ ] Passes all quality checks
- [ ] Updated documentation
- [ ] No security vulnerabilities
- [ ] Performance considerations addressed

## 📚 Resources

### Documentation
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)

### Tools
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Neo4j Cypher](https://neo4j.com/docs/cypher-manual/current/)

### Patterns
- [Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture/)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Unit of Work](https://martinfowler.com/eaaCatalog/unitOfWork.html)
