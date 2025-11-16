# User Story Lifecycle

1. **Create** → Human PO defines story.
2. **Plan** → Architect decomposes into tasks.
3. **Work** → Agents collaborate (dev, devops, data, QA).
4. **Validate** → QA + Judge + automated checks.
5. **Persist** → Decisions, tasks, and results stored in graph DB.
6. **Rehydrate** → Any task/story can be re-opened or improved.

Note: The Product Owner is human and interacts with agents during ceremonies (planning, reviews, retros), ensuring priorities and acceptance criteria are clear.

Example query:

```
MATCH (t:Task)-[:PART_OF]->(s:UserStory {id:"US-123"})
RETURN t.id, t.status, t.last_updated
```
