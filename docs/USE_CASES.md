## Use cases — how it helps you today

Outcome-oriented, not implementation-focused. Each case includes inputs, steps, and expected outputs.

### 1) Planning and alignment (PO/Architect)

- Input: case specification (`case_id`), acceptance criteria, tentative subtasks.
- Steps:
  1. Load demo `CTX-001` (see Golden Path).
  2. Open `http://localhost:8080/ui/report?case_id=CTX-001`.
  3. Review sections: Summary, Acceptance Criteria, Plan (subtasks), Dependencies.
- Output: a Markdown/HTML report with plan and dependencies, ready for planning discussion.

### 2) Decision traceability (Architect/Dev)

- Input: proposed technical decisions and impacts.
- Steps:
  1. Load demo `CTX-001` (Golden Path).
  2. In the report, navigate to "Decision Graph" and "Dependencies/Influences".
  3. Validate in Neo4j (optional): Bolt `bolt://localhost:7687` with `neo4j/swefleet-dev`.
- Output: visibility into which decisions influence which subtasks, and related plans/actors.

### 3) QA handover (QA/Dev)

- Input: acceptance criteria and recent agent/LLM conversations.
- Steps:
  1. Golden Path + (optional) seed example conversations:
     - `http://localhost:8080/api/demo/seed_llm?case_id=CTX-001`
  2. Open the report UI and review "LLM Conversations (recent)" and "Acceptance Criteria".
- Output: condensed context to design test cases and verify criteria.

### 4) Lightweight audit (Tech lead)

- Input: `case_id` and time cut.
- Steps:
  1. Golden Path.
  2. Download the Markdown via API: `GET /api/report?case_id=CTX-001&persist=false`.
  3. Archive the report (or persist in Redis with `persist=true`).
- Output: auditable artifact of decisions, plan, and key events.

Resources:

- Golden Path (10 min): `docs/GOLDEN_PATH.md`
- Demo Frontend: `README.md` → "Demo Frontend (local)"
- Infrastructure (high level): `docs/INFRA_ARCHITECTURE.md`


