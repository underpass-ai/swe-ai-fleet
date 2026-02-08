# Core Agents and Tools

Reusable bounded context for agent execution logic and tool invocation.

## Scope

`core/agents_and_tools` provides:

- Agent domain and application layers (`agents/domain`, `agents/application`)
- `VLLMAgent` facade (`agents/vllm_agent.py`)
- Tool domain and adapters (`tools/domain`, `tools/adapters`, `tools/runner`)
- Shared capability model (`common/domain`)
- Role profiles and prompts under `resources/profiles` and `resources/prompts`

## Main Components

Agent side:

- Plan generation and iterative execution use cases (`generate_plan_usecase`, `execute_task_iterative_usecase`)
- LLM and tool execution ports for dependency injection
- Infrastructure adapters for vLLM client, profiles, and mapping

Tool side:

- Tool implementations: file, git, docker, db, http, helm, kubectl, psql, test, runner
- Validation helpers and typed result mappers

## Integration

Primary consumers:

- `core/ray_jobs` (tool-enabled execution inside Ray workers)
- `services/orchestrator` and related adapters (agent creation and role orchestration)

## Tests

```bash
make test-module MODULE=core/agents_and_tools
```
