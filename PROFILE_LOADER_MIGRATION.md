# Profile Loader Migration Guide

## Changes Made
- ❌ Deleted `core/agents_and_tools/agents/profile_loader.py`
- ✅ Created `ProfileLoaderPort` in `domain/ports/`
- ✅ Created `YamlProfileLoaderAdapter` in `infrastructure/adapters/`
- ✅ Created `AgentProfileMapper` in `infrastructure/mappers/`

## Where to Use the Adapter

### 1. In `vllm_agent.py` (Line 269)
**Current code:**
```python
from core.agents_and_tools.agents.infrastructure.adapters.yaml_profile_adapter import YamlProfileLoaderAdapter

# Get default profiles directory (fail-fast: must exist)
from pathlib import Path
current_file = Path(__file__)
project_root = current_file.parent.parent.parent.parent  # up to core/
profiles_url = str(project_root / "agents_and_tools" / "resources" / "profiles")

profile_adapter = YamlProfileLoaderAdapter(profiles_url)
profile = profile_adapter.load_profile_for_role(role)
```

### 2. In Tests (`test_profile_loader.py`)
**Change all:**
```python
# OLD
from core.agents_and_tools.agents.profile_loader import get_profile_for_role
profile = get_profile_for_role("ARCHITECT", profiles_url)

# NEW
from core.agents_and_tools.agents.infrastructure.adapters.yaml_profile_adapter import YamlProfileLoaderAdapter
adapter = YamlProfileLoaderAdapter(profiles_url)
profile = adapter.load_profile_for_role("ARCHITECT")
```

### 3. In Documentation (`README.md`)
Update examples to use:
```python
from core.agents_and_tools.agents.infrastructure.adapters.yaml_profile_adapter import YamlProfileLoaderAdapter

adapter = YamlProfileLoaderAdapter("/path/to/profiles")
profile = adapter.load_profile_for_role("ARCHITECT")
```

## Architecture Pattern

```
Port (interface)
   ↓
Adapter (implementation)
   ↓
Entity (domain)
```

- **Port**: `ProfileLoaderPort` - abstract interface
- **Adapter**: `YamlProfileLoaderAdapter` - concrete implementation
- **Entity**: `AgentProfile` - domain entity

## Fail-Fast Principle Applied
- `profiles_url` is REQUIRED (no default)
- Directory must exist (raises FileNotFoundError)
- All YAML fields required (raises KeyError if missing)

