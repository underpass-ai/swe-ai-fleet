# SWE AI Fleet - Roadmap

**Last Updated:** 2025-11-07  
**Status:** 🚀 Accelerated Development (RBAC L1 + L2 Complete)

---

## 🎯 Current Milestone Status

| Milestone | Status | Progress | Bar |
|----------|--------|---------:|-----|
| M0 Bootstrap | 🟢 Done | 100% | ████████████████████████████████████████ |
| M1 Cluster PoC (legacy) | 🟢 Done | 100% | ████████████████████████████████████████ |
| M2 Context | 🟢 Done | 100% | ████████████████████████████████████████ |
| M3 Roles/PO | 🟢 In Progress | 75% | ██████████████████████████████░░░░░░░░░░ |
| M4 Tools | 🟢 Near Complete | 85% | ██████████████████████████████████░░░░░░ |
| M5 Agile E2E | 🟡 In Progress | 35% | ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░ |
| M6 Community | ⚪ Planned | 10% | ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ |

**Note:** Each █ ≈ 2.5% (40 blocks = 100%)

---

## 📊 Recent Progress (Last 4 Weeks)

### **Week of Nov 4-7, 2025** 🚀

**🎉 RBAC Level 2 Complete - Workflow Orchestration Service**

- ✅ Workflow Service microservice (production-ready)
  - Protobuf API (4 RPCs, 8 message types)
  - Multi-stage Dockerfile
  - K8s deployment (2 replicas, port 50056)
  - 138 unit tests (>90% coverage)
  
- ✅ DDD + Hexagonal Architecture perfection
  - DTOs, Mappers, Use Cases, Contracts
  - Anti-corruption layer (PlanningServiceContract)
  - Tell, Don't Ask exhaustively applied (15 files)
  
- ✅ Shared Kernel refactored
  - Split into 4 cohesive files (action_enum, scope_enum, action_scopes, action)
  - 18 unit tests for Action value object
  
- ✅ Deploy infrastructure updated
  - fresh-redeploy.sh includes Workflow
  - Test pipeline includes Workflow (unit.sh)
  - Documentation: DEPLOYMENT.md, README.md
  
**Stats:**
- 58 files changed
- +5,833 lines (code + tests + docs)
- 138 Workflow tests passing
- 1,265 total tests passing

### **Week of Oct 28 - Nov 1, 2025**

