# Testing Architecture

**Version**: 1.0.0
**Status**: Normative

This document outlines the testing strategy, pyramid, and requirements for the SWE AI Fleet project.

---

## 1. The Testing Pyramid

We adhere to a strict testing pyramid to ensure speed and reliability.

### 🔼 Level 1: Unit Tests (Fast)
-   **Scope**: Domain logic, Use Cases, Pure functions.
-   **Dependencies**: **MOCKED**. Never hit the network, disk, or DB.
-   **Location**: `tests/unit/` or `services/<name>/tests/unit/`.
-   **Tools**: `pytest`, `unittest.mock`, `pytest-mock`.
-   **Target Coverage**: 90%+.
-   **Execution Time**: < 100ms per test.

```python
# Example Unit Test (Use Case)
def test_execute_task_success():
    mock_port = Mock(spec=MessagingPort)
    use_case = ExecuteTaskUseCase(mock_port)
    use_case.execute(...)
    mock_port.publish.assert_called_once()
```

### 🔹 Level 2: Integration Tests (Medium) - **TO BE REIMPLEMENTED**
-   **Status**: ⚠️ **Removed** - Will be reimplemented from scratch.
-   **Scope**: Infrastructure Adapters.
-   **Dependencies**: **REAL**. Use Docker containers for NATS, Neo4j, Redis.
-   **Location**: `tests/integration/` (to be created).
-   **Tools**: `pytest`, `testcontainers` (or pre-provisioned Docker env).
-   **Target**: Verify that adapters correctly talk to external systems.
-   **Execution Time**: Seconds.

> **Note**: Previous integration tests were removed as they were obsolete. New integration tests will be implemented following current architecture patterns.

### 🔻 Level 3: E2E Tests (Slow) - **TO BE REIMPLEMENTED**
-   **Status**: ⚠️ **Removed** - Will be reimplemented from scratch.
-   **Scope**: Full system flows (User -> API -> DB).
-   **Dependencies**: Full deployed environment (K8s or Compose).
-   **Location**: `tests/e2e/` (to be created).
-   **Tools**: `pytest`, public gRPC clients.
-   **Target**: Critical user journeys (Happy Path).

> **Note**: Previous E2E tests were removed as they were obsolete. New E2E tests will be implemented following current architecture patterns.

---

## 2. Mandatory Requirements

1.  **Tests Required**: Every new class or function MUST have accompanying tests.
2.  **No Flakiness**: Flaky tests are treated as failures. Fix them immediately.
3.  **Mock Ports, Not Internals**: When testing Use Cases, mock the *Port Interface*, not the concrete Adapter class.
4.  **Coverage**: PRs with < 90% coverage on new code will be blocked.
5.  **Clean Teardown**: Integration tests (when reimplemented) must clean up their data/state.

---

## 3. Tools & Libraries

### Python (core and most services)

-   **Runner**: `pytest`
-   **Async**: `pytest-asyncio`
-   **Mocking**: `unittest.mock` (Standard lib)
-   **Coverage**: `pytest-cov`
-   **Linting**: `ruff`

### TypeScript/JavaScript (planning-ui)

-   **Runner**: Vitest
-   **Coverage**: Vitest + `@vitest/coverage-v8` → `lcov.info`

### Other languages

Modules in other languages (e.g. Go) use their native test runners and coverage tools. Add corresponding CI jobs and Sonar config when introducing such modules.

---

## 4. Running Tests

### Python modules

```bash
# Run all Python unit tests (core + services except planning-ui)
make test-unit

# Run tests for a specific Python module
make test-module MODULE=core/shared
make test-module MODULE=services/planning

# Run all tests (currently unit tests only)
make test-all
```

`make test-unit` runs `scripts/test/unit.sh`, which invokes `scripts/test/test-module.sh` for each Python module (CORE_MODULES, SERVICE_MODULES, Ray modules). Each module emits `coverage.xml`; these are combined into a single `coverage.xml` at repo root for SonarCloud.

### TypeScript/JavaScript (planning-ui)

```bash
cd services/planning-ui
npm run test           # unit tests
npm run test:coverage  # tests + lcov coverage
```

Coverage is written to `services/planning-ui/coverage/lcov.info`. CI runs these tests in a separate job and passes lcov to SonarCloud.

### Module-specific setup

Some Python modules require environment variables when running tests (e.g. `CEREMONIES_DIR` for `services/planning_ceremony_processor`). `make test-module` and `make test-unit` set these via `scripts/test/test-module.sh`. For ad‑hoc pytest runs, set them manually.

See **Modular Architecture** (`docs/MODULAR_ARCHITECTURE.md`) for the full list of modules, languages, and CI behaviour.

> **Note**: Integration and E2E test commands have been removed. They will be re-added when new tests are implemented.

