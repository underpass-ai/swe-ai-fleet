# Memory Architecture

- **Short-term memory** → In-memory key-value store. Stores recent events, summaries, embeddings.
- **Long-term memory** → Graph knowledge store. Stores entities (UserStory, Task, Decision, Agent) and relations.

Together, they provide efficient context, auditable history, and flexible retrieval.

## Data Model (long-term)

Entities:

- UserStory(id, title, status)
- Task(id, status, assignee, timestamps)
- Decision(id, rationale, created_at)
- Agent(id, role)

Relations:

- (Task)-[:PART_OF]->(UserStory)
- (Decision)-[:RELATES_TO]->(Task|UserStory)
- (Agent)-[:PERFORMED]->(Task)
- (Decision)-[:ALTERNATIVE_OF]->(Decision)

## Retention

- Short-term: sliding window (e.g., last N events per case)
- Long-term: project lifetime with archival options

## Example Query

```
MATCH (s:UserStory {id:"US-123"})<-[:PART_OF]-(t:Task)
OPTIONAL MATCH (d:Decision)-[:RELATES_TO]->(t)
RETURN s.id, collect(distinct t.id) AS tasks, collect(distinct d.id) AS decisions
```

