# Dependency Injection Refactor - Fail-Fast Pattern

**Date**: 2025-01-28
**Status**: ✅ Complete
**Tests**: 76/76 passing (100%)

## Summary

Refactored all dependency creation in `agents_and_tools` to follow **fail-fast pattern** with **zero defaults**. All dependencies are now **required** parameters. No backward compatibility maintained.

## Architecture Changes

### Before (with defaults)

```python
class VLLMAgent:
    def __init__(
        self,
        config: AgentInitializationConfig,
        tool_execution_port: ToolExecutionPort | None = None,  # ❌ Optional with default
    ):
        # Internally constructs many dependencies
        llm_adapter = VLLMClientAdapter(...)
        self.generate_plan_usecase = GeneratePlanUseCase(llm_adapter)
        ...
```

### After (fail-fast)

```python
class VLLMAgent:
    def __init__(
        self,
        config: AgentInitializationConfig,
        llm_client_port: LLMClientPort,  # ✅ Required
        tool_execution_port: ToolExecutionPort,  # ✅ Required
        generate_plan_usecase: GeneratePlanUseCase,  # ✅ Required
        generate_next_action_usecase: GenerateNextActionUseCase,  # ✅ Required
        step_mapper: ExecutionStepMapper,  # ✅ Required
    ):
        # Fail fast validation
        if not llm_client_port:
            raise ValueError("llm_client_port is required (fail-fast)")
        if not tool_execution_port:
            raise ValueError("tool_execution_port is required (fail-fast)")
        # ... all dependencies checked
```

## Changes Made

### 1. VLLMAgent - Full DI (fail-fast)

**Changes**:
- Now requires: `llm_client_port`, `tool_execution_port`, `generate_plan_usecase`, `generate_next_action_usecase`, `step_mapper`
- Removed all internal dependency creation
- Added fail-fast validation for all dependencies
- No optional parameters

**Impact**: All callers must provide dependencies. Factory must be used.

### 2. GeneratePlanUseCase - Required Dependencies

**Changes**:
- Now requires: `llm_client`, `prompt_loader`, `json_parser`, `step_mapper`
- Removed optional parameters with defaults
- Added fail-fast validation

**Before**:
```python
def __init__(
    self,
    llm_client: LLMClientPort,
    prompt_loader: PromptLoader | None = None,  # ❌ Optional
    json_parser: JSONResponseParser | None = None,  # ❌ Optional
):
```

**After**:
```python
def __init__(
    self,
    llm_client: LLMClientPort,  # ✅ Required
    prompt_loader: PromptLoader,  # ✅ Required
    json_parser: JSONResponseParser,  # ✅ Required
    step_mapper: ExecutionStepMapper,  # ✅ Required
):
```

### 3. GenerateNextActionUseCase - Required Dependencies

Same changes as GeneratePlanUseCase.

### 4. VLLMAgentFactory - New Factory

**Purpose**: Centralizes dependency creation for `VLLMAgent`.

```python
class VLLMAgentFactory:
    @staticmethod
    def create(config: AgentInitializationConfig) -> VLLMAgent:
        # 1. Load profile
        # 2. Create LLM client adapter
        # 3. Create infrastructure services
        # 4. Create use cases
        # 5. Create tool execution adapter
        # 6. Create step mapper
        # 7. Return VLLMAgent with all dependencies
```

**Usage**: All production code and tests now use this factory.

## Test Updates

### Updated Test Files

1. `tests/unit/agents/test_vllm_agent_unit.py`
   - Added `VLLMAgentFactory` import
   - Changed `VLLMAgent(config)` → `VLLMAgentFactory.create(config)`

2. `tests/unit/core/agents/test_vllm_agent_gaps.py`
   - Added `VLLMAgentFactory` import
   - Changed `VLLMAgent(config)` → `VLLMAgentFactory.create(config)`

3. `tests/unit/core/agents/application/usecases/test_generate_plan_usecase.py`
   - Added `step_mapper` fixture
   - Updated `usecase` fixture to include `step_mapper`

4. `tests/unit/core/agents/application/usecases/test_generate_next_action_usecase.py`
   - Added `step_mapper` fixture
   - Updated `usecase` fixture to include `step_mapper`

## Benefits

1. **Fail-Fast**: Missing dependencies are caught immediately (constructor time)
2. **Testability**: All dependencies can be mocked
3. **Explicitness**: Dependencies are obvious from constructor signature
4. **No Magic**: No hidden defaults, no optional parameters
5. **Hexagonal Compliance**: Domain depends on abstractions (ports), not concrete adapters

## Breaking Changes

⚠️ **Production code that was creating `VLLMAgent` directly must now use `VLLMAgentFactory`**

**Old**:
```python
agent = VLLMAgent(config)
```

**New**:
```python
agent = VLLMAgentFactory.create(config)
```

## Architecture Validation

### Hexagonal Architecture Compliance

✅ **Domain depends on Ports only**:
- `VLLMAgent` depends on `LLMClientPort` and `ToolExecutionPort` (interfaces)
- No direct imports of concrete adapters in domain

✅ **Infrastructure implements Ports**:
- `VLLMClientAdapter` implements `LLMClientPort`
- `ToolExecutionAdapter` implements `ToolExecutionPort`

✅ **Dependency injection required**:
- All dependencies injected via constructor
- No service locator or global state

✅ **Fail-fast validation**:
- All required dependencies validated in constructor
- No silent defaults or fallbacks

## Self-Check

- **Completeness**: ✅ All dependencies identified and injected
- **Logical consistency**: ✅ No circular dependencies, proper layering
- **Fail-fast**: ✅ All dependencies required, validated in constructor
- **Testing**: ✅ 76/76 tests passing
- **Backward compatibility**: ❌ Intentionally broken (fail-fast design)

---

**Trade-offs**:
- ✅ More verbose instantiation (explicit is better)
- ✅ Factory required for common creation (acceptable)
- ✅ All tests updated (one-time cost)
- ✅ No ambiguity about dependencies (worth it)

**Confidence**: High - all tests passing, linting clean

