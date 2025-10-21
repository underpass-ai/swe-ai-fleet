# 🎯 Next Session: Ray Executor Hexagonal Architecture

**Milestone**: M7 - Ray Executor Microservice Refactor  
**Duration Estimate**: 4-6 hours  
**Status**: Planning  
**Priority**: HIGH (consistency with Orchestrator)

---

## 🎯 Objetivo

Refactorizar el microservicio **Ray Executor** (vLLM inference wrapper) siguiendo los **mismos principios hexagonales** que aplicamos al Orchestrator.

**Razón**: Mantener consistencia arquitectónica across all microservices.

---

## 📋 Current State Analysis

### Ray Executor Service

**Ubicación**: `services/ray-executor/` (Go) o Python wrapper?

**Funcionalidad Actual**:
- Recibe requests del Orchestrator (gRPC)
- Ejecuta jobs en Ray cluster
- Interactúa con vLLM server
- Retorna resultados al Orchestrator

**Problemas Potenciales**:
- ❓ ¿Tiene arquitectura hexagonal?
- ❓ ¿Ports/Adapters definidos?
- ❓ ¿Tests unitarios con mocks?
- ❓ ¿Dependency injection?

---

## 🏗️ Target Architecture

### Hexagonal Layers

```
services/ray-executor/
├── domain/                        ← Pure business logic
│   ├── entities/
│   │   ├── execution_request.py   ← Domain entity
│   │   ├── execution_result.py
│   │   └── vllm_config.py
│   ├── ports/                     ← Interfaces
│   │   ├── ray_executor_port.py   ← Execute on Ray
│   │   ├── llm_inference_port.py  ← Call vLLM
│   │   └── result_publisher_port.py  ← Publish results
│   └── services/                  ← Domain services
│       └── task_orchestration.py
│
├── application/                   ← Use cases
│   ├── usecases/
│   │   ├── execute_task_usecase.py
│   │   ├── generate_proposal_usecase.py
│   │   └── critique_proposal_usecase.py
│   └── services/
│       └── execution_coordinator.py
│
├── infrastructure/                ← Adapters
│   ├── adapters/
│   │   ├── ray_cluster_adapter.py       ← RayExecutorPort impl
│   │   ├── vllm_http_adapter.py         ← LLMInferencePort impl
│   │   ├── nats_result_adapter.py       ← ResultPublisherPort impl
│   │   └── grpc_server_adapter.py       ← gRPC servicer
│   ├── dto/
│   │   └── ray_executor_dto.py
│   └── handlers/
│       └── grpc_request_handler.py
│
├── server.py                      ← Entry point (DI container)
├── tests/
│   ├── domain/                    ← Unit tests (no mocks)
│   ├── application/               ← Unit tests (mock ports)
│   └── infrastructure/            ← Integration tests (real adapters)
│
└── gen/                           ← Generated protobuf (build-time)
    ├── ray_executor_pb2.py
    └── ray_executor_pb2_grpc.py
```

---

## 🎯 Refactor Checklist

### Phase 1: Analysis (30 min)
- [ ] Audit current ray-executor code structure
- [ ] Identify domain logic vs infrastructure
- [ ] Map current dependencies
- [ ] Document current API contracts (.proto)
- [ ] Create INTERACTIONS analysis (who calls, who it calls)

### Phase 2: Domain Layer (1 hour)
- [ ] Extract pure domain entities
- [ ] Define domain ports (interfaces)
- [ ] Implement domain services (if any)
- [ ] Zero infrastructure dependencies
- [ ] Unit tests for domain (no mocks needed)

### Phase 3: Application Layer (1.5 hours)
- [ ] Create use cases (ExecuteTask, GenerateProposal, etc.)
- [ ] Implement application services
- [ ] Define port dependencies (constructor injection)
- [ ] Unit tests with mock ports
- [ ] Verify no infrastructure leakage

### Phase 4: Infrastructure Layer (2 hours)
- [ ] Implement RayClusterAdapter (RayExecutorPort)
- [ ] Implement VLLMHttpAdapter (LLMInferencePort)
- [ ] Implement NatsResultAdapter (ResultPublisherPort)
- [ ] Implement gRPC server adapter
- [ ] Integration tests with real Ray/vLLM/NATS

### Phase 5: Entry Point & DI (1 hour)
- [ ] Refactor server.py as DI container
- [ ] Wire all dependencies
- [ ] Initialize adapters
- [ ] Inject into use cases
- [ ] Verify startup

### Phase 6: Testing (1 hour)
- [ ] Unit tests: domain + application
- [ ] Integration tests: adapters
- [ ] E2E: full Ray execution
- [ ] Coverage: >90% on new refactored code

### Phase 7: Documentation (30 min)
- [ ] RAY_EXECUTOR_HEXAGONAL_PRINCIPLES.md
- [ ] Update HEXAGONAL_ARCHITECTURE_PRINCIPLES.md (add Ray Executor example)
- [ ] Session summary
- [ ] Deployment guide

---

## 📊 Success Criteria

### Architecture ✅
- [ ] Hexagonal layers clearly separated
- [ ] Ports defined as interfaces
- [ ] Adapters implement ports
- [ ] Domain has zero infrastructure deps
- [ ] Dependency injection throughout

