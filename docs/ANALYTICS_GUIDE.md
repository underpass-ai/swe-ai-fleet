# Analytics Guide - SWE AI Fleet

## 🎯 Overview

The Analytics Engine in SWE AI Fleet provides comprehensive graph analytics capabilities for decision analysis, dependency management, and project insights. It leverages Neo4j's graph database to analyze decision relationships, identify critical dependencies, and provide actionable insights for software development projects.

## 🏗️ Architecture

### Analytics Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Reports       │───▶│  Analytics       │───▶│  Neo4j          │
│   UseCase       │    │  Port            │    │  Graph          │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  Analytics       │    │  Cypher         │
                       │  Adapter         │    │  Queries        │
                       └──────────────────┘    └─────────────────┘
```

### Data Flow

1. **Report Generation**: `ImplementationReportUseCase` requests analytics
2. **Analytics Port**: `GraphAnalyticsReadPort` interface defines analytics operations
3. **Neo4j Adapter**: `Neo4jGraphAnalyticsReadAdapter` executes Cypher queries
4. **Graph Analysis**: Neo4j processes graph algorithms and returns results
5. **Report Integration**: Analytics results are integrated into implementation reports

## 📊 Analytics Features

### 1. Critical Decision Analysis

Identifies high-impact decisions based on their indegree (number of incoming dependencies).

#### **Algorithm**
- **Indegree Analysis**: Counts incoming dependencies for each decision
- **Scoring**: Higher indegree = higher criticality score
- **Ranking**: Decisions sorted by criticality score

#### **Use Cases**
- **Risk Assessment**: Identify decisions that could block multiple tasks
- **Resource Planning**: Focus attention on high-impact decisions
- **Dependency Management**: Understand decision impact on project timeline

#### **Example Output**
```markdown
### Critical Decisions (by indegree)
- `ARCH-001` — score 5.00
- `SEC-002` — score 3.00
- `PERF-003` — score 2.00
```

### 2. Cycle Detection

Identifies dependency cycles in decision graphs that could cause deadlocks or infinite loops.

#### **Algorithm**
- **Path Finding**: Uses variable-length path queries (1 to max_depth)
- **Cycle Detection**: Identifies paths that start and end at the same node
- **Cycle Analysis**: Extracts cycle nodes and relationship types

#### **Use Cases**
- **Deadlock Prevention**: Identify circular dependencies
- **Architecture Review**: Detect design issues
- **Planning Validation**: Ensure feasible execution order

#### **Example Output**
```markdown
### Cycles
- Cycle 1: AUTH-001 -> SEC-002 -> AUTH-001
- Cycle 2: DB-001 -> CACHE-002 -> DB-001
```

### 3. Topological Layering

Organizes decisions into layers based on their dependencies using Kahn's algorithm.

#### **Algorithm**
- **Kahn's Algorithm**: Topological sorting for directed acyclic graphs
- **Layer Assignment**: Decisions with no dependencies go in layer 0
- **Dependency Resolution**: Removes completed decisions and updates remaining
- **Cycle Handling**: Remaining nodes in cycles are placed in final layer

#### **Use Cases**
- **Execution Planning**: Determine optimal decision execution order
- **Parallelization**: Identify decisions that can be made in parallel
- **Milestone Planning**: Group decisions into logical phases

#### **Example Output**
```markdown
### Topological Layers
- Layer 0: ARCH-001, SEC-002
- Layer 1: DB-003, CACHE-004
- Layer 2: API-005, UI-006
```

## 🔧 Implementation

### Analytics Data Types

```python
@dataclass(frozen=True)
class CriticalNode:
    id: str
    label: str
    score: float

@dataclass(frozen=True)
class PathCycle:
    nodes: list[str]
    rels: list[str]

@dataclass(frozen=True)
class LayeredTopology:
    layers: list[list[str]]
```

### Analytics Port Interface

```python
class GraphAnalyticsReadPort(Protocol):
    def get_critical_decisions(self, case_id: str, limit: int = 10) -> list[CriticalNode]: ...
    def find_cycles(self, case_id: str, max_depth: int = 6) -> list[PathCycle]: ...
    def topo_layers(self, case_id: str) -> LayeredTopology: ...
```

### Neo4j Adapter Implementation

```python
class Neo4jGraphAnalyticsReadAdapter(GraphAnalyticsReadPort):
    def __init__(self, store: Neo4jStore) -> None:
        self._store = store

    def get_critical_decisions(self, case_id: str, limit: int = 10) -> list[CriticalNode]:
        # Cypher query for indegree analysis
        # Returns CriticalNode objects

    def find_cycles(self, case_id: str, max_depth: int = 6) -> list[PathCycle]:
        # Cypher query for cycle detection
        # Returns PathCycle objects

    def topo_layers(self, case_id: str) -> LayeredTopology:
        # Kahn's algorithm implementation
        # Returns LayeredTopology object
```

## 📈 Cypher Queries

### Critical Decision Analysis

```cypher
MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(p:PlanVersion)
WITH p ORDER BY coalesce(p.version,0) DESC LIMIT 1
MATCH (p)-[:CONTAINS_DECISION]->(d:Decision)
WITH collect(d) AS D
UNWIND D AS m
OPTIONAL MATCH (m)<-[r]-(:Decision)
WHERE ALL(x IN [startNode(r), endNode(r)] WHERE x:Decision) 
  AND endNode(r) IN D AND startNode(r) IN D
