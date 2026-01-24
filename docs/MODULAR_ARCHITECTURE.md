# Modular Architecture

## Overview

The project has been restructured into independent modules following a monorepo pattern. Each module has its own `pyproject.toml`, test configuration, and can be built and tested independently.

## Module Structure

### Core Modules

Core modules can be used by services but are independent of each other (except for explicit dependencies):

- **@core/shared** - Shared kernel with domain concepts used across bounded contexts
- **@core/memory** - LLM session persistence and summarization
- **@core/context** - Decision graph management and context services
- **@core/orchestrator** - Multi-agent coordination and deliberation
- **@core/agents_and_tools** - Autonomous agents and tool execution
- **@core/ray_jobs** - Ray-based agent execution infrastructure
- **@core/reports** - Decision graph analytics and reporting

### Service Modules

Service modules are independent of each other but may depend on core modules:

- **@services/backlog_review_processor** - Converts backlog review deliberations into tasks (Python)
- **@services/context** - gRPC Server with NATS support for hydrated prompts (Python)
- **@services/orchestrator** - gRPC Server for multi-agent coordination (Python)
- **@services/planning** - User Story Management with FSM (Python)
- **@services/planning_ceremony_processor** - gRPC service to start ceremony executions (Python)
- **@services/ray_executor** - Executes deliberations on Ray cluster (Python)
- **@services/task_derivation** - Automatic task derivation using LLM (Python)
- **@services/workflow** - Workflow Orchestration Service (Python)
- **@services/planning-ui** - TypeScript/JavaScript UI (Astro/Vitest, independent)

## Dependencies

### Core Module Dependencies

- `core/reports` depends on `core/context`
- `core/agents_and_tools` depends on `core/shared`

### Service Module Dependencies

- `services/context` depends on `core/context`, `core/memory`, `core/reports`
- `services/orchestrator` depends on `core/orchestrator`
- `services/ray_executor` depends on `core/ray_jobs`
- `services/workflow` depends on `core/shared`
- `services/planning` depends on `core/shared`
- `services/task_derivation` depends on `core/shared`

## Installation

### Install All Modules

```bash
make install-deps
# or
./scripts/install-modules.sh
```

This installs all modules in dependency order:
1. Core modules first (shared, memory, context, orchestrator, agents_and_tools, ray_jobs, reports)
2. Service modules second (all services)

### Install a Specific Module

```bash
pip install -e core/shared
# or for a service
pip install -e services/planning
```

**Note**: When installing a service module individually, ensure its core dependencies are installed first.

## Protobuf Generation

### Generate Protos for All Modules

```bash
make generate-protos
```

This generates protobuf files for all services that have a `generate-protos.sh` script.

### Generate Protos for a Specific Module

```bash
make generate-protos-module MODULE=services/orchestrator
# or
bash services/orchestrator/generate-protos.sh
```

Each service module has its own `generate-protos.sh` script that:
- Generates its own service proto
- Generates any client protos it needs (e.g., planning generates context and orchestrator protos for its adapters)
- Fixes imports to use relative imports
- Creates `__init__.py` files

### Clean Generated Protos

```bash
make clean-protos
```

## Module Languages

Modules may use different programming languages. Test execution and coverage formats vary by language:

