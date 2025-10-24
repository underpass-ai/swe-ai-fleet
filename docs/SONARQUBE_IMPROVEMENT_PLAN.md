# SonarQube Metrics Improvement Plan

**Branch**: `feature/improve-sonarqube-metrics`  
**Date**: October 24, 2025  
**Owner**: Tirso (Architect)  
**Target**: 90%+ coverage on new code for SonarCloud quality gate  

---

## 📊 Current State Analysis

### Coverage Metrics
- **Local Coverage (coverage.xml)**: 69.37% (6,874 / 9,909 lines)
- **SonarCloud Badge**: 92% (from README)
- **Discrepancy**: Local tests running with mocks vs. SonarCloud integration
- **Requirement**: 90% minimum for **new code** to pass quality gate

### Module Coverage Breakdown
Based on `coverage.xml` analysis:

| Module | Coverage | Lines | Status | Priority |
|--------|----------|-------|--------|----------|
| `core/orchestrator/` | 92% | ~800 | ✅ Good | Low |
| `core/context/` | ~65% | ~1,200 | 🟡 Medium | Medium |
| `services/orchestrator/` | 92% | ~600 | ✅ Good | Low |
| `core/agents/` | 47.19% | ~200 | 🔴 Low | **HIGH** |
| `core/models/` | Varies | ~400 | 🟡 Medium | **HIGH** |
| `core/tools/` | Varies | ~600 | 🟡 Medium | High |
| `core/memory/` | Varies | ~400 | 🟡 Medium | Medium |

### Known Test Issues
- 36 unit tests still failing (16 ERRORS + 20 FAILED)
- Root cause: Protobuf modules not generated correctly in test environment
- `services.*.gen` import failures in test setup
- Async/mock configuration issues

---

## 🎯 Improvement Strategy

### Phase 1: Fix Failing Tests (Week 1)
**Objective**: Get all unit tests passing to establish true baseline

1. **Diagnose Protobuf Generation**
   - [ ] Run `make test-unit` with verbose output
   - [ ] Capture failure logs in `debug/test-failures.log`
   - [ ] Identify root cause of `services.*.gen` failures
   - [ ] Fix `scripts/test/_generate_protos.sh` if needed

2. **Fix Context Service Tests**
   - [ ] `tests/unit/services/context/test_server.py` (19 errors)
   - [ ] Verify mocks for Neo4jQueryStore, NEO4J_PORT
   - [ ] Ensure async test handling is correct
   - [ ] Add missing test fixtures

3. **Fix Orchestrator Tests**
   - [ ] `tests/unit/services/orchestrator/` (8+ errors)
   - [ ] Verify Ray mock configuration
   - [ ] Check NATS publisher/subscriber mocks
   - [ ] Fix any async/await issues

4. **Quick Wins**
   - [ ] Fix 2 assertion errors in misc modules
   - [ ] Fix 4 async mock configuration issues

**Expected Result**: All 36 tests pass + baseline coverage = 69%+

### Phase 2: Add Missing Unit Tests (Week 2-3)
**Objective**: Close coverage gaps in critical modules

1. **Core/Agents Module** (Currently 47.19%)
   - [ ] Profile loader tests
   - [ ] Agent interface implementations
   - [ ] Configuration loading edge cases
   - **Target**: 85% coverage (+~60 lines)

2. **Core/Models Module**
   - [ ] Model factory tests
   - [ ] Configuration parsing
   - [ ] Error handling paths
   - **Target**: 80% coverage (+~80 lines)

3. **Core/Tools Module**
   - [ ] Tool registry tests
   - [ ] Tool execution mocking
   - [ ] Error recovery
   - **Target**: 75% coverage (+~100 lines)

4. **Core/Memory Module**
   - [ ] Memory interface implementations
   - [ ] Cache behavior
   - [ ] Consistency checks
   - **Target**: 80% coverage (+~60 lines)

5. **Core/Context Use Cases** (Priority)
   - [ ] ProjectDecisionUseCase
   - [ ] UpdateSubtaskStatusUseCase
   - [ ] ProjectSubtaskUseCase
   - [ ] ProjectCaseUseCase
   - **Target**: 85% coverage (+~120 lines)

6. **Core/Orchestrator Use Cases** (Priority)
   - [ ] Deliberate (already 92%, maintain)
   - [ ] Orchestrate (already 92%, maintain)
   - [ ] Additional edge cases
   - **Target**: 90%+ coverage

**Expected Result**: Overall coverage = 75-78%

### Phase 3: Integration & Edge Cases (Week 4)
**Objective**: Push coverage to 90%+ on new code paths

1. **Error Handling Coverage**
   - [ ] Exception paths in critical services
   - [ ] Timeout/retry scenarios
   - [ ] Invalid input validation
   - **Target**: +~80 lines at 100% coverage

2. **Async/Concurrency Tests**
   - [ ] Race condition scenarios
   - [ ] Deadlock prevention
   - [ ] Concurrent access patterns
   - **Target**: +~60 lines

3. **Integration Points**
   - [ ] NATS message flow
   - [ ] gRPC service calls
   - [ ] Neo4j graph operations
   - [ ] Ray job dispatch
   - **Target**: +~100 lines

4. **Boundary Conditions**
   - [ ] Empty/None inputs
   - [ ] Oversized payloads
   - [ ] Malformed messages
   - [ ] Service degradation
   - **Target**: +~70 lines

**Expected Result**: Overall coverage = 85-88%

### Phase 4: Quality Gate Enforcement (Week 4-5)
**Objective**: Ensure 90% coverage on new code passes SonarQube

