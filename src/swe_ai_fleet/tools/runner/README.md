# SWE AI Fleet Runner

This directory contains the complete implementation of the Developer Agent ↔ Runner Contract protocol for SWE AI Fleet.

## Overview

The Runner implements a standardized contract between LLM agents and containerized execution environments, supporting both local (Podman/Docker) and Kubernetes execution modes.

## Components

### 1. Container Image (`Containerfile`)

- **Base**: Ubuntu 24.04 with comprehensive toolchain
- **Tools**: kubectl, podman, docker-compose, Go 1.22.6, Python 3
- **User**: Non-root `agent` user with configurable UID/GID
- **Workspace**: `/workspace` directory for code mounting
- **Testcontainers**: Pre-configured for integration testing
- **Shim**: `agent-task` script for standardized task execution

### 2. Build System (`Makefile`)

```bash
# Build the container image
make build

# Run container interactively
make run

# Execute specific task
make task TASK=unit LANG=python

# Push to registry
make push REGISTRY=your-registry.com

# Clean up images
make clean

# Show image information
make info

# Show help
make help
```

### 3. Task Execution Shim (`agent-task`)

The `agent-task` script provides a standardized interface for task execution:

- **Tasks**: `unit`, `integration`, `e2e`, `build`
- **Languages**: `python`, `go`
- **Environment**: Automatic setup based on language
- **Logging**: Structured JSON output with timestamps
- **Artifacts**: Standardized output paths

### 4. Runner Tool (`runner_tool.py`)

Python implementation of the MCP Runner Tool with TaskSpec/TaskResult contract:

- **TaskSpec**: Declarative task specification
- **TaskResult**: Structured execution results
- **Runtime Detection**: Auto-detect Podman/Docker/Kubernetes
- **Async Execution**: Non-blocking task execution
- **Log Streaming**: Real-time log access
- **Artifact Management**: Automatic artifact collection

### 5. Examples (`examples/`)

- `task-spec-python-unit.json` - Python unit test example
- `task-spec-go-integration.json` - Go integration test example
- `task-result-success.json` - Successful execution result
- `task-result-failure.json` - Failed execution result

## Protocol Contract

### TaskSpec (Input)

```json
{
  "image": "localhost/swe-ai-fleet-runner:latest",
  "cmd": ["/bin/bash", "-lc", "agent-task"],
  "env": {
    "TASK": "unit",
    "LANG": "python",
    "REPO_URL": "https://github.com/user/repo.git",
    "REF": "main",
    "TEST_CMD": "pytest -q --junitxml=/workspace/test-reports/junit.xml"
  },
  "mounts": [
    {"type": "bind", "source": "/work/build-123", "target": "/workspace"},
    {"type": "bind", "source": "/run/podman/podman.sock", "target": "/var/run/docker.sock"}
  ],
  "timeouts": {"overallSec": 2400},
  "resources": {"cpu": "2", "memory": "4Gi"},
  "artifacts": {"paths": ["/workspace/test-reports", "/workspace/coverage"]},
  "context": {
    "case_id": "case-7429",
    "task_id": "dev-impl-authz-v2",
    "role": "developer"
  }
}
```

### TaskResult (Output)

```json
{
  "status": "passed",
  "exitCode": 0,
  "captured": {
    "logsRef": "s3://fleet-builds/build-123/logs.ndjson",
    "artifacts": [
      {"path": "/workspace/test-reports", "ref": "s3://fleet-builds/build-123/test-reports/"}
    ]
  },
  "metadata": {
    "containerId": "4b43a1c2d3e4f5g6h7i8j9k0l1m2n3o4p",
    "imageDigest": "sha256:abc123...",
    "startedAt": "2025-01-02T09:12:01Z",
    "finishedAt": "2025-01-02T09:16:44Z",
    "duration": 283,
    "case_id": "case-7429",
    "task_id": "dev-impl-authz-v2"
  }
}
```

## Usage Examples

### Local Development

```bash
# Build the runner image
cd src/swe_ai_fleet/tools/runner
make build

# Test with Python
make task TASK=unit LANG=python

# Test with Go
make task TASK=integration LANG=go
```

### Python API

```python
from runner_tool import RunnerTool, TaskSpec

# Create runner
runner = RunnerTool()

# Define task
spec = TaskSpec(
    image="localhost/swe-ai-fleet-runner:latest",
    cmd=["/bin/bash", "-lc", "agent-task"],
    env={"TASK": "unit", "LANG": "python"},
    mounts=[{"type": "bind", "source": "/tmp/test", "target": "/workspace"}],
    timeouts={"overallSec": 300},
    resources={"cpu": "1", "memory": "1Gi"},
    artifacts={"paths": ["/workspace/test-reports"]}
)

# Execute task
task_id = await runner.run_task(spec)
result = await runner.await_result(task_id)
print(f"Status: {result.status}")
```

### MCP Integration

The Runner Tool can be integrated with MCP (Model Context Protocol) clients:

```json
{
  "tool": "runner",
  "method": "run_task",
  "args": {
    "spec": {
      "image": "localhost/swe-ai-fleet-runner:latest",
      "cmd": ["/bin/bash", "-lc", "agent-task"],
      "env": {"TASK": "unit", "LANG": "python"},
      "mounts": [{"type": "bind", "source": "/work/build-123", "target": "/workspace"}],
      "timeouts": {"overallSec": 2400},
      "resources": {"cpu": "2", "memory": "4Gi"},
      "artifacts": {"paths": ["/workspace/test-reports"]}
    }
  }
}
```

## Integration with SWE AI Fleet

The Runner integrates with the SWE AI Fleet context system:

- **Redis**: Short-term plan/spec/events storage
- **Neo4j**: Graph of decisions/plan/subtasks  
- **Context Assembler**: Builds filtered context packs by role and phase

The `context.hydration_refs` in TaskSpec files reference Redis keys and Neo4j queries that the orchestrator uses to hydrate the agent's context before task execution.

## Testing

Run the test suite to verify functionality:

```bash
python3 test_runner.py
```

This will test:
- Basic Python task execution
- Go task execution
- Health check functionality
- Task cancellation
- Error handling

## Security

- **Non-root execution**: All tasks run as non-root user
- **Resource limits**: CPU and memory constraints enforced
- **Timeout protection**: Automatic task termination
- **Isolated workspace**: Mounted directories with proper permissions
- **No secrets**: All secrets injected at runtime

## Performance

- **Parallel execution**: Multiple tasks can run concurrently
- **Resource optimization**: Efficient container reuse
- **Caching**: Build/test caches mounted for performance
- **Streaming**: Real-time log streaming without blocking

## Troubleshooting

### Common Issues

1. **Permission denied**: Ensure USER_UID/USER_GID match your system
2. **Container not found**: Run `make build` to create the image
3. **Socket mounting**: Ensure Podman/Docker socket is accessible
4. **Resource limits**: Adjust CPU/memory constraints as needed

### Debug Mode

Enable debug logging:

```bash
export PYTHONPATH=/home/ia/develop/swe-ai-fleet/src
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from runner_tool import RunnerTool
# ... your code
"
```

## Contributing

When extending the Runner:

1. Follow the TaskSpec/TaskResult contract
2. Add tests for new functionality
3. Update examples with new use cases
4. Document any new environment variables or mount points
5. Ensure compatibility with both local and Kubernetes modes

