"""Agent aggregate root."""

from __future__ import annotations

from dataclasses import dataclass

from core.agents_and_tools.agents.domain.entities.rbac import Action, Role
from core.agents_and_tools.common.domain.entities.agent_capabilities import AgentCapabilities

from .agent_id import AgentId


@dataclass(frozen=True)
class Agent:
    """Aggregate Root: Agent in the SWE AI Fleet system.

    Agent is the root entity for the agents_and_tools bounded context.
    It encapsulates agent identity, capabilities, and RBAC enforcement.

    Responsibilities:
    - Identity (agent_id, name)
    - Capabilities (role → allowed_actions, allowed_tools)
    - RBAC enforcement (can_execute)
    - Self-validation

    Domain Invariants:
    - Agent must have valid agent_id
    - Agent must have valid role
    - Name cannot be empty
    - Capabilities are derived from role
    - Agent is immutable

    Examples:
        >>> from core.agents_and_tools.agents.domain.entities.rbac import RoleFactory
        >>> role = RoleFactory.create_architect()
        >>> agent = Agent(
        ...     agent_id=AgentId("agent-arch-001"),
        ...     role=role,
        ...     name="Senior Architect Agent",
        ...     capabilities=AgentCapabilities(...),
        ... )
        >>> agent.can_execute(Action(value=ActionEnum.APPROVE_DESIGN))
        True
    """

    agent_id: AgentId
    role: Role
    name: str
    capabilities: AgentCapabilities

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type checking is handled by type hints.
        This validates business rules only.

        Raises:
            ValueError: If name is empty
        """
        if not self.name:
            raise ValueError("Agent name cannot be empty")

    def can_execute(self, action: Action) -> bool:
        """Check if agent can execute the given action (RBAC enforcement).

        This method implements RBAC at the domain level. The agent validates
        its own capabilities based on its role.

        Business Rules:
        - Action MUST be in role's allowed_actions
        - Action scope MUST match role's scope
        - Cross-scope actions are forbidden

        Args:
            action: The Action to check

        Returns:
            True if agent can execute action, False otherwise

        Examples:
            >>> architect = Agent(
            ...     agent_id=AgentId("agent-arch-001"),
            ...     role=RoleFactory.create_architect(),
            ...     name="Architect",
            ...     capabilities=AgentCapabilities(...),
            ... )
            >>> approve_design = Action(value=ActionEnum.APPROVE_DESIGN)
            >>> architect.can_execute(approve_design)
            True
        """
        return self.role.can_perform(action)

    def can_use_tool(self, tool_name: str) -> bool:
        """Check if agent can use the given tool.

        Tell, Don't Ask: Agent delegates to its role to check tool access.

        Args:
            tool_name: Name of the tool (e.g., "files", "git", "tests")

        Returns:
            True if tool is allowed for this role, False otherwise

        Examples:
            >>> developer = Agent(...)  # role=Developer
            >>> developer.can_use_tool("git")
            True
            >>> developer.can_use_tool("db")
            False  # Only DATA role can use db
        """
        return self.role.has_tool_access(tool_name)

    def get_role_name(self) -> str:
        """Get role name for logging/display.

        Tell, Don't Ask: Agent provides its role name.

        Returns:
            Role name (e.g., "architect", "developer")
        """
        return self.role.get_name()

    def get_agent_id_string(self) -> str:
        """Get agent ID as string.

        Tell, Don't Ask: Agent provides its ID as string.

        Returns:
            Agent ID string (e.g., "agent-dev-001")
        """
        return str(self.agent_id)

    def can_execute_capability(self, capability: Any) -> bool:
        """Check if agent can execute a specific capability.

        Business Logic: Combines RBAC (role) + available tools (capabilities).

        Rules:
        - Capability tool must be in role's allowed_tools
        - Capability must exist in agent's available capabilities
        - Both conditions must be true

        Args:
            capability: Capability to check (tool.operation)

        Returns:
            True if agent can execute this capability, False otherwise

        Examples:
            >>> agent = Agent(...)  # Developer role
            >>> git_commit = Capability("git", "commit")
            >>> agent.can_execute_capability(git_commit)
            True  # Developer can use git
            >>> db_query = Capability("db", "query")
            >>> agent.can_execute_capability(db_query)
            False  # Developer cannot use db (only DATA role)
        """
        # RBAC check: role must allow this tool
        if not self.role.has_tool_access(capability.tool):
            return False

        # Capability availability check: must be in available operations
        if capability not in self.capabilities.operations:
            return False

        return True

    def get_executable_capabilities(self) -> list:
        """Get list of capabilities agent can actually execute.

        Business Logic: Returns intersection of:
        - Role's allowed_tools (RBAC permissions)
        - Available capabilities (infrastructure constraints)

        Tell, Don't Ask: Agent delegates to capabilities and role.

        Returns:
            List of Capability objects agent can execute

        Examples:
            >>> agent = Agent(...)  # Developer with files, git, tests
            >>> caps = agent.get_executable_capabilities()
            >>> all(agent.role.has_tool_access(cap.tool) for cap in caps)
            True
        """
        # Tell Don't Ask: filter by role's allowed tools
        return [
            cap
            for cap in self.capabilities.operations
            if self.role.has_tool_access(cap.tool)
        ]

    def get_write_capabilities(self) -> list:
        """Get capabilities that perform write operations.

        Business Logic: Filter executable capabilities to only writes.
        Combines RBAC (role) + write operation filtering.

        Returns:
            List of write-capable Capability objects
        """
        # Tell Don't Ask: delegate to collection, then filter by role
        write_caps = self.capabilities.operations.get_write_capabilities()
        return [cap for cap in write_caps if self.role.has_tool_access(cap.tool)]

    def get_read_capabilities(self) -> list:
        """Get capabilities that perform read operations.

        Business Logic: Filter executable capabilities to only reads.
        Combines RBAC (role) + read operation filtering.

        Returns:
            List of read-only Capability objects
        """
        # Tell Don't Ask: delegate to collection, then filter by role
        read_caps = self.capabilities.operations.get_read_capabilities()
        return [cap for cap in read_caps if self.role.has_tool_access(cap.tool)]

    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.agent_id} ({self.role.get_name()})"

