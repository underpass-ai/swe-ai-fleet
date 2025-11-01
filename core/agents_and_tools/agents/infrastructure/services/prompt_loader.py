"""Service for loading prompt templates from YAML."""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    Service for loading prompt templates from YAML files.

    This service belongs to the infrastructure layer and handles loading
    prompt configurations from external YAML files.
    """

    def __init__(self, resources_path: Path | None = None):
        """
        Initialize prompt loader.

        Args:
            resources_path: Path to resources directory (default: auto-detect)
        """
        if resources_path is None:
            # Auto-detect resources path
            resources_path = Path(__file__).parent.parent.parent.parent / "resources"
        self.resources_path = resources_path
        self._prompts_cache: dict[str, Any] = {}

    def load_prompt_config(self, prompt_name: str) -> dict[str, Any]:
        """
        Load prompt configuration from YAML file.

        Args:
            prompt_name: Name of prompt config (e.g., "plan_generation", "next_action_react")

        Returns:
            Dictionary with prompt configuration

        Raises:
            FileNotFoundError: If prompt file not found
        """
        # Check cache
        if prompt_name in self._prompts_cache:
            return self._prompts_cache[prompt_name]

        # Load from file
        prompt_file = self.resources_path / "prompts" / f"{prompt_name}.yaml"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt config not found: {prompt_file}")

        with open(prompt_file) as f:
            config = yaml.safe_load(f)

        # Cache result
        self._prompts_cache[prompt_name] = config

        logger.debug(f"Loaded prompt config: {prompt_name}")
        return config

    def get_system_prompt_template(self, prompt_name: str) -> str:
        """
        Get system prompt template.

        Args:
            prompt_name: Name of prompt config

        Returns:
            System prompt template string
        """
        config = self.load_prompt_config(prompt_name)
        return config.get("system_prompt", "")

    def get_user_prompt_template(self, prompt_name: str) -> str:
        """
        Get user prompt template.

        Args:
            prompt_name: Name of prompt config

        Returns:
            User prompt template string
        """
        config = self.load_prompt_config(prompt_name)
        return config.get("user_prompt", "")

    def get_role_prompt(self, prompt_name: str, role: str) -> str:
        """
        Get role-specific prompt.

        Args:
            prompt_name: Name of prompt config
            role: Agent role (DEV, QA, etc.)

        Returns:
            Role-specific prompt string
        """
        config = self.load_prompt_config(prompt_name)
        roles = config.get("roles", {})
        return roles.get(role, f"You are an expert {role} engineer.")

