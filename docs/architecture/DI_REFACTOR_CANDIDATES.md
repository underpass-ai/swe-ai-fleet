# DI Refactor Candidates Analysis

**Date**: 2025-01-28
**Status**: Analysis complete
**Next Action**: Refactor remaining use cases

## Current Status

✅ **Completed**:
- VLLMAgent: Requires all dependencies (fail-fast)
- GeneratePlanUseCase: Requires all dependencies (fail-fast)
- GenerateNextActionUseCase: Requires all dependencies (fail-fast)

❌ **Needs Refactoring**:
- ExecuteTaskUseCase: Still creates mappers internally
- ExecuteTaskIterativeUseCase: Still creates mappers internally

## Remaining DI Candidates

### 1. ExecuteTaskUseCase (Line 36-50)

**Current (BAD)**:
```python
def __init__(
    self,
    tool_execution_port: ToolExecutionPort,
    llm_client_port: LLMClientPort | None = None,
):
    self.tool_execution_port = tool_execution_port
    self.llm_client_port = llm_client_port
    self.step_mapper = ExecutionStepMapper()  # ❌ Created internally
    self.artifact_mapper = ArtifactMapper()   # ❌ Created internally
```

**Should be (FAIL-FAST)**:
```python
def __init__(
    self,
    tool_execution_port: ToolExecutionPort,
    llm_client_port: LLMClientPort | None = None,
    step_mapper: ExecutionStepMapper,  # ✅ Required
    artifact_mapper: ArtifactMapper,   # ✅ Required
):
    if not tool_execution_port:
        raise ValueError("tool_execution_port is required (fail-fast)")
    if not step_mapper:
        raise ValueError("step_mapper is required (fail-fast)")
    if not artifact_mapper:
        raise ValueError("artifact_mapper is required (fail-fast)")

    self.tool_execution_port = tool_execution_port
    self.llm_client_port = llm_client_port
    self.step_mapper = step_mapper
    self.artifact_mapper = artifact_mapper
```

### 2. ExecuteTaskIterativeUseCase (Line 36-46)

**Current (BAD)**:
```python
def __init__(self, tool_execution_port: ToolExecutionPort):
    self.tool_execution_port = tool_execution_port
    self.step_mapper = ExecutionStepMapper()  # ❌ Created internally
    self.artifact_mapper = ArtifactMapper()   # ❌ Created internally
```

**Should be (FAIL-FAST)**:
```python
def __init__(
    self,
    tool_execution_port: ToolExecutionPort,
    step_mapper: ExecutionStepMapper,  # ✅ Required
    artifact_mapper: ArtifactMapper,   # ✅ Required
):
    if not tool_execution_port:
        raise ValueError("tool_execution_port is required (fail-fast)")
    if not step_mapper:
        raise ValueError("step_mapper is required (fail-fast)")
    if not artifact_mapper:
        raise ValueError("artifact_mapper is required (fail-fast)")

    self.tool_execution_port = tool_execution_port
    self.step_mapper = step_mapper
    self.artifact_mapper = artifact_mapper
```

## Usage Analysis

### Are These Use Cases Used?

**ExecuteTaskUseCase**:
- ❌ Not directly instantiated anywhere in codebase
- ❌ No tests found
- ⚠️ May be legacy code

**ExecuteTaskIterativeUseCase**:
- ❌ Not directly instantiated anywhere in codebase
- ❌ No tests found
- ⚠️ May be legacy code

### VLLMAgent Usage

VLLMAgent currently calls methods internally rather than delegating to these use cases:
- `_execute_step()` calls `tool_execution_port.execute_operation()` directly
- `_generate_plan()` delegates to `generate_plan_usecase` (✅ already refactored)
- `_decide_next_action()` delegates to `generate_next_action_usecase` (✅ already refactored)

## Impact Analysis

### Low Impact (Safe to Refactor)

These use cases are **not currently used** in the codebase:
- No production code depends on them
- No tests depend on them
- Risk: Very low

### Refactoring Strategy

Since these use cases are not used:
1. **Option A**: Refactor them (for consistency and future use)
2. **Option B**: Delete them (if they're truly legacy code)

**Recommendation**: **Refactor for consistency** - these use cases may be used in the future, and keeping them aligned with our DI pattern is good practice.

## Next Steps

1. **Refactor ExecuteTaskUseCase**:
   - Add `step_mapper` and `artifact_mapper` as required parameters
   - Add fail-fast validation
   - Update any hypothetical users (none found)

2. **Refactor ExecuteTaskIterativeUseCase**:
   - Add `step_mapper` and `artifact_mapper` as required parameters
   - Add fail-fast validation
   - Update any hypothetical users (none found)

3. **Create Tests** (optional):
   - Since these aren't currently tested, consider adding unit tests
   - Or mark them for future implementation

## Estimated Effort

- **Complexity**: Low (2 files, 4 lines each)
- **Risk**: Minimal (not used in production)
- **Time**: < 30 minutes

## Priority

**Medium** - These are not actively used, but keeping the codebase consistent with DI patterns is important for maintainability.