### Quality ✅
- [ ] Unit tests >90% coverage
- [ ] Zero code smells (Ruff)
- [ ] SOLID compliance
- [ ] No circular dependencies

### Documentation ✅
- [ ] Normative doc (like Orchestrator)
- [ ] Code analysis with diagrams
- [ ] Session summary

---

## 🎓 Lessons from Orchestrator Refactor

### What Worked Well ✅

1. **Start with Domain**: Extract entities first, then ports
2. **Application Services**: Use for complex orchestration (AutoDispatchService pattern)
3. **Constructor Injection**: All dependencies via __init__
4. **Mock Ports in Tests**: Unit tests fast and isolated
5. **Documentation First**: Write principles BEFORE coding

### Pitfalls to Avoid ❌

1. **Don't assume API structure**: Check .proto FIRST
2. **No dynamic imports**: Always constructor injection
3. **Fail-fast validation**: Check preconditions early
4. **Tests before integration**: Write use case tests, then integrate

---

## 📝 Pre-Session Preparation

### Read Before Starting
1. `HEXAGONAL_ARCHITECTURE_PRINCIPLES.md` - Our principles
2. `specs/fleet/ray_executor/v1/ray_executor.proto` - API contract
3. `services/ray-executor/` - Current code (if Go, may need rewrite in Python)
4. `src/swe_ai_fleet/ray_jobs/` - Existing Ray integration code

### Questions to Answer
1. ¿Ray Executor está en Go o Python?
2. ¿Qué servicios lo llaman? (Orchestrator principalmente)
3. ¿Qué servicios llama? (Ray cluster, vLLM server, NATS)
4. ¿Necesita ser público o privado? (privado, ClusterIP)
5. ¿Qué datos maneja? (ExecutionRequest, ExecutionResult)

### Create Before Coding
- `RAY_EXECUTOR_INTERACTIONS.md` (following memory [[memory:9734181]])
- Map all interactions BEFORE designing architecture

---

## 🎯 Expected Outcome

### After Refactor

```
Ray Executor Microservice:
✅ Hexagonal architecture (like Orchestrator)
✅ Ports & Adapters clearly separated
✅ >90% test coverage
✅ Zero code smells
✅ Normative documentation
✅ Production-ready deployment
```

### Consistency Across Services

```
Orchestrator:  ✅ Hexagonal (M5-M6 complete)
Ray Executor:  📋 Hexagonal (M7 planned)
Context:       📋 Hexagonal (M8 future)
Planning:      ✅ Already clean (Go, simple)
StoryCoach:    ✅ Already clean (Go, simple)
Workspace:     ✅ Already clean (Go, simple)
```

**Goal**: All Python microservices follow same hexagonal pattern.

---

## 📚 References

### Our Docs
- [HEXAGONAL_ARCHITECTURE_PRINCIPLES.md](HEXAGONAL_ARCHITECTURE_PRINCIPLES.md)
- [ORCHESTRATOR_HEXAGONAL_CODE_ANALYSIS.md](ORCHESTRATOR_HEXAGONAL_CODE_ANALYSIS.md)
- [CLEAN_ARCHITECTURE_REFACTOR_20251020.md](docs/sessions/2025-10-20/)

### External
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Ports and Adapters](https://herbertograca.com/2017/09/21/ports-adapters-architecture/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

## ⏰ Time Estimate

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Analysis | 30 min | 0.5h |
| Domain | 1 hour | 1.5h |
| Application | 1.5 hours | 3h |
| Infrastructure | 2 hours | 5h |
| Entry Point | 1 hour | 6h |
| Testing | 1 hour | 7h |
| Documentation | 30 min | 7.5h |

**Total**: ~7-8 hours (full day session)

---

## 🎯 Next Session Plan

```bash
# 1. Session start
git checkout main
git pull origin main
git checkout -b feature/ray-executor-hexagonal

# 2. Analysis phase
# Read specs, current code, create INTERACTIONS.md

# 3. Refactor
# Follow checklist above

# 4. Test
make test-unit  # Should pass with >90% coverage

# 5. Document
# Create RAY_EXECUTOR_HEXAGONAL_PRINCIPLES.md

# 6. Deploy & verify
# Build, push, deploy to K8s, verify E2E

# 7. Commit & push
git push origin feature/ray-executor-hexagonal
# Create PR
```

---

## 💡 Key Success Factors

1. ✅ **Follow Orchestrator pattern** (proven successful)
2. ✅ **Document BEFORE code** (INTERACTIONS.md first)
3. ✅ **Test as you go** (not at the end)
4. ✅ **Same rigor** (normative docs, clean code)
5. ✅ **Production verify** (deploy to K8s, test E2E)

---

**Ready for**: Next session (M7)  
**Reference**: This session (M5-M6) as template  
**Expected**: Same quality, same rigor, same success 🚀

---

**Created**: 21 October 2025  
**For Session**: M7 - Ray Executor Hexagonal Refactor  
**Estimated**: 7-8 hours  
**Outcome**: Production-ready hexagonal Ray Executor

