# E2E Jobs Refactor Status

Version: 1.1
Last Updated: 2025-01-02
Status: 🔄 In Progress

---

## Executive Summary

This document tracks the migration of E2E tests from local execution to Kubernetes Jobs. Running tests inside the cluster provides direct access to internal services (`*.svc.cluster.local`) without port-forwarding, ensuring tests run in the same environment as production.

**Migration Progress: 3/15+ test suites migrated (~20%)**

---

## Completed Migrations ✅

### 1. `test-vllm-agent-tools-e2e`
- **Job:** `test-vllm-agent-tools-e2e`
- **Test File:** `tests/e2e/orchestrator/test_orchestrator_with_tools_e2e.py`
- **Test Function:** `test_vllm_agent_with_smart_context`
- **Status:** ✅ Implemented
- **Manifest:** `deploy/k8s/99-test-vllm-agent-tools-e2e.yaml`
- **Image:** `registry.underpassai.com/swe-fleet/test-vllm-agent-tools-e2e:v0.1.0`
- **Dependencies:**
  - vLLM server (`vllm-server.swe-ai-fleet.svc.cluster.local:8000`)
  - Context Service (`context.swe-ai-fleet.svc.cluster.local:50054`)
  - Orchestrator (`orchestrator.swe-ai-fleet.svc.cluster.local:50055`)
- **Features:**
  - Tests agent execution with smart context filtering
  - Validates tool execution in temporary workspace
  - Uses init container to clone repo
  - Non-root user (UID 1000)

### 2. `test-orchestrator-deliberation-e2e`
- **Job:** `test-orchestrator-deliberation-e2e`
- **Test File:** `tests/e2e/orchestrator/test_deliberate_e2e.py` (custom script)
- **Status:** ✅ Implemented
- **Manifest:** `deploy/k8s/99-test-orchestrator-deliberation-e2e.yaml`
- **Image:** `registry.underpassai.com/swe-fleet/test-orchestrator-deliberation-e2e:v0.1.3`
- **Dependencies:**
  - Orchestrator gRPC (`orchestrator.swe-ai-fleet.svc.cluster.local:50055`)
  - NATS JetStream (`nats.swe-ai-fleet.svc.cluster.local:4222`)
- **Features:**
  - Tests deliberation flow via gRPC
  - Subscribes to NATS subjects (`orchestration.>`, `agent.results.>`)
  - Validates event-driven flow
  - Generates protobuf stubs in Dockerfile

### 3. `test-ray-vllm-e2e`
- **Job:** `test-ray-vllm-e2e`
- **Test File:** `tests/e2e/test_ray_vllm_e2e.py`
- **Test Functions:**
  - `test_basic_deliberation`
  - `test_different_roles`
  - `test_proposal_quality`
  - `test_proposal_diversity`
  - `test_complex_scenario`
  - `test_performance_scaling`
- **Status:** ✅ Implemented
- **Manifest:** `deploy/k8s/99-test-ray-vllm-e2e.yaml`
- **Image:** `registry.underpassai.com/swe-fleet/test-ray-vllm-e2e:v0.1.1`
- **Dependencies:**
  - Orchestrator gRPC (`orchestrator.swe-ai-fleet.svc.cluster.local:50055`)
  - vLLM server (`vllm-server.swe-ai-fleet.svc.cluster.local:8000`)
- **Features:**
  - Tests deliberation flow with multiple roles (DEV, QA, ARCHITECT, DEVOPS)
  - Validates proposal quality, diversity, and relevance
  - Performance scaling tests with different agent counts
  - Protobuf generation in Dockerfile
  - Uses pytest fixtures from `tests/e2e/conftest.py`

### 4. `test-architecture-e2e` (Legacy)
- **Job:** `test-architecture-e2e`
- **Status:** ⚠️ Exists but may need update
- **Manifest:** `deploy/k8s/99-test-architecture-e2e.yaml`
- **Image:** `registry.underpassai.com/swe-ai-fleet/architecture-test:latest`
- **Note:** This appears to be an older job; may need review/refresh to match current patterns

