# SWE AI Fleet - API Documentation

This directory contains auto-generated API documentation from Protocol Buffer definitions.

## Services

- [Context Service](context.md) - Decision graph and timeline management
- [Orchestrator Service](orchestrator.md) - Multi-agent deliberation coordination
- [Ray Executor Service](ray_executor.md) - Distributed task execution
- [Planning Service](planning.md) - User story and workflow management
- [StoryCoach Service](storycoach.md) - Story refinement and validation
- [Workspace Service](workspace.md) - Code evaluation and rigor assessment

## Version

Current API version: v1.0.0

## How to Read

Each service has its own markdown file. Expand the details section to view the complete proto definition.

## Interactive API Testing 🧪

### Using grpcui (Web UI)

**grpcui** provides a Swagger-like web interface for testing gRPC endpoints interactively.

#### Installation

```bash
# Option 1: Using the install script
bash scripts/install-grpcui.sh

# Option 2: Using Go
go install github.com/fullstorydev/grpcui/cmd/grpcui@latest
```

#### Usage

```bash
# From the specs/ directory

# Test all services (requires server reflection)
make grpcui-serve

# Test specific service with proto file
make grpcui-serve SERVICE=orchestrator

# Custom host and port
make grpcui-serve HOST=localhost PORT=50055 SERVICE=orchestrator
```

The grpcui web UI will open at `http://localhost:8080` where you can:
- Browse available gRPC methods
- Fill out request forms
- Execute calls and view responses
- Test streaming RPCs
- View request/response schemas

### Using grpcurl (CLI)

**grpcurl** is a CLI tool for testing gRPC endpoints.

```bash
# List services
grpcurl -plaintext localhost:50055 list

# Describe service
grpcurl -plaintext localhost:50055 describe fleet.orchestrator.v1.OrchestratorService

# Call method
grpcurl -plaintext -d '{"role":"DEV"}' \
  localhost:50055 fleet.orchestrator.v1.OrchestratorService/ListCouncils
```

## More Information

- [API Versioning Strategy](../../docs/API_VERSIONING_STRATEGY.md)
- [Full Repository](../../README.md)
- [Proto Versioning Guide](../../docs/specs/PROTO_VERSIONING_GUIDE.md)
- [Tooling Setup](../../docs/TOOLING_SETUP.md)
