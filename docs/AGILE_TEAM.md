# Agile Team Simulation

EdgeCrew simulates a **virtual agile squad**:

- **Developers** → generate and review code.
- **DevOps** → manage infra and deployments.
- **QA** → validate outputs against acceptance criteria.
- **Data** → handle schemas and pipelines.
- **Architect** → selects best solutions, aligns to user story.
- **Judge (optional)** → verifies correctness & safety.
- **Human Product Owner** → defines user stories, backlog, priorities.

**Human-in-the-loop**: The Product Owner is human (no PM bot) and participates in ceremonies with the agents.

Agents collaborate using peer councils, architect selection, and audit trails.

## Roles & Responsibilities

- Developer: implementation, refactors, unit tests, code reviews
- DevOps: CI/CD, runtime, observability, infra as code, release engineering
- QA: test strategy, acceptance criteria, regression and e2e validation
- Data: schemas, migrations, pipelines, data quality checks
- Architect: non-functional requirements, trade-off analysis, system design
- Judge: policy and safety validation on risky changes

## Ceremonies

- Planning: PO defines and prioritizes; Architect decomposes; agents estimate
- Daily: PO joins as needed to clarify priorities and unblock work
- Review: PO validates against acceptance criteria; Architect selects final approach
- Retrospective: PO shares business feedback; outcomes recorded in the knowledge graph

## Artifacts

- User stories and tasks with acceptance criteria
- Decision records and rationales
- Test evidence and execution artifacts

