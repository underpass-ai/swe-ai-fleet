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

- **@services/backlog_review_processor** - Converts backlog review deliberations into tasks
- **@services/context** - gRPC Server with NATS support for hydrated prompts
- **@services/orchestrator** - gRPC Server for multi-agent coordination
- **@services/planning** - User Story Management with FSM
- **@services/ray_executor** - Executes deliberations on Ray cluster
- **@services/task_derivation** - Automatic task derivation using LLM
- **@services/workflow** - Workflow Orchestration Service
- **@services/planning-ui** - TypeScript/JavaScript UI (independent)

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

## Testing

### Test All Modules

```bash
make test-unit
# or
bash scripts/test/unit.sh
```

Tests automatically:
- Test **all core modules individually** (core/shared, core/memory, core/context, etc.)
- Test **all service modules individually** (services/orchestrator, services/planning, etc.)
- Generate protobuf files before running (for services that need them)
- Combine coverage reports from all modules
- **Clean up generated protos after tests complete** (success or failure)

### Test a Specific Module

```bash
# Test a core module
make test-module MODULE=core/shared
# or
./scripts/test-module.sh core/shared

# Test a service module
make test-module MODULE=services/orchestrator
# or
./scripts/test-module.sh services/orchestrator
```

The test script automatically:
- Installs the module if not already installed
- Generates protos if the module has a `generate-protos.sh` script
- Runs tests in the module directory
- **Automatically cleans up generated protos after tests complete** (success or failure)

Works for both **core modules** and **service modules**.

### Test with Coverage

```bash
./scripts/test-module.sh core/shared --cov-report=xml --cov-report=html
```

## CI/CD

The CI pipeline (`.github/workflows/ci-modules.yml`) builds and tests each module independently using a matrix strategy. Each module:
- Installs its dependencies
- Generates protobuf files (if needed)
- Runs tests
- Uploads coverage reports

Coverage reports are then combined for SonarCloud analysis.

## Module Configuration

Each module has its own `pyproject.toml` with:
- Module name and version
- Dependencies (external and internal)
- Test configuration (pytest)
- Coverage configuration
- Linting configuration (ruff)

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

Run tests for a specific module to isolate issues:
```bash
./scripts/test-module.sh <module-path> -v
```

