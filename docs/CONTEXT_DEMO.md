# Context Demo (Redis + Neo4j)

This demo seeds the bounded context `context` with minimal data across Redis and Neo4j and shows how to query it.

## Seed

```bash
export REDIS_URL="redis://:swefleet-dev@localhost:6379/0"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="swefleet-dev"
export DEMO_CASE_ID="CTX-001"
python scripts/seed_context_example.py
```

Redis keys created:
- `swe:case:CTX-001:spec`
- `swe:case:CTX-001:planning:draft`
- `swe:case:CTX-001:planning:stream`

Neo4j nodes/relationships:
- `(:Case {id:"CTX-001"})-[:HAS_PLAN]->(:PlanVersion {id:"P-CTX-001"})`
- `(:PlanVersion)-[:CONTAINS_DECISION]->(:Decision {id:"D1"|"D2"})`
- `(:Decision)-[:INFLUENCES]->(:Subtask {id:"S1"|"S2"})`
- `(:Decision)-[:AUTHORED_BY]->(:Actor {id:"actor:planner"})`
- `(:Decision {id:"D1"})-[:DEPENDS_ON]->(:Decision {id:"D2"})`

## Verify

```bash
# Decisions with influenced subtasks and authors (CRI‑O)
sudo crictl exec $(sudo crictl ps -a -q --name neo4j | head -n1) \
  /var/lib/neo4j/bin/cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (c:Case {id:'CTX-001'})-[:HAS_PLAN]->(:PlanVersion)-[:CONTAINS_DECISION]->(d:Decision)
   OPTIONAL MATCH (d)-[:INFLUENCES]->(s:Subtask)
   OPTIONAL MATCH (d)-[:AUTHORED_BY]->(a:Actor)
   RETURN d.id, collect(DISTINCT s.id), collect(DISTINCT a.id)
   ORDER BY d.id;"

# Decision dependencies (CRI‑O)
sudo crictl exec $(sudo crictl ps -a -q --name neo4j | head -n1) \
  /var/lib/neo4j/bin/cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (c:Case {id:'CTX-001'})-[:HAS_PLAN]->(:PlanVersion)-[:CONTAINS_DECISION]->(d1:Decision)
   MATCH (d1)-[r]->(d2:Decision)
   RETURN d1.id, type(r), d2.id
   ORDER BY d1.id, d2.id;"
```

### Exported artifacts

- Spec JSON: `docs/context_demo/spec.json`
- Plan draft JSON: `docs/context_demo/plan_draft.json`
- Planning stream JSON: `docs/context_demo/planning_stream.json`
- Neo4j nodes CSV: `docs/context_demo/nodes.csv`
- Neo4j relationships CSV: `docs/context_demo/relationships.csv`

## Use Case Example

You can now run `SessionRehydrationUseCase` to assemble role-based context packs using the seeded stores (Redis for planning, Neo4j for decisions):

- Build `RehydrationRequest` with roles like `architect`, `developer` and `case_id=CTX-001`.
- Expect relevant decisions and impacted subtasks to be included.

## Troubleshooting

- Auth rate limiting: wait ~60 seconds or restart the Neo4j container.
- Ensure all clients use the same password; healthcheck reads `${NEO4J_AUTH##*/}`.