---

## Pending Migrations 📋

### High Priority

#### 1. `test_full_architecture_deliberation`
- **Test File:** `tests/e2e/test_architecture_e2e.py`
- **Test Function:** `test_full_architecture_deliberation`
- **Status:** 🔴 Not Started
- **Dependencies:**
  - Orchestrator gRPC
  - Ray cluster
  - vLLM server
  - NATS JetStream
- **Estimated Complexity:** Medium
- **Blockers:** None

#### 2. ~~`test_ray_vllm_e2e` (Multiple Tests)~~ ✅ MIGRATED
- **Status:** ✅ Completed (see Completed Migrations section)

#### 3. `test_ray_vllm_with_tools_e2e`
- **Test File:** `tests/e2e/test_ray_vllm_with_tools_e2e.py`
- **Status:** 🔴 Not Started
- **Dependencies:**
  - Orchestrator gRPC
  - Context Service
  - Ray cluster
  - vLLM server
  - Workspace with code
- **Estimated Complexity:** High (tool execution + workspace setup)
- **Blockers:** None

#### 4. `test_full_orchestrator_to_tools_flow`
- **Test File:** `tests/e2e/orchestrator/test_orchestrator_with_tools_e2e.py`
- **Test Function:** `test_full_orchestrator_to_tools_flow`
- **Status:** 🟡 Skipped (API not implemented)
- **Note:** Currently skipped with `pytest.skip("OrchestrateFullRequest API not implemented yet")`
- **Dependencies:** OrchestrateWithTools API
- **Blockers:** API implementation required

### Medium Priority

#### 5. Context Service E2E Tests
- **Test Files:**
  - `tests/e2e/context/test_grpc_e2e.py`
  - `tests/e2e/context/test_persistence_e2e.py`
  - `tests/e2e/context/test_project_case_e2e.py`
  - `tests/e2e/context/test_project_plan_e2e.py`
  - `tests/e2e/context/test_project_subtask_e2e.py`
  - `tests/e2e/context/test_projector_coordinator_e2e.py`
  - `tests/e2e/context/test_realistic_workflows_e2e.py`
- **Status:** 🔴 Not Started
- **Dependencies:**
  - Context Service gRPC
  - Neo4j
  - Redis/Valkey
- **Estimated Complexity:** Medium
- **Blockers:** None

#### 6. Orchestrator Additional Tests
- **Test Files:**
  - `tests/e2e/orchestrator/test_orchestrate_e2e.py`
  - `tests/e2e/orchestrator/test_ray_vllm_async_e2e.py`
- **Status:** 🔴 Not Started
- **Dependencies:**
  - Orchestrator gRPC
  - Ray cluster
  - NATS JetStream
- **Estimated Complexity:** Medium

#### 7. System Integration Tests
- **Test Files:**
  - `tests/e2e/test_system_e2e.py`
  - `tests/e2e/comprehensive_system_test.sh`
  - `tests/e2e/test_full_async_system.sh`
- **Status:** 🔴 Not Started
- **Dependencies:** All services
- **Estimated Complexity:** High (multiple services)
- **Note:** May benefit from test orchestration job that runs multiple sub-jobs

---

## Migration Patterns & Standards

### Standard Structure
```
jobs/test-<name>-e2e/
├── Dockerfile          # Python 3.13, pytest, dependencies
└── run_test.py         # Runner script with colored output

deploy/k8s/
└── 99-test-<name>-e2e.yaml  # Job manifest with:
                              - Init container (git clone)
                              - Test container
                              - Environment variables (FQDNs)
                              - ServiceAccount + RBAC (if needed)
```

