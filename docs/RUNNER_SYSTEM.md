# Runner System Documentation - SWE AI Fleet

## 🎯 Overview

The Runner System is a critical component of SWE AI Fleet that implements the **Developer Agent ↔ Runner Contract** protocol. It provides standardized, secure, and traceable execution of development tasks in containerized environments.

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Agent LLM     │───▶│   Runner Tool    │───▶│   Container     │
│   (MCP Client)  │    │   (MCP Server)   │    │   Execution     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Context       │    │   TaskSpec      │    │   agent-task    │
│   Assembly      │    │   Validation    │    │   Shim          │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Redis/Neo4j   │    │   Policy Engine  │    │   Testcontainers│
│   Integration   │    │   (Future)       │    │   Services      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Protocol Contract

#### TaskSpec (Input)
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

#### TaskResult (Output)
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

## 🔧 Implementation Details

### 1. Container Image (`Containerfile`)

The runner container provides a comprehensive development environment:

- **Base**: Ubuntu 24.04 with comprehensive toolchain
- **Tools**: kubectl, podman, docker-compose, Go 1.22.6, Python 3
- **User**: Non-root `agent` user with configurable UID/GID
- **Workspace**: `/workspace` directory for code mounting
- **Testcontainers**: Pre-configured for integration testing
- **Shim**: `agent-task` script for standardized task execution

### 2. agent-task Shim

The `agent-task` script provides a standardized interface for task execution:

#### Supported Tasks
- `unit`: Unit tests
- `integration`: Integration tests with Testcontainers
- `e2e`: End-to-end tests
- `build`: Build tasks

#### Supported Languages
- `python`: Python development with pytest
- `go`: Go development with go test

#### Features
- **Environment Setup**: Automatic language-specific configuration
- **Structured Logging**: JSON output with timestamps and metadata
- **Artifact Collection**: Standardized output paths
- **Error Handling**: Comprehensive error reporting

### 3. Runner Tool (`runner_tool.py`)

Python implementation of the MCP Runner Tool:

#### Key Features
- **Async Execution**: Non-blocking task execution
- **Multi-Runtime Support**: Auto-detect Podman/Docker/Kubernetes
- **Real-time Logging**: Stream logs during execution
- **Artifact Management**: Automatic artifact collection
- **Context Integration**: Redis/Neo4j integration

#### MCP Methods
- `run_task(spec: TaskSpec) -> str`: Start task execution
- `stream_logs(task_id: str) -> List[str]`: Stream execution logs
- `await_result(task_id: str, timeout_sec: Optional[int]) -> TaskResult`: Wait for completion
- `copy_artifacts(task_id: str, path: str) -> str`: Copy artifacts
- `cancel(task_id: str) -> bool`: Cancel running task
- `health() -> Dict[str, Any]`: Health check

### 4. Build System (`Makefile`)

Comprehensive build and deployment automation:

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
```

## 🔒 Security Features

### Container Security
- **Non-root execution**: All tasks run as non-root user
- **Resource limits**: CPU and memory constraints enforced
- **Timeout protection**: Automatic task termination
- **Isolated workspace**: Mounted directories with proper permissions
- **No secrets**: All secrets injected at runtime

### Runtime Security
- **Multi-runtime support**: Podman, Docker, Kubernetes
- **Ephemeral containers**: Each execution in new container
- **Network isolation**: Configurable network access
- **Process limits**: Maximum process count restrictions

### Audit and Traceability
- **Complete logging**: Every execution logged to Redis/Neo4j
- **Structured metadata**: Case ID, task ID, role tracking
- **Performance metrics**: Execution time and resource usage
- **Artifact tracking**: Complete artifact lifecycle management

## 🚀 Usage Examples

### Python API Usage

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

### Command Line Usage

```bash
# Build and test locally
cd src/swe_ai_fleet/tools/runner
make build
make task TASK=unit LANG=python

# Test the runner tool
python3 test_runner.py
```

## 🔗 Integration with SWE AI Fleet

### Context System Integration

The Runner integrates seamlessly with the SWE AI Fleet context system:

- **Redis**: Short-term plan/spec/events storage
- **Neo4j**: Graph of decisions/plan/subtasks  
- **Context Assembler**: Builds filtered context packs by role and phase

### Context Hydration

The `context.hydration_refs` in TaskSpec files reference Redis keys and Neo4j queries that the orchestrator uses to hydrate the agent's context before task execution:

```json
{
  "context": {
    "case_id": "case-7429",
    "task_id": "dev-impl-authz-v2",
    "role": "developer",
    "scope": ["spec.min", "decisions.related", "coding.conventions"],
    "hydration_refs": [
      {"redis_key": "swe:case:case-7429:spec"},
      {"neo4j_query": "MATCH (c:Case{id:'case-7429'})-[:HAS_PLAN]->(p)-[:CONTAINS]->(s {id:'dev-impl-authz-v2'}) RETURN p,s"}
    ]
  }
}
```

## 📊 Performance and Monitoring

### Key Metrics
- **Execution time** per task type
- **Success rate** by language and task
- **Resource usage** (CPU, memory)
- **Artifact generation** and collection

### Health Monitoring
```python
health_info = await runner.health()
# Returns:
# {
#   "status": "healthy",
#   "runtime": "podman",
#   "registry": "localhost",
#   "active_tasks": 2,
#   "total_tasks": 15
# }
```

## 🧪 Testing

### Test Suite
The runner system includes comprehensive tests:

```bash
python3 test_runner.py
```

Tests cover:
- Basic Python task execution
- Go task execution
- Health check functionality
- Task cancellation
- Error handling

### Test Coverage
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Security Tests**: Isolation and security validation
- **Performance Tests**: Resource usage and timing

## 🚀 Future Enhancements

### Planned Features
1. **Policy Engine**: Role-based access control and validation
2. **Enhanced Tool Gateway**: HTTP/gRPC API for external integration
3. **Advanced Sandboxing**: Enhanced security and isolation
4. **Kubernetes Integration**: Native Kubernetes Job execution
5. **Monitoring Dashboard**: Real-time execution monitoring

### Extensibility
The system is designed for easy extension:
- **New Languages**: Add language support to agent-task shim
- **New Task Types**: Extend task routing logic
- **New Runtimes**: Add runtime detection and support
- **New Artifacts**: Extend artifact collection patterns

## 📚 References

- **Containerfile**: `/src/swe_ai_fleet/tools/runner/Containerfile`
- **agent-task Shim**: `/src/swe_ai_fleet/tools/runner/agent-task`
- **Runner Tool**: `/src/swe_ai_fleet/tools/runner/runner_tool.py`
- **Examples**: `/src/swe_ai_fleet/tools/runner/examples/`
- **Test Suite**: `/src/swe_ai_fleet/tools/runner/test_runner.py`

## 🎯 Summary

The Runner System provides:

- **Standardized Protocol**: TaskSpec/TaskResult contract for agent-container interaction
- **Secure Execution**: Non-root, resource-limited, audited task execution
- **Multi-Runtime Support**: Podman, Docker, and Kubernetes compatibility
- **Context Integration**: Seamless integration with SWE AI Fleet context system
- **Comprehensive Testing**: Full test coverage and validation
- **Extensible Design**: Easy extension for new languages, tasks, and runtimes

This system represents a critical milestone in SWE AI Fleet's evolution from "talking and reasoning" to "executing, validating, and learning" autonomously.

