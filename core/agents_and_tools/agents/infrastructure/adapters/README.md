# Agent Infrastructure Adapters

This directory contains adapters that provide implementations of ports for the agents bounded context following the Hexagonal Architecture pattern.

## 🔧 Adapters

### ToolSet (`toolset.py`)

**Purpose**: Manages the lifecycle and access to agent tools.

**Features**:
- Initializes all required tools (Git, File, Test, HTTP, Database)
- Handles optional tools gracefully (Docker)
- Provides clean access interface
- Delegates audit logging to tools

**Usage**:
```python
from core.agents_and_tools.agents.infrastructure.adapters import ToolSet

# Initialize toolset
toolset = ToolSet(
    workspace_path="/workspace/project",
    audit_callback=my_audit_callback
)

# Access tools
git_tool = toolset.get_tool("git")
if git_tool:
    git_tool.status()

# Check availability
if toolset.has_tool("docker"):
    docker_tool = toolset.get_tool("docker")

# Get all tools as dict
all_tools = toolset.get_all_tools()
```

**Interface**:
- `get_tool(tool_name: str) -> Any | None` - Get a specific tool
- `get_all_tools() -> dict[str, Any]` - Get all tools as dict
- `has_tool(tool_name: str) -> bool` - Check if tool is available
- `get_available_tools() -> list[str]` - Get list of available tool names
- `get_tool_count() -> int` - Get total number of tools

### VLLMClientAdapter (`vllm_client_adapter.py`)

**Purpose**: Adapter for vLLM LLM client port.

**Responsibilities**:
- Communicate with vLLM service
- Format requests/responses
- Handle errors and retries

### YamlProfileAdapter (`yaml_profile_adapter.py`)

**Purpose**: Adapter for loading agent profiles from YAML files.

**Responsibilities**:
- Load agent profile configurations
- Validate profile schemas
- Convert YAML to domain entities

### ProfileConfig (`profile_config.py`)

**Purpose**: Configuration adapter for agent profiles.

**Responsibilities**:
- Load profile configurations
- Map role to profile
- Provide profile access interface

## 🏗️ Architecture

All adapters follow the Hexagonal Architecture pattern:

```
Domain Layer (core/agents_and_tools/agents/domain/)
├── Entities (AgentProfile, AgentResult, etc.)
├── Ports (interfaces like LLMClientPort)
└── Use Cases (business logic)

Infrastructure Layer (core/agents_and_tools/agents/infrastructure/)
├── Adapters (this directory) ← Concrete implementations
├── DTOs (data transfer objects)
└── Mappers (convert DTOs to entities)
```

**Key Principle**: Domain layer has ZERO dependencies on adapters. All dependencies flow inward:
- Adapters implement Ports
- Use Cases depend on Ports (not adapters)
- Entities are pure domain logic

## 🧪 Testing

Each adapter has corresponding unit tests in `tests/unit/core/agents/test_*.py`:

- `test_toolset.py` - Tests for ToolSet
- Other adapter tests follow similar patterns

**Test Requirements**:
- Mock all external dependencies
- Test both success and failure paths
- Verify correct delegation to ports
- Test graceful degradation for optional features

## 📝 Usage in VLLMAgent

The VLLMAgent uses adapters through dependency injection:

```python
class VLLMAgent:
    def __init__(self, config: AgentInitializationConfig):
        # Initialize toolset via adapter
        self.toolset = ToolSet(
            workspace_path=self.workspace_path,
            audit_callback=self.audit_callback,
        )

        # Access tools through toolset
        self.tools = self.toolset.get_all_tools()
```

This pattern ensures:
- Clean separation of concerns
- Easy mocking in tests
- Flexible tool management
- Optional tool support