**🎉 RBAC Level 1 Complete - Tool Access Control** (PR #95)

- ✅ RBAC system (Role, Action, Scope enums)
- ✅ Policy enforcement (agents_and_tools service)
- ✅ 676 unit tests
- ✅ >90% coverage

**Stats:**
- 106 files changed
- +157,574 lines
- Production-ready

### **Week of Oct 21-25, 2025**

**Planning Service** (PR #93)
- ✅ Microservice completo (gRPC API, FSM, Neo4j + Valkey)
- ✅ 278 unit tests
- ✅ DDD + Hexagonal Architecture

**Stats:**
- 100 files changed
- +10,678 lines

### **Week of Oct 14-18, 2025**

**Ray Executor Service** (PR #91)
- ✅ Hexagonal Architecture refactoring
- ✅ Async agent execution
- ✅ vLLM integration

**Monitoring Service** (PR #86)
- ✅ Hexagonal refactor
- ✅ 305 unit tests

**Stats:**
- 513 + 5,049 files changed
- +41,837 + 11,683 lines

---

## 🏗️ Milestone Details

### M0: Bootstrap ✅ COMPLETE (100%)

**Deliverables:**
- [x] Kubernetes cluster setup
- [x] Helm charts
- [x] Orchestrator skeleton
- [x] NATS JetStream messaging

### M1: Cluster PoC ✅ COMPLETE (100%)

**Deliverables:**
- [x] Cluster-from-YAML e2e demo
- [x] Basic agent deliberation

### M2: Context ✅ COMPLETE (100%)

**Deliverables:**
- [x] Context Service microservice
- [x] Neo4j + Valkey (Redis) hybrid storage
- [x] Intelligent context assembly
- [x] Session rehydration
- [x] gRPC API

### M3: Roles/PO 🟢 IN PROGRESS (75%)

**Deliverables:**
- [x] **RBAC Level 1: Tool Access Control** ✅ (Oct 28)
- [x] **RBAC Level 2: Workflow Action Control** ✅ (Nov 7)
- [ ] RBAC Level 3: Data Access Control (⏳ Next)
- [x] Role definitions (Developer, Architect, QA, DevOps, Data, PO)
- [x] Planning Service with story FSM
- [ ] Human PO interface (UI integration)
- [ ] Agent-to-agent task routing

**Progress:**
- **RBAC L1:** Production-ready (676 tests)
- **RBAC L2:** Workflow Service complete (138 tests)
- **RBAC L3:** Planned (data filtering, column-level access)

### M4: Tools 🟢 NEAR COMPLETE (85%)

**Deliverables:**
- [x] Tool registry and RBAC enforcement
- [x] File operations tool
- [x] Git tool
- [x] Docker tool
- [x] HTTP tool
- [x] Database tool
- [x] Helm tool (basic)
- [x] kubectl tool (basic)
- [ ] Tool sandboxing (security hardening)
- [ ] Tool rate limiting
- [ ] Tool audit trail (partial)

**Progress:**
- 6 tools production-ready with RBAC
- Agent tool execution validated (e2e tests)
- Security policies enforced

### M5: Agile E2E Flow 🟡 IN PROGRESS (35%)

**Deliverables:**
- [x] Planning Service (story FSM)
- [x] Workflow Service (task FSM)
- [x] Agent deliberation (orchestrator)
- [x] Context assembly
- [x] Ray-based agent execution
- [ ] Full workflow: design → decision → implementation → test → approval
- [ ] PO approval flow
- [ ] Automated testing by QA agent
- [ ] Deployment by DevOps agent
- [ ] Reporting and analytics

**Progress:**
- Core services deployed (orchestrator, planning, workflow, context)
- Agent execution working (Ray + vLLM)
- Missing: Full E2E integration tests, PO UI

### M6: Community & OSS ⚪ PLANNED (10%)

**Deliverables:**
- [x] Git repository structure
- [x] Basic documentation
- [ ] Landing page
- [ ] Contribution guidelines
- [ ] Installation automation
- [ ] Video demos
- [ ] Blog posts

---

## 📈 Progress Timeline

### **2025-11 (November)** - RBAC Level 2 Sprint

| Date | Achievement | Lines Changed | Tests |
|------|-------------|--------------|-------|
| Nov 7 | ✅ Workflow Service + Shared Kernel refactor | +5,833 | 138 |
| Nov 6 | ✅ Shared Kernel (Action/ActionEnum decoupling) | +3,885 | - |
| Nov 5 | ✅ Workflow Service (DDD Pure implementation) | +4,786 | 86 |
| Nov 4 | ✅ Workflow Service design (FSM, RBAC L2+L3) | +1,206 | - |

**Month Total:** ~15,710 lines, 224+ tests, 4 microservice features

### **2025-10 (October)** - Foundation Sprint

| Date | Achievement | Lines Changed | Tests |
|------|-------------|--------------|-------|
| Oct 28 | ✅ RBAC Level 1 (Tool Access Control) | +157,574 | 676 |
| Oct 25 | ✅ Planning Service microservice | +10,678 | 278 |
| Oct 21 | ✅ E2E Tests + Context API improvements | +6,803 | - |
| Oct 18 | ✅ Ray Executor Hexagonal refactor | +41,837 | - |
| Oct 14 | ✅ Monitoring Hexagonal refactor | +11,683 | 305 |

**Month Total:** ~228,575 lines, 1,259+ tests, 5 major features

---

## 🎯 Next Sprint (Nov 8-14, 2025)

### **Priority 1: RBAC L2 Integration**

- [ ] Orchestrator integration (call Workflow Service gRPC)
- [ ] E2E tests (Planning → Workflow → Agent execution)
- [ ] Deploy to K8s cluster
- [ ] Verify full flow

### **Priority 2: RBAC L3 Planning**

- [ ] Data Access Control design
- [ ] Column-level filtering
- [ ] Story-level isolation
- [ ] Audit trail for data access

### **Priority 3: PO Interface**

- [ ] PO UI for story approval
- [ ] Workflow visualization
- [ ] Task assignment dashboard

---

## 📊 System Status (As of Nov 7, 2025)

### **Microservices Deployed** (6/8 planned)

| Service | Status | Port | Tests | Coverage | Version |
|---------|--------|------|-------|----------|---------|
| **Orchestrator** | ✅ Production | 50055 | 142 | 65% | v3.0.0 |
| **Context** | ✅ Production | 50054 | - | 96% | v2.0.0 |
| **Planning** | ✅ Production | 50051 | 278 | 95% | v2.0.0 |
| **Workflow** | ✅ Ready to Deploy | 50056 | 138 | 94% | v1.0.0 |
| **Ray Executor** | ✅ Production | 50057 | - | 90% | v3.0.0 |
| **Monitoring** | ✅ Production | 8080 | 305 | 98% | v3.2.1 |
| **Agents & Tools** | ✅ Library | - | 402 | 85% | - |
| **PO UI** | ⚪ Planned | 80 | - | - | - |

**Total Tests:** 1,265 passing  
**Total Lines:** ~50,000+ (production code)

### **Infrastructure**

- ✅ Kubernetes cluster (1.28+)
- ✅ NATS JetStream (messaging backbone)
- ✅ Neo4j (graph database)
- ✅ Valkey (cache)
- ✅ Ray cluster (agent execution)
- ✅ Registry (registry.underpassai.com)

---

## 🔥 Velocity Metrics

### **Last 4 Weeks (Oct 14 - Nov 7)**

- **Commits:** 23 significant features/refactors
- **Lines added:** ~244,000+
- **Tests added:** 1,483+
- **Microservices created:** 3 (Planning, Workflow, RBAC)
- **Services refactored:** 3 (Ray Executor, Monitoring, Context)
- **PRs merged:** 13

**Average velocity:**
- ~6 commits/week
- ~61,000 lines/week
- ~370 tests/week
- ~1 microservice/week

### **Technical Debt Reduction**

- ✅ SonarCloud CRITICAL issues resolved
- ✅ Coverage improved: 45% → 85%+ (new code)
- ✅ Hexagonal Architecture: 5 services refactored
- ✅ DDD principles: consistently applied
- ✅ Test pyramid: 1,265 unit tests, E2E suite

---

## 🎯 2025 Q4 Goals (Revised)

### **November 2025** (Current)

- [x] RBAC Level 1 ✅
- [x] RBAC Level 2 ✅
- [ ] RBAC Level 3 (data access) - In Progress
- [ ] Full E2E workflow validation
- [ ] PO UI MVP

**Target:** RBAC L1-L3 complete by Nov 30

### **December 2025**

- [ ] Production deployment (all services)
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Documentation complete
- [ ] Demo video

**Target:** Production-ready system by Dec 31

---

## 📚 Documentation Status

### **Architecture Decisions** ✅

- [x] 11 ADRs in docs/architecture/decisions/2025-11-06/
- [x] RBAC Levels 2 & 3 Strategy
- [x] Shared Kernel design
- [x] FSM validation (workflow vs ceremonies)
- [x] Claim approval decision (YAGNI)

### **Operations** ✅

- [x] DEPLOYMENT.md (deployment procedures)
- [x] K8S_TROUBLESHOOTING.md
- [x] Monitoring setup
- [x] Testing guide

### **Pending**

- [ ] API documentation (OpenAPI/gRPC docs)
- [ ] Architecture diagrams
- [ ] User guides
- [ ] Video tutorials

---

## 🚀 Release Plan

### **v1.0.0 - RBAC Foundation** (Target: Nov 30, 2025)

**Scope:**
- RBAC Levels 1, 2, 3 complete
- 6 microservices deployed
- Full agile workflow (design → deployment)
- Basic PO UI

**Exit Criteria:**
- [ ] All RBAC levels functional
- [ ] E2E tests passing
- [ ] >85% test coverage
- [ ] Production deployment verified
- [ ] Documentation complete

### **v1.1.0 - Performance & Scale** (Target: Dec 31, 2025)

**Scope:**
- Multi-agent parallelism
- Advanced tool sandboxing
- Observability (Grafana dashboards)
- Load testing

### **v2.0.0 - Community** (Target: Q1 2026)

**Scope:**
- Public release
- Landing page
- Installation automation
- Contributor onboarding

---

## 📈 Success Metrics

### **Code Quality**

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Unit Tests | 1,265 | 1,500+ | 🟢 84% |
| Test Coverage | 85%+ (new) | 90% | 🟢 94% |
| SonarCloud Quality Gate | Passing | Passing | 🟢 Pass |
| Technical Debt | Low | Low | 🟢 Good |

### **Architecture**

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Hexagonal Services | 6/6 | 6/6 | 🟢 100% |
| DDD Compliance | High | High | 🟢 Pass |
| API Consistency | gRPC | gRPC | 🟢 Pass |
| Bounded Contexts | Isolated | Isolated | 🟢 Pass |

### **Functionality**

| Feature | Status | Tests | Notes |
|---------|--------|-------|-------|
| Story Planning | ✅ Done | 278 | Planning Service |
| Task Workflow | ✅ Done | 138 | Workflow Service |
| Agent Execution | ✅ Done | 402 | Ray + vLLM |
| Tool Access Control | ✅ Done | 676 | RBAC L1 |
| Workflow Control | ✅ Done | 138 | RBAC L2 |
| Data Access Control | ⏳ Next | - | RBAC L3 |
| Context Assembly | ✅ Done | - | Context Service |
| Monitoring | ✅ Done | 305 | Monitoring Service |

---

## 🔗 Related Documentation

- [Architecture Decisions](docs/architecture/decisions/2025-11-06/) - Recent ADRs
- [RBAC Strategy](docs/sessions/2025-11-05/RBAC_LEVELS_2_AND_3_STRATEGY.md)
- [Deployment Guide](docs/operations/DEPLOYMENT.md)
- [Testing Guide](docs/testing/E2E_JOBS_K8S_GUIDE.md)
- [Microservices Architecture](docs/architecture/MICROSERVICES_ARCHITECTURE.md)

---

**Maintained by:** Tirso García Ibáñez (Software Architect)  
**Review Frequency:** After each milestone  
**Next Review:** Nov 14, 2025 (RBAC L3 completion)
