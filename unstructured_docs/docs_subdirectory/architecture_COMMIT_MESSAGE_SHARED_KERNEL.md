# Commit Message - Shared Kernel Migration

**Date:** 2025-11-06
**Type:** refactor(core)
**Scope:** Bounded Contexts + Shared Kernel

---

## Commit Message

```
refactor(core): implement Shared Kernel for Action/ActionEnum

BREAKING CHANGE: Action moved from agents_and_tools to shared kernel

This commit implements DDD Shared Kernel pattern to decouple bounded
contexts while sharing domain concepts used across multiple contexts.

Changes:
- Create core/shared/domain/action.py (Shared Kernel)
- Move Action/ActionEnum from agents_and_tools to shared
- Update 23 files to import from core.shared.domain
- Add workflow actions: AUTO_ROUTE_*, DISCARD_TASK, CLAIM_TESTING
- Remove FIX_BUGS (unified with REVISE_CODE per architect feedback)
- Fix WorkflowStateMetadata.QA_FAILED to use REVISE_CODE
- Update test FSM config to match real workflow.fsm.yaml
- Move tests to bounded context dirs for cohesion

Bounded Contexts:
- core/agents_and_tools: imports from core.shared.domain
- services/workflow: imports from core.shared.domain
- Both decoupled, share Action via kernel

Tests: 688 passing (agents:278, orch/mon/plan:305, workflow:105)

Architecture validated by Tirso García Ibáñez (Agile Architect).

Key architectural decisions:
- Ceremonies (dailys, sprint review) are NATS events, NOT FSM transitions
- CLAIM states required for all multi-agent roles (architect, QA)
- PO has NO CLAIM (single PO, no concurrency)
- REVISE_CODE generic (arch OR qa feedback)
- Auto-transitions have explicit actions (audit trail)

Refs:
- docs/architecture/decisions/2025-11-06/SHARED_KERNEL_FINAL_DESIGN.md
- docs/architecture/decisions/2025-11-06/CEREMONIES_VS_FSM_SEPARATION.md
- docs/architecture/decisions/2025-11-06/CLAIM_APPROVAL_DECISION.md
```

---

## Files Changed (23 total)

### Created (4):
- core/shared/__init__.py
- core/shared/domain/__init__.py
- core/shared/domain/action.py
- docs/architecture/decisions/2025-11-06/* (5 docs)

### Modified (19):
- config/workflow.fsm.yaml (FIX_BUGS → REVISE_CODE, CANCEL_TASK → DISCARD_TASK)
- core/agents_and_tools/agents/domain/entities/rbac/__init__.py
- core/agents_and_tools/agents/domain/entities/rbac/role.py
- core/agents_and_tools/agents/domain/entities/rbac/role_factory.py
- services/workflow/domain/* (6 files)
- services/workflow/application/* (1 file)
- services/workflow/infrastructure/* (4 files)
- services/workflow/tests/* (7 files)
- scripts/test/unit.sh

### Deleted (1):
- core/agents_and_tools/agents/domain/entities/rbac/action.py (moved to shared)

---

## Impact Assessment

### Bounded Context Decoupling: ✅
- No direct dependencies between agents_and_tools ↔ workflow
- Both depend on shared kernel only
- Clean architecture

### Test Coverage: ✅
- All 688 tests passing
- No regressions
- Coverage maintained

### Breaking Changes: ⚠️
- Import paths changed (core.agents_and_tools.*.action → core.shared.domain)
- Mitigated: All internal, no external APIs affected

### Architecture Quality: ✅
- DDD Shared Kernel pattern correctly applied
- Validated by agile architect (Tirso)
- Reflects real team workflows

---

**Ready to commit:** YES
**Requires:** Code review from Tirso before merge



