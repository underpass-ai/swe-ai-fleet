# Context Management

EdgeCrew introduces a **state-of-the-art pipeline** for managing and distributing context.

- **Summarization Layer** → lightweight models create concise snapshots after each phase.
- **Knowledge Catalog** → events converted into entities/relations in a graph store.
- **Assembler** → builds role-specific prompts per agent type.
- **Distribution** → context is routed per-role, ensuring consistency and efficiency.

This approach cuts token cost, prevents confusion, and preserves full traceability.

## Pipeline Overview

1. Ingest events (story created, task updated, test failed)
2. Summarize into compact, role-neutral notes
3. Catalog entities and relations in the knowledge graph
4. Assemble role-specific packs (Developer/DevOps/QA/Data/Architect)
5. Distribute to agents; capture outputs and feed back into the loop

## Role-Specific Packs

- Developer: code diffs, failing tests, APIs, acceptance criteria
- DevOps: deployment manifests, runtime metrics, infra changes
- QA: acceptance criteria, scenarios, regression set, coverage deltas
- Data: schema changes, migration plans, data quality checks
- Architect: decisions, trade-offs, non-functional requirements

## Example

```
Input events:
- US-123 created; AC: login with 2FA
- Task DEV-1 opened; failing tests in auth module

Summaries:
- AC: user can log in with OTP; lockout after 5 attempts
- DEV note: token validation bug in `auth/otp.py`

Developer pack:
- Diffs: auth/otp.py, tests/test_auth_otp.py
- AC: 2FA, lockout policy
- Related decisions: D-42 "OTP source of truth"
```

