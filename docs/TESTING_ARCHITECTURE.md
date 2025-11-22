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

### 🔹 Level 2: Integration Tests (Medium)
-   **Scope**: Infrastructure Adapters.
-   **Dependencies**: **REAL**. Use Docker containers for NATS, Neo4j, Redis.
-   **Location**: `tests/integration/`.
-   **Tools**: `pytest`, `testcontainers` (or pre-provisioned Docker env).
-   **Target**: Verify that adapters correctly talk to external systems.
-   **Execution Time**: Seconds.

```python
# Example Integration Test (Adapter)
@pytest.mark.integration
async def test_neo4j_adapter_save():
    adapter = Neo4jAdapter(uri="bolt://localhost:7687", ...)
    await adapter.save(my_entity)
    result = await adapter.get(my_entity.id)
    assert result == my_entity
```

### 🔻 Level 3: E2E Tests (Slow)
-   **Scope**: Full system flows (User -> API -> DB).
-   **Dependencies**: Full deployed environment (K8s or Compose).
-   **Location**: `tests/e2e/`.
-   **Tools**: `pytest`, public gRPC clients.
-   **Target**: Critical user journeys (Happy Path).

---

## 2. Mandatory Requirements

1.  **Tests Required**: Every new class or function MUST have accompanying tests.
2.  **No Flakiness**: Flaky tests are treated as failures. Fix them immediately.
3.  **Mock Ports, Not Internals**: When testing Use Cases, mock the *Port Interface*, not the concrete Adapter class.
4.  **Coverage**: PRs with < 90% coverage on new code will be blocked.
5.  **Clean Teardown**: Integration tests must clean up their data/state.

---

## 3. Tools & Libraries

-   **Runner**: `pytest`
-   **Async**: `pytest-asyncio`
-   **Mocking**: `unittest.mock` (Standard lib)
-   **Coverage**: `pytest-cov`
-   **Linting**: `ruff`

## 4. Running Tests

```bash
# Run all unit tests (fast)
make test-unit

# Run integration tests (requires docker)
make test-integration

# Run everything with coverage
make test-all
```

