# RFC-0003: Human-in-the-Loop Collaboration Flow (Sprint Planning)

## Summary

Define a controlled, human-in-the-loop collaboration flow that converts an atomic use case into an approved plan of technical subtasks before any execution. The flow ensures traceability, safe orchestration, and reusability through structured logging, graph projections, and checkpoints.

## Problem

Unstructured agent execution risks time/cost overruns and poor traceability:

- Plans are not validated by a human before tools run.
- Dependencies and priorities are implicit, leading to rework.
- There is no standardized, searchable record of execution context and decisions.
- Rollback and mid-flight replanning are ad hoc.
- Lessons learned are not consistently captured for reuse.

## Goals

- Human approval before any automated execution (human-in-the-loop).
- Granular planning of technical subtasks with dependencies and priorities.
- Full traceability: decisions, adjustments, and state transitions recorded.
- Operational visibility via Redis Streams and graph projection in Neo4j.
- Safe iteration with checkpoints and controlled pause/replan.
- Knowledge reuse: closure reports and lessons learned indexed for future cases.

## Non-Goals

- Replace a full-featured project management system.
- Fully automate planning without human validation.
- Production hardening of RBAC/auditing beyond what is specified here.

## Decision

Adopt a five-phase collaboration flow with a council of role-based agents proposing a plan that is integrated by an Architect, validated by a human, then executed in a controlled manner with persistent telemetry and audit artifacts.

## Details

### 1. Use Case Creation

- The human Product Owner (PO) provides:
  - Functional and non-functional goals
  - Success criteria (Definition of Done)
  - Known technical/economic constraints
- Persist as `CaseSpec` in memory (Redis + Neo4j).

---

### 2. Refinement / Sprint Planning (agent proposal)

- A role-based agent council analyzes the case and proposes:
  - Required technical subtasks
  - Technologies and processes per subtask
  - Risks and dependencies
- The Architect integrates proposals into a Preliminary Plan.

---

### 3. Human Participation

- The human receives the Preliminary Plan before any execution.
- The human may:
  - Change technologies (cost, licenses, timelines)
  - Adjust priorities
  - Reorder dependencies
  - Add/remove subtasks
- The plan is validated and marked as Ready.

---

### 4. Controlled Execution

- Agents execute subtasks according to the validated plan.
- Each subtask emits:
  - Log records to Redis Streams (immediate execution context)
  - Graph projection to Neo4j (state and relationships)
  - Checkpoints to enable partial rollback
- The human can pause or replan at any point.

---

### 5. Closure and Feedback

- Upon completion of all subtasks:
  - Generate a closure report with decisions, outcomes, durations, and learnings
  - Index the report for future retrieval in similar cases
  - Add lessons learned to the knowledge repository

---

## Advantages

1. Human in the loop before execution.
2. Granular planning for better time and cost control.
3. Total traceability: every decision and adjustment is recorded.
4. Reuse: past plans can be cloned/adapted for similar cases.
5. Flexibility: real-time stack or approach changes without breaking global logic.


