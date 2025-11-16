# ADR: CLAIM_APPROVAL for Product Owner

**Date:** 2025-11-06  
**Status:** REJECTED (for now - YAGNI)  
**Decision:** Do NOT add CLAIM_APPROVAL to FSM in this PR  
**Rationale:** Documented below

---

## 🎯 Context

During RBAC L2+L3 implementation, we identified naming inconsistency:

```
Developer: todo → CLAIM_TASK → implementing
Architect: pending_arch_review → CLAIM_REVIEW → arch_reviewing
QA:        pending_qa → CLAIM_TESTING → qa_testing
PO:        pending_po_approval → (NO CLAIM!) → (APPROVE_STORY directly)
```

**Question:** Should PO have `CLAIM_APPROVAL` action?

---

## 🔍 Analysis

### If We Add CLAIM_APPROVAL:

**FSM Changes:**
```yaml
# NEW state required:
- id: po_approving
  description: "PO is reviewing business value"
  allowed_roles: [po]
  entry_actions: [CLAIM_APPROVAL]
  exit_actions: [APPROVE_STORY, REJECT_STORY]

# NEW transition:
- from: pending_po_approval
  to: po_approving
  action: CLAIM_APPROVAL
  role_required: po

# UPDATE existing transitions:
- from: po_approving  # Changed from pending_po_approval
  to: po_approved
  action: APPROVE_STORY

- from: po_approving  # Changed from pending_po_approval
  to: cancelled
  action: REJECT_STORY
```

**Impact:**
- States: 12 → 13 (adds po_approving)
- Transitions: 15 → 17 (adds CLAIM + updates APPROVE/REJECT sources)
- Tests: Update ~20 test cases
- Docs: Update all FSM diagrams

---

## ⚖️ Trade-offs

### Pros of Adding CLAIM_APPROVAL:

✅ **Pattern Consistency:**
- All validator roles have CLAIM action
- Symmetric design (architect, qa, po all same pattern)

✅ **Future-Proof:**
- Supports multiple PO agents
- Prevents concurrent approval attempts
- Scales to enterprise teams

✅ **Explicit State Model:**
- Differentiates "waiting for approval" vs "actively approving"
- Better observability (can see PO is working on it)

### Cons of Adding CLAIM_APPROVAL:

❌ **YAGNI (You Ain't Gonna Need It):**
- Current system: 1 PO agent only
- No evidence of multiple PO agents needed
- Over-engineering for theoretical future

❌ **Complexity:**
- 13 states vs 12 states
- More state transitions to maintain
- More test cases to write/maintain

❌ **Real Team Reality:**
```
In real startup teams:
  - 1 Product Owner (not 5)
  - PO approval is NOT concurrent work
  - No "claim" needed (no race condition)
  
In real enterprise teams:
  - Multiple POs exist BUT...
  - Each PO owns different product areas
  - Stories assigned to specific PO (no claiming)
```

❌ **Time to Market:**
- Delays RBAC L2+L3 implementation
- Can be added later WITHOUT breaking changes

---

## 🎯 Decision

### **REJECTED (for now)**

Do NOT add CLAIM_APPROVAL in this PR.

### Rationale:

1. **YAGNI Principle:**
   - No current need for multiple PO agents
   - Can add later if needed
   - Simpler now = faster to production

2. **Real Team Model:**
   - 1 PO is realistic for current scale
   - No concurrency issues in practice
   - PO approval is low-frequency event

3. **Evolutive Architecture:**
   - Can add po_approving state later
   - Not a breaking change (adds intermediate state)
   - Backward compatible

4. **Focus:**
   - Core value: RBAC L2 (workflow routing) + L3 (context scoping)
   - CLAIM_APPROVAL is nice-to-have, not critical path

---

## 📋 When to Revisit This Decision

### Triggers for Adding CLAIM_APPROVAL:

1. **Multiple PO Agents:**
   - If we implement PO agent pool (> 1 agent)
   - If concurrent approval becomes issue

2. **Enterprise Scaling:**
   - Multiple product lines
   - Multiple PO agents per product

3. **Race Condition Evidence:**
   - If we see duplicate approvals
   - If PO agents conflict

4. **Pattern Enforcement:**
   - If we decide ALL validators MUST have claim
   - For architectural purity

---

## 🔧 How to Add Later (Migration Path)

If we need CLAIM_APPROVAL in future PR:

**Step 1:** Add state to WorkflowStateEnum
```python
PO_APPROVING = "po_approving"
```

**Step 2:** Add action to ActionEnum (already done!)
```python
CLAIM_APPROVAL = "claim_approval"
```

**Step 3:** Update workflow.fsm.yaml
```yaml
- id: po_approving
  description: "PO is actively approving"
  allowed_roles: [po]
```

**Step 4:** Add transitions
```yaml
- from: pending_po_approval
  to: po_approving
  action: CLAIM_APPROVAL
```

**Step 5:** Update tests
- Add test cases for new state
- Update FSM test config

**Estimation:** 2-3 hours work, backward compatible

---

## 📊 Current FSM Pattern (Intentional Asymmetry)

```
Developer: 
  todo → CLAIM_TASK → implementing → work → dev_completed
  
Architect:
  pending_arch_review → CLAIM_REVIEW → arch_reviewing → validate → arch_approved/rejected
  
QA:
  pending_qa → CLAIM_TESTING → qa_testing → validate → qa_passed/failed
  
PO (SIMPLER):
  pending_po_approval → (APPROVE_STORY directly) → po_approved
  ↑ NO intermediate claiming state (intentional simplification)
```

**Why Simpler for PO:**
- Lower frequency (approval is final gate)
- Typically single PO (no concurrency)
- Faster approval flow (no unnecessary state)

---

## 🎯 Conclusion

**Decision:** Do NOT add CLAIM_APPROVAL or po_approving state in this PR.

**Status:** INTENTIONAL ASYMMETRY (documented)

**Future:** Can add if needed (migration path defined)

**Documentation:** Mark in code comments that PO pattern is intentionally simpler

---

**Approved By:** Tirso García Ibáñez  
**Date:** 2025-11-06  
**PR:** feature/rbac-level-2-orchestrator  
**Revisit:** When scaling to multiple PO agents