### Key Practices
1. **Fully Qualified Domain Names (FQDNs):**
   - Always use `*.svc.cluster.local` format
   - Example: `orchestrator.swe-ai-fleet.svc.cluster.local:50055`

2. **Image Naming:**
   - Registry: `registry.underpassai.com/swe-fleet/` (or `swe-ai-fleet/` for legacy)
   - Format: `test-<name>-e2e:v<version>`
   - Version increment on breaking changes

3. **Init Container Pattern:**
   ```yaml
   initContainers:
     - name: clone-repo
       image: docker.io/alpine/git:v2.43.0
       command: [clone, set permissions]
   volumes:
     - name: source-code
       emptyDir: {}
   ```

4. **Security:**
   - Non-root user (UID 1000)
   - `readOnlyRootFilesystem: false` (for git operations)
   - Minimal RBAC (if needed)

5. **Resource Limits:**
   ```yaml
   resources:
     requests:
       cpu: "200m"
       memory: "512Mi"
     limits:
       cpu: "1000m"
       memory: "2Gi"
   ```

---

## Known Issues & Blockers

### Resolved ✅
1. ✅ Promtail pipeline stages config (fixed: use `null` instead of empty array)
2. ✅ Loki DNS resolution (fixed: deployed Loki service)
3. ✅ NATS stream subscription errors (fixed: initialized streams via `nats-streams-init` job)
4. ✅ Job template immutability (workaround: delete job before apply)

### Open Issues 🟡
1. **test_full_orchestrator_to_tools_flow:** API `OrchestrateWithTools` not implemented
   - **Status:** Blocked on implementation
   - **Action:** Track in product backlog

2. **Job Cleanup:** Jobs persist after completion (using `ttlSecondsAfterFinished`)
   - **Current:** Manual cleanup or TTL-based
   - **Future:** Consider Argo Workflows or Tekton for test orchestration

3. **Test Reports:** No central aggregation of test results
   - **Future:** Consider test result storage (S3, PVC) or notification (Slack, email)

---

## Next Steps

### Immediate (Next Sprint)
1. **Migrate `test_full_architecture_deliberation`**
   - Create `jobs/test-architecture-full-e2e/`
   - Port test to use FQDNs
   - Validate against current architecture

2. **Document test execution workflow**
   - How to build and push job images
   - How to trigger jobs (kubectl, CI/CD)
   - How to view logs and results

### Short Term (Next 2-4 Weeks)
1. **Context Service E2E Tests:** Migrate 7+ context tests
2. **System Integration Tests:** Migrate comprehensive system tests
3. **Test Orchestration:** Consider test runner job that triggers multiple sub-jobs

### Long Term
1. **CI/CD Integration:** Add e2e jobs to GitHub Actions / GitLab CI
2. **Test Result Dashboard:** Aggregate results in Grafana or similar
3. **Test Scheduling:** Regular e2e runs (nightly, pre-release)

---

## Migration Checklist Template

For each new migration:

- [ ] Create `jobs/test-<name>-e2e/Dockerfile`
- [ ] Create `jobs/test-<name>-e2e/run_test.py`
- [ ] Create `deploy/k8s/99-test-<name>-e2e.yaml`
- [ ] Build and push image to registry
- [ ] Test job locally in cluster
- [ ] Verify test passes with all dependencies
- [ ] Update this status document
- [ ] Update `E2E_JOBS_MIGRATION_GUIDE.md` if patterns change

---

## References

- [E2E Jobs Migration Guide](./E2E_JOBS_MIGRATION_GUIDE.md) - Step-by-step guide for creating new jobs
- [Makefile](../Makefile) - Build and deployment targets (if applicable)
- [Orchestrator Architecture](../../docs/architecture/AGENTS_AND_TOOLS_ARCHITECTURE.md) - System design context

---

## Contributing

When migrating a test:
1. Follow the standard structure above
2. Update this status document with your migration
3. Test thoroughly in cluster before marking complete
4. Document any deviations from standard patterns