WITH m, count(r) AS indeg
RETURN m.id AS id, 'Decision' AS label, toFloat(indeg) AS score
ORDER BY score DESC LIMIT $limit
```

### Cycle Detection

```cypher
MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(p:PlanVersion)
WITH p ORDER BY coalesce(p.version,0) DESC LIMIT 1
MATCH (p)-[:CONTAINS_DECISION]->(d:Decision)
WITH collect(d) AS D
UNWIND D AS start
MATCH p=(start)-[r*1..$maxDepth]->(start)
WHERE ALL(rel IN r WHERE startNode(rel):Decision AND endNode(rel):Decision 
  AND startNode(rel) IN D AND endNode(rel) IN D)
RETURN [x IN nodes(p) | x.id] AS nodes, [rel IN relationships(p) | type(rel)] AS rels
LIMIT 20
```

### Graph Structure Query

```cypher
MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(p:PlanVersion)
WITH p ORDER BY coalesce(p.version,0) DESC LIMIT 1
MATCH (p)-[:CONTAINS_DECISION]->(d:Decision)
WITH collect(d) AS D
UNWIND D AS d1
OPTIONAL MATCH (d1)-[r]->(d2:Decision)
WHERE d2 IN D
WITH collect(DISTINCT d1.id) AS nodes, collect({src:d1.id, dst:d2.id}) AS edges
RETURN nodes, edges
```

## 🧪 Testing

### Unit Tests

```python
def test_critical_nodes_mapping():
    adapter = _make({
        "critical": [
            {"id": "D2", "label": "Decision", "score": 3.0},
            {"id": "D1", "label": "Decision", "score": 1.0},
        ]
    })
    lst = adapter.get_critical_decisions("C1", limit=10)
    assert [c.id for c in lst] == ["D2", "D1"]
    assert all(isinstance(x, CriticalNode) for x in lst)
```

### Integration Tests

```python
def test_report_usecase_e2e_with_analytics():
    # Full end-to-end test with analytics integration
    analytics_port = _make_analytics_port()
    usecase = ImplementationReportUseCase(adapter, analytics_port=analytics_port)
    report = usecase.generate(req)
    
    # Validate analytics section
    assert "Graph Analytics (Decisions)" in report.markdown
    assert "Critical Decisions (by indegree)" in report.markdown
```

## 🚀 Usage Examples

### Basic Analytics Integration

```python
from swe_ai_fleet.reports.report_usecase import ImplementationReportUseCase
from swe_ai_fleet.reports.adapters.neo4j_graph_analytics_read_adapter import Neo4jGraphAnalyticsReadAdapter

# Create analytics adapter
analytics_adapter = Neo4jGraphAnalyticsReadAdapter(neo4j_store)

# Create report use case with analytics
report_usecase = ImplementationReportUseCase(
    planning_store=planning_adapter,
    analytics_port=analytics_adapter
)

# Generate report with analytics
report = report_usecase.generate(report_request)
```

### Custom Analytics Queries

```python
# Get critical decisions
critical_decisions = analytics_adapter.get_critical_decisions("case-123", limit=5)

# Find cycles
cycles = analytics_adapter.find_cycles("case-123", max_depth=4)

# Get topological layers
layers = analytics_adapter.topo_layers("case-123")
```

## 🔧 Configuration

### Neo4j Connection

```python
from swe_ai_fleet.memory.neo4j_store import Neo4jStore

# Configure Neo4j connection
neo4j_store = Neo4jStore(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password"
)
```

### Analytics Parameters

```python
# Critical decision analysis
critical_decisions = analytics_adapter.get_critical_decisions(
    case_id="case-123",
    limit=10  # Number of top critical decisions
)

# Cycle detection
cycles = analytics_adapter.find_cycles(
    case_id="case-123",
    max_depth=6  # Maximum cycle length to detect
)
```

## 📊 Performance Considerations

### Query Optimization

- **Indexing**: Ensure proper indexes on Case and Decision nodes
- **Parameter Binding**: Use parameterized queries for security and performance
- **Result Limiting**: Limit result sets to prevent memory issues
- **Caching**: Consider caching frequently accessed analytics results

### Scalability

- **Batch Processing**: Process large graphs in batches
- **Async Operations**: Use async/await for I/O intensive operations
- **Connection Pooling**: Reuse Neo4j connections
- **Query Optimization**: Monitor and optimize Cypher query performance

## 🔒 Security

### Data Protection

- **Parameter Binding**: Prevent Cypher injection attacks
- **Access Control**: Implement proper authentication and authorization
- **Data Validation**: Validate all input parameters
- **Audit Logging**: Log all analytics operations

### Privacy

- **Data Redaction**: Remove sensitive information from analytics results
- **Access Logging**: Track who accesses analytics data
- **Data Retention**: Implement appropriate data retention policies

## 🚀 Future Enhancements

### Planned Features

1. **Machine Learning Integration**
   - Predictive analytics for decision outcomes
   - Risk assessment based on historical patterns
   - Automated decision recommendations

2. **Advanced Graph Algorithms**
   - Community detection for decision clusters
   - Centrality analysis for influence mapping
   - Path analysis for impact assessment

3. **Real-time Analytics**
   - Live analytics dashboard
   - Real-time decision monitoring
   - Automated alerts for critical changes

4. **Visual Analytics**
   - Interactive graph visualization
   - Decision flow diagrams
   - Dependency network visualization

## 📚 References

- [Neo4j Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [Graph Algorithms](https://neo4j.com/docs/graph-algorithms/current/)
- [Kahn's Algorithm](https://en.wikipedia.org/wiki/Topological_sorting)
- [Graph Theory](https://en.wikipedia.org/wiki/Graph_theory)
