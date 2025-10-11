# Archived E2E Tests

## 📦 Why These Tests Are Archived

These E2E tests were written for an **older architecture** where:
- Direct Redis access was used (now using Valkey + NATS)
- Tests required local Redis setup with specific passwords
- Architecture was pre-microservices (direct imports vs gRPC)

**Archived Date:** 2025-10-11  
**Reason:** Replaced by modern testcontainers-based E2E tests

---

## 📋 Archived Tests

### 1. test_context_assembler_e2e.py (1 test)
**What it tested:**
- `build_prompt_blocks()` end-to-end
- ✅ **Secret redaction** (passwords, Bearer tokens)
- Scope policies application

**Status:** ✅ Functionality **extracted** to `test_grpc_e2e.py::test_context_redacts_secrets`

---

### 2. test_session_rehydration_e2e.py (1 test)
**What it tested:**
- `SessionRehydrationUseCase` with multiple roles
- Handoff bundles with TTL
- Decision relevance filtering by role
- Timeline event ordering

**Status:** ✅ Functionality **covered** by `test_grpc_e2e.py::test_rehydrate_session_*`  
**Note:** Handoff bundles tested indirectly through RehydrateSession gRPC

---

### 3. test_redis_store_e2e.py (1 test)
**What it tested:**
- Basic LLM call storage in Redis

**Status:** ⚠️ **Not extracted** - Too basic, covered by unit tests

---

### 4. test_decision_enriched_report_e2e.py (1 test)
**What it tested:**
- DecisionEnrichedReportUseCase
- Reports with decisions, dependencies, impacts
- Markdown-formatted reports

**Status:** ⚠️ **Deferred** - Reports functionality exists but not critical for Context Service E2E

---

### 5. test_report_usecase_e2e.py (3 tests)
**What it tested:**
- ImplementationReportUseCase with **graph analytics**
- Critical decisions (by indegree score)
- Cycle detection in decision graphs
- Topological layers
- Analytics with empty results (edge case)

**Status:** 🎯 **PLANNED** - Will create `test_analytics_e2e.py` with Neo4j-based analytics  
**Priority:** High - Graph analytics is a project differentiator

---

## 🎯 What Was Extracted

### Added to test_grpc_e2e.py

#### test_context_redacts_secrets
```python
# Tests that sensitive data is redacted in context assembly
# Verifies: passwords, API keys, Bearer tokens are [REDACTED]
```

**Why it matters:** Security - prevents credential leaks to LLMs

---

## 🔮 Future Work

### Graph Analytics E2E (High Priority) 🌟
Create `tests/e2e/services/context/test_analytics_e2e.py`:
- Use testcontainers for Neo4j
- Seed decision graph with cycles, dependencies
- Test critical decision detection
- Test cycle detection
- Test topological sorting
- Test report generation with analytics

**Value:** This is a **differentiating feature** - advanced decision graph analytics

### Report Generation E2E (Medium Priority)
If Reports become critical for Context Service:
- Modernize with testcontainers
- Integrate with gRPC API
- Test DecisionEnrichedReportUseCase

---

## 💡 Why Not Just Update These Tests?

### Problems with Original Tests:
1. **Architecture mismatch:**
   - Old: Direct imports from domain/use cases
   - New: gRPC API as interface
   
2. **Infrastructure setup:**
   - Old: Require manual Redis setup with password
   - New: Testcontainers auto-setup

3. **Data seeding:**
   - Old: Manual Redis key manipulation
   - New: gRPC API + fixtures

4. **Maintenance:**
   - Old: Tied to internal implementation
   - New: Test through public API (more robust)

### Better Approach:
- ✅ Keep valuable test **scenarios** (what to test)
- ✅ Rewrite using **modern infrastructure** (testcontainers)
- ✅ Test through **public APIs** (gRPC)
- ✅ Result: More maintainable, faster, more reliable

---

## 📚 References

- [Modern E2E Tests](../services/context/README.md) - Current E2E test suite
- [Test Strategy](../../docs/TESTING_STRATEGY.md) - Overall testing approach
- [Context Service](../../services/context/README.md) - Current architecture

---

**Note:** These tests are kept as **reference** for test scenarios and edge cases.  
They are not meant to be run but serve as documentation of what was tested before.

