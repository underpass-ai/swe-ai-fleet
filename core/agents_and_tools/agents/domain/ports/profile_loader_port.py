"""Port for loading agent profiles."""

from abc import ABC, abstractmethod

from core.agents_and_tools.agents.domain.entities.agent_profile import AgentProfile


class ProfileLoaderPort(ABC):
    """Port for loading agent profiles by role.

    This port defines the contract for loading agent profile configurations.
    Adapters implement this port to load from various sources (YAML, database, etc.).
    """

    @abstractmethod
    def load_profile_for_role(self, role: str) -> AgentProfile:
        """Load agent profile configuration for a specific role.

        Args:
            role: Agent role (DEV, QA, ARCHITECT, DEVOPS, DATA)

        Returns:
            AgentProfile domain entity

        Raises:
            FileNotFoundError: If profile not found for the role
            KeyError: If required fields missing in configuration
        """
        pass

