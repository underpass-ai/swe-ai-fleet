"""Use case for loading agent profiles."""

from core.agents_and_tools.agents.domain.entities import AgentProfile
from core.agents_and_tools.agents.domain.ports.profile_loader_port import ProfileLoaderPort


class LoadProfileUseCase:
    """Use case for loading agent profiles by role.

    This use case delegates to the ProfileLoaderPort to load profiles.
    The port can be implemented by different adapters (YAML, database, etc.).

    Args:
        profile_loader: ProfileLoaderPort implementation (injected dependency)
    """

    def __init__(self, profile_loader: ProfileLoaderPort):
        """Initialize use case with profile loader port.

        Args:
            profile_loader: ProfileLoaderPort implementation (injected dependency)
        """
        self.profile_loader = profile_loader

    def execute(self, role: str) -> AgentProfile:
        """Load agent profile for a specific role.

        Args:
            role: Agent role (DEV, QA, ARCHITECT, DEVOPS, DATA)

        Returns:
            AgentProfile domain entity

        Raises:
            FileNotFoundError: If profile not found for the role
        """
        return self.profile_loader.load_profile_for_role(role)

