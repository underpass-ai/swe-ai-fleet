"""Adapter for loading profiles from YAML files."""

from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

from core.agents_and_tools.agents.domain.entities.agent_profile import AgentProfile


def load_profile_from_yaml(yaml_path: str | Path) -> AgentProfile:
    """Load AgentProfile from YAML file (fail fast).
    
    Args:
        yaml_path: Path to YAML file
        
    Returns:
        AgentProfile domain entity
        
    Raises:
        ImportError: If pyyaml not available
        FileNotFoundError: If file doesn't exist
        KeyError: If required fields missing in YAML
    """
    if not YAML_AVAILABLE:
        raise ImportError("pyyaml required. Install with: pip install pyyaml")

    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {yaml_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    # Fail fast if required fields are missing
    return AgentProfile(
        name=data["name"],
        model=data["model"],
        context_window=data["context_window"],
        temperature=data["temperature"],
        max_tokens=data["max_tokens"],
    )

