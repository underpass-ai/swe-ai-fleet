"""Load agent profiles with role-specific model configurations."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

logger = logging.getLogger(__name__)


@dataclass
class AgentProfile:
    """Agent profile with model configuration."""
    
    name: str
    model: str
    context_window: int
    temperature: float
    max_tokens: int
    
    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "AgentProfile":
        """Load profile from YAML file."""
        if not YAML_AVAILABLE:
            raise ImportError("pyyaml required. Install with: pip install pyyaml")
        
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {yaml_path}")
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        return cls(
            name=data["name"],
            model=data["model"],
            context_window=data.get("context_window", 32768),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
        )


# Default profiles by role
ROLE_MODEL_MAPPING = {
    "ARCHITECT": {
        "model": "databricks/dbrx-instruct",
        "temperature": 0.3,
        "max_tokens": 8192,
        "context_window": 128000,
    },
    "DEV": {
        "model": "deepseek-coder:33b",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 32768,
    },
    "QA": {
        "model": "mistralai/Mistral-7B-Instruct-v0.3",
        "temperature": 0.5,
        "max_tokens": 3072,
        "context_window": 32768,
    },
    "DEVOPS": {
        "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
        "temperature": 0.6,
        "max_tokens": 4096,
        "context_window": 32768,
    },
    "DATA": {
        "model": "deepseek-ai/deepseek-coder-6.7b-instruct",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 32768,
    },
}


def get_profile_for_role(role: str, profiles_dir: str | Path | None = None) -> dict[str, Any]:
    """
    Get agent profile configuration for a role.
    
    Tries to load from YAML file first, falls back to defaults.
    
    Args:
        role: Agent role (DEV, QA, ARCHITECT, DEVOPS, DATA)
        profiles_dir: Directory containing profile YAML files
                     Defaults to core/models/profiles/
    
    Returns:
        Dictionary with model, temperature, max_tokens, context_window
    """
    role = role.upper()
    
    # Try to load from YAML if directory provided or use default location
    if profiles_dir is None:
        # Default: core/models/profiles/
        profiles_dir = Path(__file__).parent.parent / "models" / "profiles"
    else:
        profiles_dir = Path(profiles_dir)
    
    if profiles_dir.exists() and YAML_AVAILABLE:
        # Map role to profile filename
        role_to_file = {
            "ARCHITECT": "architect.yaml",
            "DEV": "developer.yaml",
            "QA": "qa.yaml",
            "DEVOPS": "devops.yaml",
            "DATA": "data.yaml",
        }
        
        profile_file = profiles_dir / role_to_file.get(role, f"{role.lower()}.yaml")
        
        if profile_file.exists():
            try:
                profile = AgentProfile.from_yaml(profile_file)
                logger.info(f"Loaded profile for {role} from {profile_file}")
                return {
                    "model": profile.model,
                    "temperature": profile.temperature,
                    "max_tokens": profile.max_tokens,
                    "context_window": profile.context_window,
                }
            except Exception as e:
                logger.warning(f"Failed to load profile from {profile_file}: {e}")
    
    # Fallback to hardcoded defaults
    if role in ROLE_MODEL_MAPPING:
        logger.info(f"Using default profile for {role}")
        return ROLE_MODEL_MAPPING[role]
    
    # Ultimate fallback
    logger.warning(f"No profile found for role {role}, using generic defaults")
    return {
        "model": "Qwen/Qwen3-0.6B",
        "temperature": 0.7,
        "max_tokens": 2048,
        "context_window": 8192,
    }

