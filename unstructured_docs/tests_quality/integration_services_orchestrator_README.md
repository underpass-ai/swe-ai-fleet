# Orchestrator Service E2E Tests

E2E tests for the Orchestrator Service using real infrastructure (NATS, Redis, Orchestrator Service) in containers.

## 🎯 What These Tests Cover

### Test Files
- **`test_deliberate_e2e.py`** (7 tests) - Multi-agent deliberation
- **`test_orchestrate_e2e.py`** (8 tests) - Complete task workflow
- **`test_realistic_workflows_e2e.py`** (5 tests) - Real-world scenarios

### Main RPC Endpoints
1. ✅ **Deliberate** - Multi-agent peer review and consensus
2. ✅ **Orchestrate** - Complete task execution workflow
3. ✅ **CreateCouncil** - Council management
4. ✅ **GetStatus** - Health and observability

### Realistic Scenarios
- ✅ Complete task lifecycle (Planning → Deliberation → Selection → Execution)
- ✅ Multi-phase story workflow (ARCHITECT → DEV → QA → DEVOPS)
- ✅ Parallel task orchestration (3 tasks simultaneously)
- ✅ Complex consensus building (multi-round deliberation)
- ✅ Council management and reuse

---

## 📋 Prerequisites

### 1. Container Runtime
**Podman** (Docker is paid software - not used in this project)

```bash
# Check Podman
podman --version
```

### 2. podman-compose
```bash
# Install
pip install podman-compose

# Verify
podman-compose --version
```

---

## 🚀 Running E2E Tests

### Quick Start

```bash
# From project root
./tests/integration/services/orchestrator/run-e2e.sh
```

This script:
1. Builds test and service images
2. Starts NATS, Redis, Orchestrator Service
3. Waits for all services to be healthy
4. Runs all E2E tests
5. Cleans up containers

### Manual Execution

```bash
# Start infrastructure
podman-compose -f tests/integration/services/orchestrator/docker-compose.e2e.yml up -d

# Wait for services (30-60 seconds)
sleep 60

# Run tests
podman-compose -f tests/integration/services/orchestrator/docker-compose.e2e.yml run --rm tests

# Cleanup
podman-compose -f tests/integration/services/orchestrator/docker-compose.e2e.yml down -v
```

---

## 🏗️ Infrastructure

### Services Started

| Service | Image | Port (Host) | Port (Container) |
|---------|-------|-------------|------------------|
| **NATS** | `nats:2.10-alpine` | 24222 | 4222 |
| **Redis** | `redis:7-alpine` | 26379 | 6379 |
| **Orchestrator** | Local build | 50055 | 50055 |

**Note**: Different ports than Context Service to avoid conflicts.

### Healthchecks

All services have healthchecks before tests run:
- **NATS**: Monitoring endpoint (`/healthz`)
- **Redis**: `PING` command
- **Orchestrator**: gRPC channel ready check

---

## 🧪 Test Structure

```
tests/integration/services/orchestrator/
├── conftest.py                      # Fixtures
├── docker-compose.e2e.yml          # Infrastructure definition
├── Dockerfile.test                 # Test container
├── run-e2e.sh                      # Execution script
├── requirements-test.txt           # Test dependencies
├── test_deliberate_e2e.py          # Deliberate endpoint tests
├── test_orchestrate_e2e.py         # Orchestrate endpoint tests
├── test_realistic_workflows_e2e.py # Realistic scenarios
└── README.md                       # This file
```

---

## 📊 Test Coverage

### Deliberate Endpoint (7 tests)
- ✅ Basic deliberation
- ✅ Multiple rounds
- ✅ Different roles
- ✅ With constraints
- ✅ Error handling (empty task, invalid role)
- ✅ Convergence and consensus

### Orchestrate Endpoint (8 tests)
- ✅ Basic orchestration
- ✅ With context integration
- ✅ Different roles
- ✅ With constraints
- ✅ Error handling
- ✅ Winner selection quality
- ✅ All agents contribution

### Realistic Workflows (5 tests)
- ✅ Complete task lifecycle
- ✅ Multi-phase story workflow (4 roles)
- ✅ Parallel task orchestration (3 tasks)
- ✅ Quality improvement with rounds
- ✅ Council management

**Total: 20 E2E tests**

---

## 🎯 What These Tests Validate

### 1. Multi-Agent Coordination
- ✅ Multiple agents participate in deliberation
- ✅ All agents contribute proposals
- ✅ No race conditions in parallel execution
- ✅ Unique agent IDs maintained

### 2. Consensus Building
- ✅ Winner is selected based on scoring
- ✅ All candidates are evaluated
- ✅ Best proposal wins
- ✅ Metadata is tracked

### 3. Role-Based Routing
- ✅ Different roles (DEV, QA, ARCHITECT, DEVOPS, DATA)
- ✅ Role-specific councils
- ✅ Correct role handling

### 4. Complete Workflows
- ✅ Planning → Orchestration → Selection
- ✅ Multi-phase stories (ARCHITECT → DEV → QA → DEVOPS)
- ✅ No data loss between phases
- ✅ Execution IDs tracked

### 5. Error Handling
- ✅ Empty task descriptions
- ✅ Invalid roles
- ✅ Missing parameters
- ✅ Graceful degradation

---

## 🔧 Environment Variables

Tests use these environment variables when running in containers:

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_HOST` | `localhost` | Orchestrator service hostname |
| `REDIS_HOST` | `localhost` | Redis hostname |
| `NATS_HOST` | `localhost` | NATS hostname |

---

## 📈 Performance

**Typical execution times:**
- Infrastructure startup: 30-60 seconds (first run)
- Infrastructure startup: 10-20 seconds (cached images)
- Per test: 200ms - 2s (depending on deliberation rounds)
- **Total test suite: ~30-60 seconds**

---

## 🎓 Best Practices

### ✅ DO
- Use fixtures for service clients (`orchestrator_stub`)
- Generate unique test IDs (`test_task_id` fixture)
- Verify response structure AND semantics
- Test error conditions
- Test parallel execution

### ❌ DON'T
- Hardcode task IDs (use fixtures)
- Skip error handling tests
- Make tests dependent on execution order
- Commit generated `*_pb2.py` files

---

## 🚀 Next Steps

### Planned Enhancements
1. **NATS Event Verification** - Verify `orchestrator.events` published
2. **Context Service Integration** - E2E with real Context Service
3. **Performance Benchmarks** - Deliberation latency SLAs
4. **Chaos Testing** - NATS/Redis failures mid-orchestration
5. **Load Testing** - 100+ concurrent orchestrations

---

**Status**: 🚧 In Development  
**Target Quality**: ⭐⭐⭐⭐⭐ 9/10 (matching Context Service)  
**Methodology**: Replicated from Context Service success

