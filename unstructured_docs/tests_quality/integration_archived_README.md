# Archived Tests

## 📦 Why These Tests Are Archived

These tests were written for an **older architecture** and have **obsolete dependencies**:

### Problemas Comunes:
1. **Imports rotos**: `swe_ai_fleet.memory.redis_store` no existe
   - Debería ser: `swe_ai_fleet.memory.adapters.redis_store`
   - Pero `RedisKvPort` tampoco existe (renombrado/eliminado)

2. **Arquitectura vieja**: Pre-microservices
   - Imports directos de domain/use cases
   - Ahora: gRPC APIs como interfaz

3. **Setup manual**: Redis con passwords específicas
   - Ahora: testcontainers auto-setup

**Archived Date:** 2025-10-11  
**Actualizado:** 2025-10-12 (investigación completa)  
**Reason:** Dependencias obsoletas, arquitectura desactualizada

---

## 📋 Archived Tests (6 total)

### 1. test_context_assembler_e2e.py (1 test)
**What it tested:**
- `build_prompt_blocks()` end-to-end
- ✅ **Secret redaction** (passwords, Bearer tokens)
- Scope policies application

**Why archived:**
- ❌ Import roto: `RedisKvPort` no existe
- ❌ Arquitectura obsoleta (pre-microservices)

**Status:** ✅ Functionality **extracted** to `test_grpc_e2e.py::test_context_redacts_secrets`

---

### 2. test_session_rehydration_e2e.py (1 test)
**What it tested:**
- `SessionRehydrationUseCase` with multiple roles
- Handoff bundles with TTL
- Decision relevance filtering by role
- Timeline event ordering

**Why archived:**
- ❌ Import roto: `RedisKvPort` no existe
- ❌ Arquitectura obsoleta

**Status:** ✅ Functionality **covered** by `test_grpc_e2e.py::test_rehydrate_session_*`  
**Note:** Handoff bundles tested indirectly through RehydrateSession gRPC

---

### 3. test_redis_store_e2e.py (1 test)
**What it tested:**
- Basic LLM call storage in Redis

**Why archived:**
- ❌ Import roto: `RedisKvPort` no existe
- ❌ Test trivial (solo save)

**Status:** ✅ **Covered by unit tests** - Funcionalidad básica ya testeada

---

### 4. test_decision_enriched_report_e2e.py (1 test)
**What it tested:**
- DecisionEnrichedReportUseCase
- Reports with decisions, dependencies, impacts
- Markdown-formatted reports

**Why archived:**
- ⚠️ Arquitectura obsoleta (pre-microservices)
- ⚠️ Requiere setup manual de Redis

**Status:** ⚠️ **Deferred** - Reports functionality exists but not critical

---

### 5. test_report_usecase_e2e.py (3 tests)
**What it tested:**
- ImplementationReportUseCase with **graph analytics**
- Critical decisions (by indegree score)
- Cycle detection in decision graphs
- Topological layers
- Analytics with empty results (edge case)

**Why archived:**
- ⚠️ Arquitectura obsoleta (pre-microservices)
- ⚠️ Requiere setup manual de Redis + Neo4j

**Status:** 🎯 **PLANNED** - Will create modern version with testcontainers  
**Priority:** High - Graph analytics is a project differentiator

---

### 6. test_persistence_integration.py (12 tests)
**What it tested:**
- Neo4j persistence layer direct
- Decision/Subtask/Milestone CRUD
- Scope detection

**Why archived:**
- ❌ Requiere `services.context.server` (módulo Python que no existe en estructura actual)
- ❌ Fixture `neo4j_connection` no definida
- ❌ Arquitectura obsoleta

**Status:** ✅ **Covered** by `test_persistence_e2e.py` (7 tests) via gRPC API

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