| Language              | Modules                                    | Test runner                                            | Coverage format                      | Sonar                                                                 |
| --------------------- | ------------------------------------------ | ------------------------------------------------------ | ----------------------------------- | --------------------------------------------------------------------- |
| **Python**            | core/*, services/* (except planning-ui)    | pytest (`scripts/test-module.sh`, `scripts/test/unit.sh`) | `coverage.xml` per module, combined  | `sonar.python.coverage.reportPaths=coverage.xml`                       |
| **TypeScript/JS**     | services/planning-ui                       | Vitest (`npm run test` / `npm run test:coverage`)       | `lcov.info`                          | `sonar.javascript.lcov.reportPaths`, `sonar.typescript.lcov.reportPaths` |
| **Go** (future)       | e.g. services/agent_executor               | `go test`                                              | `coverage.out` or similar            | Configure per SonarScanner docs                                        |

- **Python modules** are run via `make test-unit` / `make test-module MODULE=<path>`. Coverage from all Python modules is combined into a single `coverage.xml` at repo root for SonarCloud.
- **planning-ui** (TypeScript) is tested separately; CI runs `npm run test:coverage` in `services/planning-ui`. It is **not** part of `make test-unit`.
- **Other languages**: run their native test commands (e.g. `go test`). Add CI jobs and Sonar config as new modules are introduced.

## Testing

### Test All Python Modules

```bash
make test-unit
# or
bash scripts/test/unit.sh
```

This runs **Python modules only** (core + services except planning-ui). It:

- Tests **all core modules** individually (core/shared, core/memory, core/context, core/ceremony_engine, core/orchestrator, core/agents_and_tools, core/reports)
- Tests **all Python service modules** individually (backlog_review_processor, context, orchestrator, planning, planning_ceremony_processor, task_derivation, workflow)
- Runs **Ray modules** (core/ray_jobs, services/ray_executor) in a Python 3.11 environment (local or Docker)
- Generates protobuf files before running (for modules with `generate-protos.sh`)
- Emits `coverage.xml` per module, then **combines** them into a single `coverage.xml` at repo root for SonarCloud
- Cleans up generated protos after tests (success or failure)

### Test a Specific Python Module

```bash
# Core module
make test-module MODULE=core/shared
# or
./scripts/test-module.sh core/shared

# Service module
make test-module MODULE=services/orchestrator
# or
./scripts/test-module.sh services/orchestrator
```

The script (`scripts/test-module.sh`):

- Installs the module (with dev deps) if not already installed
- Generates protos if the module has `generate-protos.sh`
- **Injects module-specific env** (e.g. `CEREMONIES_DIR` for `services/planning_ceremony_processor`; see below)
- Runs pytest in the module directory
- Cleans up generated protos after tests

Works for **core** and **Python service** modules.

### Module-specific configuration

Some modules require environment variables when running tests:

- **`services/planning_ceremony_processor`**: `CEREMONIES_DIR` must point to the ceremonies config directory (e.g. `<repo>/config/ceremonies`). `make test-module MODULE=services/planning_ceremony_processor` and `make test-unit` set this automatically via `scripts/test-module.sh`. For ad‑hoc pytest runs, set `CEREMONIES_DIR` yourself.

### Test planning-ui (TypeScript/JavaScript)

```bash
cd services/planning-ui
npm ci
npm run test          # unit tests
npm run test:coverage # tests + lcov coverage
```

Coverage is written to `services/planning-ui/coverage/lcov.info`. CI uploads it for SonarCloud separately from Python coverage.

### Test with Coverage (Python)

```bash
./scripts/test-module.sh core/shared --cov-report=xml --cov-report=term-missing
```

When running `make test-unit`, each module is already invoked with `--cov-report=xml` so that combined coverage can be produced.

### Running all tests (Python + UI)

- **`make test-unit`** runs only Python unit tests.
- **`make test-all`** runs `scripts/test/all.sh`, which currently runs only `unit.sh` (Python).
- **CI** runs Python unit tests and UI tests in separate jobs, then combines coverage for SonarCloud.

To run both locally: run `make test-unit`, then `cd services/planning-ui && npm run test:coverage`.

## CI/CD

- **`.github/workflows/ci.yml`**: Runs `make test-unit` (Python), then UI tests (`npm run test:coverage` in planning-ui). Uploads `coverage.xml` (Python, combined) and `services/planning-ui/coverage/lcov.info` for SonarCloud.
- **`.github/workflows/ci-modules.yml`**: Matrix-based build per **Python** module. Each job runs `scripts/test-module.sh` for one module, uploads `coverage.xml` and `.coverage`. A **combine-coverage** job merges all Python `coverage.xml` files into one and feeds SonarCloud. planning-ui is tested in a separate job.

Coverage from all Python modules is combined; planning-ui coverage is passed separately. Both are used in SonarCloud analysis.

## Module Configuration (Python)

Each **Python** module has its own `pyproject.toml` with:
- Module name and version
- Dependencies (external and internal)
- Test configuration (pytest, pytest-asyncio, pytest-cov, pytest-timeout)
- Coverage configuration (source, omit, output paths)
- Linting configuration (ruff)

**Non-Python modules** (e.g. planning-ui) use their own config (e.g. `package.json`, Vitest).

## Best Practices

1. **Always install core modules before services** - Use `make install-deps` or `./scripts/install-modules.sh`
2. **Test modules independently** - Use `make test-module MODULE=<path>` for focused testing
3. **Keep dependencies explicit** - List all core module dependencies in service `pyproject.toml`
4. **Services are independent** - Services should not depend on each other, only on core modules

## Troubleshooting

### Module Not Found

If you get import errors, ensure the module is installed:
```bash
pip install -e <module-path>
```

### Dependency Issues

If a service fails to install, check that its core dependencies are installed first:
```bash
# Install core modules first
./scripts/install-modules.sh
```

### Test Failures

Run tests for a specific **Python** module to isolate issues:
```bash
./scripts/test-module.sh <module-path> -v
```

For **planning-ui**, run `npm run test` (or `npm run test:coverage`) in `services/planning-ui`.

