# VLLMClient Refactor Plan

## Current Analysis

### VLLMClient Class (290 lines)

**Location**: `core/agents/vllm_client.py`

**Purpose**: Client for calling vLLM API for text generation.

**Methods**:
1. `generate()` - Generic text generation via vLLM API ✅ CORRECT
2. `generate_plan()` - Generate execution plan for a task ❌ WRONG RESPONSIBILITY
3. `decide_next_action()` - ReAct-style next action decision ❌ WRONG RESPONSIBILITY

**Dependencies**:
- `aiohttp` (async HTTP client)
- vLLM API endpoint

**Current Issues**:
- ✅ Well-defined core responsibility: `generate()`
- ✅ Async implementation
- ✅ Good error handling
- ❌ **TOO MANY RESPONSIBILITIES**: `generate_plan()` and `decide_next_action()` contain business logic, not just LLM calls
- ⚠️ Directly coupled to vLLM API
- ⚠️ No abstraction/port

## Refactor Strategy

### Step 1: Create Minimal Port (Domain Layer)

Create `core/agents/domain/ports/llm_client_port.py`:

```python
"""Port for LLM client operations (low-level API calls)."""

from abc import ABC, abstractmethod

class LLMClientPort(ABC):
    """Port defining low-level LLM API interface.

    This port should ONLY contain the primitive LLM operation:
    generating text from prompts.

    Business logic (planning, decisions, etc.) belongs in Use Cases.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate text from prompts.

        This is the ONLY responsibility: call LLM API and return text.
        No business logic, no specific task handling, just raw LLM communication.
        """
        pass
```

**Key Change**: Remove `generate_plan()` and `decide_next_action()` from the port.

These methods contain business logic (building prompts, parsing responses, fallbacks).
They belong in Use Cases, not in the low-level LLM adapter.

### Step 2: Simplify VLLMClient Adapter

Move `core/agents/vllm_client.py` → `core/agents/infrastructure/adapters/vllm_client_adapter.py`

Update class name: `VLLMClient` → `VLLMClientAdapter`

**Remove methods that contain business logic**:
- ❌ Delete `generate_plan()` - business logic, not LLM communication
- ❌ Delete `decide_next_action()` - business logic, not LLM communication

**Keep only**:
- ✅ `generate()` - pure LLM API call
- ✅ Initialization (`__init__`)

```python
class VLLMClientAdapter(LLMClientPort):
    """Adapter for vLLM API - ONLY raw LLM communication."""

    def __init__(self, vllm_url: str, model: str, temperature: float, max_tokens: int, timeout: int):
        # Keep initialization as-is
        self.vllm_url = vllm_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    async def generate(self, system_prompt: str, user_prompt: str, temperature: float | None = None, max_tokens: int | None = None) -> str:
        """Call vLLM API to generate text. ONLY this responsibility."""
        # Keep implementation as-is (lines 61-118 from vllm_client.py)
        pass

    # Remove generate_plan() - move to use case
    # Remove decide_next_action() - move to use case
```

### Step 3: Create Use Cases (Application Layer)

Move business logic from `generate_plan()` and `decide_next_action()` to Use Cases:

**Create `core/agents/application/usecases/generate_plan_usecase.py`**:

```python
class GeneratePlanUseCase:
    """Use case for generating execution plans."""

    def __init__(self, llm_client: LLMClientPort):
        self.llm_client = llm_client

    async def execute(self, task: str, context: str, role: str, available_tools: dict, constraints: dict | None = None) -> dict:
        """Generate execution plan using LLM."""
        # Move business logic from VLLMClient.generate_plan() here:
        # - Build system prompt
        # - Build user prompt
        # - Call llm_client.generate()
        # - Parse response
        # - Return plan dict
        pass
```

**Create `core/agents/application/usecases/generate_next_action_usecase.py`**:

```python
class GenerateNextActionUseCase:
    """Use case for deciding next action (ReAct)."""

    def __init__(self, llm_client: LLMClientPort):
        self.llm_client = llm_client

    async def execute(self, task: str, context: str, observation_history: list[dict], available_tools: dict) -> dict:
        """Decide next action using ReAct pattern."""
        # Move business logic from VLLMClient.decide_next_action() here:
        # - Build system prompt
        # - Build user prompt with history
        # - Call llm_client.generate()
        # - Parse response
        # - Return decision dict
        pass
```

### Step 4: Update VLLMAgent

Change in `vllm_agent.py`:

```python
# OLD (direct import of concrete adapter)
from core.agents.vllm_client import VLLMClient

# NEW (inject use cases, not adapter directly)
from core.agents.application.usecases.generate_plan_usecase import GeneratePlanUseCase
from core.agents.application.usecases.generate_next_action_usecase import GenerateNextActionUseCase

class VLLMAgent:
    def __init__(self, ..., generate_plan_usecase: GeneratePlanUseCase, generate_next_action_usecase: GenerateNextActionUseCase):
        # Inject use cases
        self.generate_plan_usecase = generate_plan_usecase
        self.generate_next_action_usecase = generate_next_action_usecase
```

### Step 5: Factory/Composition

Create factory that wires dependencies:

```python
# core/agents/infrastructure/factories/vllm_agent_factory.py
def create_vllm_agent(agent_id: str, role: str, vllm_url: str, ...):
    # Create low-level adapter
    llm_adapter = VLLMClientAdapter(vllm_url, model, temperature, max_tokens, timeout)

    # Create use cases (they use the adapter)
    generate_plan_usecase = GeneratePlanUseCase(llm_adapter)
    generate_next_action_usecase = GenerateNextActionUseCase(llm_adapter)

    # Create agent with use cases
    agent = VLLMAgent(agent_id, role, ...,
                     generate_plan_usecase=generate_plan_usecase,
                     generate_next_action_usecase=generate_next_action_usecase)
    return agent
```

## Benefits

1. **Single Responsibility**: VLLMClientAdapter only does LLM API calls
2. **Testable**: Can inject mock LLMClientPort for tests
3. **Business Logic Separation**: Planning/decision logic moved to Use Cases
4. **Flexible**: Can swap vLLM for OpenAI, Anthropic, etc. (only adapter changes)
5. **Clean**: Proper hexagonal architecture (domain, application, infrastructure)

## Migration Path

1. ✅ Create minimal port interface (`LLMClientPort.generate()` only)
2. ✅ Simplify VLLMClientAdapter (remove `generate_plan()`, `decide_next_action()`)
3. ✅ Create Use Cases (`GeneratePlanUseCase`, `GenerateNextActionUseCase`)
4. ✅ Move business logic from adapter to use cases
5. ✅ Update VLLMAgent to inject use cases instead of adapter
6. ✅ Update factory/composition to wire dependencies
7. ✅ Run tests to verify

## Risk: MEDIUM

- ✅ Clear separation of concerns
- ⚠️ Need to carefully move logic from adapter methods to use cases
- ⚠️ Need to update all VLLMAgent calls to use use cases
- ⚠️ Tests may need updates to mock use cases instead of adapter

