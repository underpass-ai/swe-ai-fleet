# Agent Profile Files

Role-specific LLM model configurations for SWE AI Fleet agents.

## 📁 Structure

Each YAML file contains configuration for one agent role:

```
profiles/
├── architect.yaml    # ARCHITECT role - design decisions
├── developer.yaml    # DEV role - code implementation
├── qa.yaml          # QA role - testing and validation
├── devops.yaml      # DEVOPS role - infrastructure
└── data.yaml        # DATA role - database management
```

## 🔧 Configuration

Each profile contains:

```yaml
name: <Role Name>
model: <LLM model identifier>
context_window: <int>    # Maximum context size in tokens
temperature: <float>      # Sampling temperature (0.0-2.0)
max_tokens: <int>         # Maximum tokens to generate
```

## 📊 Current Models

| Role | Model | Temperature | Context | Max Tokens |
|------|-------|-------------|---------|------------|
| ARCHITECT | databricks/dbrx-instruct | 0.3 | 128K | 8192 |
| DEV | deepseek-coder:33b | 0.7 | 32K | 4096 |
| QA | mistralai/Mistral-7B-Instruct-v0.3 | 0.5 | 32K | 3072 |
| DEVOPS | Qwen/Qwen2.5-Coder-14B-Instruct | 0.6 | 32K | 4096 |
| DATA | deepseek-ai/deepseek-coder-6.7b-instruct | 0.7 | 32K | 4096 |

## 🎯 How It Works

The `profile_loader` module automatically loads these configurations:

```python
from core.agents_and_tools.agents.profile_loader import get_profile_for_role

# Get configuration for DEV role
profile = get_profile_for_role("DEV")
# Returns: {"model": "deepseek-coder:33b", "temperature": 0.7, ...}
```

These profiles are loaded by `VLLMAgent` during initialization to configure the LLM adapter.

## 🔄 Customization

To customize a profile:

1. Edit the corresponding YAML file
2. Adjust model, temperature, or token limits as needed
3. Restart agents to load new configuration
4. No code changes required!

## 📚 See Also

- `core/agents_and_tools/agents/profile_loader.py` - Loading logic
- `docs/architecture/AGENT_PROFILE_LOADER_EXPLAINED.md` - Detailed explanation

