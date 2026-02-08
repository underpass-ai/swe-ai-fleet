# Core Reports

Reporting bounded context for implementation and decision-enriched planning reports.

## Scope

`core/reports` provides:

- Report use cases:
  - `ImplementationReportUseCase` (`report_usecase.py`)
  - `DecisionEnrichedReportUseCase` (`decision_enriched_report.py`)
- Domain models for reports, decisions, edges, task impacts, and graph analytics types
- Ports:
  - `PlanningReadPort`
  - `DecisionGraphReadPort`
  - `GraphAnalyticsReadPort`
- Adapters:
  - `RedisPlanningReadAdapter`
  - `Neo4jDecisionGraphReadAdapter`
  - `Neo4jGraphAnalyticsReadAdapter`

## Output

Both use cases produce Markdown reports plus computed stats.
Reports can be persisted back to Redis through `save_report` in the planning read adapter.

## Notes

- Decision-graph adapters rely on projected planning/context graph data in Neo4j.
- LLM conversation enrichment is best-effort and depends on available Redis keys.

## Tests

```bash
make test-module MODULE=core/reports
```