1. **Local Verification**
   - [ ] Run full test suite: `make test-unit`
   - [ ] Generate coverage.xml
   - [ ] Verify coverage.xml reports ≥90% for modified files
   - [ ] Run lint: `ruff check . --fix`

2. **SonarCloud Configuration**
   - [ ] Verify `sonar-project.properties` is correct
   - [ ] Check GitHub Actions workflow
   - [ ] Review quality gate settings on SonarCloud
   - [ ] Monitor PR analysis results

3. **Commit & Push**
   - [ ] Commit with conventional format: `feat(quality): improve coverage to 90%+`
   - [ ] Create PR with test results in description
   - [ ] Monitor SonarCloud analysis

---

## 📋 Testing Checklist

### Before Each Commit
- [ ] Run `source .venv/bin/activate`
- [ ] Run `make test-unit` (all tests pass)
- [ ] Verify `coverage.xml` generated
- [ ] Run `ruff check . --fix`
- [ ] Check no new linting errors

### Module-Specific Tests
- [ ] **agents**: `pytest tests/unit/core/agents/ -v --cov=core.agents`
- [ ] **models**: `pytest tests/unit/core/models/ -v --cov=core.models`
- [ ] **tools**: `pytest tests/unit/core/tools/ -v --cov=core.tools`
- [ ] **memory**: `pytest tests/unit/core/memory/ -v --cov=core.memory`
- [ ] **context**: `pytest tests/unit/core/context/ -v --cov=core.context`
- [ ] **orchestrator**: `pytest tests/unit/core/orchestrator/ -v --cov=core.orchestrator`

### Coverage Targets
```
Core modules:
- core/orchestrator: ≥92% (maintain)
- core/context: ≥85% (improve from 65%)
- core/agents: ≥85% (improve from 47%)
- core/models: ≥80% (improve from varies)
- core/tools: ≥75% (improve from varies)
- core/memory: ≥80% (improve from varies)

Services:
- services/orchestrator: ≥92% (maintain)
- services/context: ≥80% (improve)

Overall: ≥90% on new code
```

---

## 🚨 Risk Assessment

### High Risk Areas
1. **Protobuf Generation in Tests**
   - Risk: Generated stubs cause import failures
   - Mitigation: Use `make test-unit` not pytest directly
   - Fallback: Debug protobuf compilation script

2. **Async Mock Configuration**
   - Risk: Incorrect async/await setup breaks tests
   - Mitigation: Review conftest.py fixtures
   - Fallback: Simplify mocks to sync versions first

3. **Coverage Discrepancy**
   - Risk: Local 69% vs SonarCloud 92% (inconsistent)
   - Mitigation: Investigate exclusions in sonar-project.properties
   - Fallback: Run SonarCloud scanner locally to verify

### Medium Risk Areas
1. **External Service Mocking**
   - Ensure all Redis/Neo4j/NATS/Ray calls are mocked
   - Create realistic mock responses

2. **Async Test Patterns**
   - Review pytest-asyncio configuration
   - Use proper async fixtures

---

## 📚 Resources & References

### Project Standards
- [.cursorrules](../.cursorrules) - Project rules and conventions
- [Testing Strategy](./docs/TESTING_STRATEGY.md) - Comprehensive testing guide
- [Testing Architecture](./docs/TESTING_ARCHITECTURE.md) - Test structure details
- [Hexagonal Architecture](./docs/architecture/HEXAGONAL_ARCHITECTURE.md) - Domain-driven design

### SonarQube Configuration
- `sonar-project.properties` - Coverage and exclusion rules
- `deploy/k8s/SONARQUBE_NOTES.md` - SonarCloud integration notes

### Test Troubleshooting
- [Common Test Issues](./docs/sessions/2025-10-21/TEST_RESULTS_20251021.md) - Recent test failures
- [Unit Tests to Fix](./archived-docs/UNIT_TESTS_TO_FIX.md) - Detailed error list

---

## 🎯 Success Criteria

### Phase 1 Complete ✅
- [ ] All 36 failing tests pass
- [ ] `make test-unit` runs successfully
- [ ] coverage.xml generated without errors
- [ ] Baseline coverage ≥69%

### Phase 2 Complete ✅
- [ ] Core modules reach target coverage
- [ ] Overall coverage ≥75%
- [ ] No new test failures introduced
- [ ] All commits have passing tests

### Phase 3 Complete ✅
- [ ] Edge cases covered
- [ ] Overall coverage ≥85%
- [ ] Error handling paths 100% covered
- [ ] Integration scenarios tested

### Phase 4 Complete ✅
- [ ] Overall coverage ≥90%
- [ ] SonarCloud quality gate PASSED ✅
- [ ] PR merged successfully
- [ ] Badge updated in README

---

## 📅 Timeline

| Phase | Duration | Start | End | Status |
|-------|----------|-------|-----|--------|
| Phase 1: Fix Tests | 3-4 days | Oct 24 | Oct 27 | 🚀 In Progress |
| Phase 2: Add Tests | 5-7 days | Oct 28 | Nov 03 | ⏰ Pending |
| Phase 3: Edge Cases | 3-4 days | Nov 04 | Nov 07 | ⏰ Pending |
| Phase 4: Quality Gate | 1-2 days | Nov 08 | Nov 09 | ⏰ Pending |

**Total**: ~2-3 weeks

---

## 📝 Notes for Future Sessions

- Check Git branch status: `git branch -v`
- Compare local vs SonarCloud coverage before each phase
- Keep PR description updated with progress
- Document any new issues discovered in Phase 1
