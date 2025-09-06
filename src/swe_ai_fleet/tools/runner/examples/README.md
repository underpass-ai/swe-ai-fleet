# Runner Contract Examples

This directory contains example TaskSpec and TaskResult JSON files that demonstrate the Developer Agent ↔ Runner Contract protocol.

## Files

- `task-spec-python-unit.json` - Example Python unit test task specification
- `task-spec-go-integration.json` - Example Go integration test task specification  
- `task-result-success.json` - Example successful task result
- `task-result-failure.json` - Example failed task result

## Usage

These examples can be used to:

1. **Test the Runner Tool** - Use TaskSpec files as input to test the MCP Runner Tool implementation
2. **Validate Contract** - Ensure your implementation matches the expected TaskSpec/TaskResult format
3. **Documentation** - Reference for developers implementing agent-runner interactions

## TaskSpec Structure

The TaskSpec defines what work the agent wants the container to perform:

- `image` - Container image to run
- `cmd` - Command to execute (typically agent-task shim)
- `env` - Environment variables (TASK, LANG, REPO_URL, etc.)
- `mounts` - Volume mounts (workspace, docker socket)
- `timeouts` - Execution time limits
- `resources` - CPU/memory constraints
- `artifacts` - Output paths to collect
- `context` - Case/task metadata for context hydration

## TaskResult Structure

The TaskResult reports the outcome of the task execution:

- `status` - passed|failed|error|timeout
- `exitCode` - Process exit code
- `captured` - References to logs and artifacts
- `metadata` - Execution details (timing, container info, case context)

## Testing Locally

You can test these examples using the Makefile:

```bash
# Build the runner image
make build

# Run a Python unit test task
make task TASK=unit LANG=python

# Run a Go integration test task  
make task TASK=integration LANG=go
```

## Integration with SWE AI Fleet

These examples integrate with the SWE AI Fleet context system:

- **Redis** - Short-term plan/spec/events storage
- **Neo4j** - Graph of decisions/plan/subtasks
- **Context Assembler** - Builds filtered context packs by role and phase

The `context.hydration_refs` in TaskSpec files reference Redis keys and Neo4j queries that the orchestrator uses to hydrate the agent's context before task execution.
